// bookmid — C++17 order-book mid reconstructor for the desk's recordings.
//
// Reads the recorder's gzip'd jsonl (one line per WebSocket message:
// {"t": <epoch>, "m": "<escaped json>"} where the inner message is either a
// snapshot {"event_type":"book","asset_id":...,"bids":[...],"asks":[...]}
// or a diff {"event_type":"price_change","price_changes":[{"asset_id":...,
// "best_bid":...,"best_ask":...},...]} — messages may also arrive as arrays)
// and emits CSV: t,asset,bid,ask for every top-of-book change.
//
// This is the hot path of trade_markout.build_mids(); the Python and C++
// implementations are pinned against each other in tests/test_bookmid.py.
// No JSON library: the producer's schema is fixed and covered by tests, so
// extraction is targeted string scanning after unescaping the envelope.
//
// Parallel design: parsing is ~90% of the cost and stateless per line, so the
// buffer is split into line-aligned shards parsed by N threads into event
// vectors; the stateful top-of-book APPLY then runs sequentially in original
// order (correctness requires it: diffs depend on prior state per asset).
//
// build:  g++ -O2 -std=c++17 -pthread -o bookmid bookmid.cpp -lz
// usage:  ./bookmid [-j N] file.jsonl.gz > mids.csv
#include <zlib.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
#include <thread>
#include <atomic>
#include <chrono>
#include <charconv>
#include <unordered_map>
#include <vector>

namespace {

struct Top {
    double bid = 0.0;
    double ask = 1.0;
};

// read a whole gzip file (multi-member OK — gzread handles concatenation)
std::string gz_read_all(const char* path) {
    gzFile f = gzopen(path, "rb");
    if (!f) return {};
    std::string out;
    char buf[1 << 16];
    int n;
    while ((n = gzread(f, buf, sizeof buf)) > 0) out.append(buf, n);
    gzclose(f);
    return out;
}

// unescape the JSON string escapes the envelope adds (\" \\ \/ \n \t)
std::string unescape(const std::string& s) {
    std::string o;
    o.reserve(s.size());
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] == '\\' && i + 1 < s.size()) {
            char c = s[++i];
            o += (c == 'n' ? '\n' : c == 't' ? '\t' : c);
        } else {
            o += s[i];
        }
    }
    return o;
}

// index just past `"key":` + any spaces, or npos
size_t after_key(const std::string& s, const char* key, size_t from = 0) {
    std::string pat = std::string("\"") + key + "\"";
    size_t k = s.find(pat, from);
    if (k == std::string::npos) return std::string::npos;
    size_t v = k + pat.size();
    while (v < s.size() && (s[v] == ' ' || s[v] == ':')) ++v;
    return v;
}

// find "key":<value...> and return the raw scalar or quoted string after it,
// starting the scan at `from`; returns empty if absent
std::string field(const std::string& s, const char* key, size_t from = 0) {
    size_t v = after_key(s, key, from);
    if (v == std::string::npos || v >= s.size()) return {};
    if (s[v] == '"') {
        size_t e = s.find('"', v + 1);
        return e == std::string::npos ? std::string{}
                                      : s.substr(v + 1, e - v - 1);
    }
    size_t e = v;
    while (e < s.size() && strchr("-.0123456789eE", s[e])) ++e;
    return s.substr(v, e - v);
}

double num(const std::string& v, double fallback) {
    if (v.empty()) return fallback;
    try {
        return std::stod(v);
    } catch (...) {
        return fallback;
    }
}

// last "price" inside the LAST element of the named array (recorder writes
// bids/asks best-last, matching the Python `bids[-1]` convention)
std::string last_price_in_array(const std::string& s, const char* key) {
    size_t v = after_key(s, key);
    if (v == std::string::npos || v >= s.size() || s[v] != '[') return {};
    size_t depth = 0, i = v;
    size_t end = std::string::npos;
    for (; i < s.size(); ++i) {          // matching ] of this array
        if (s[i] == '[') ++depth;
        else if (s[i] == ']' && --depth == 0) { end = i; break; }
    }
    if (end == std::string::npos) return {};
    std::string arr = s.substr(v + 1, end - v - 1);
    size_t last = arr.rfind("\"price\"");
    if (last == std::string::npos) return {};
    return field(arr, "price", last);
}

// one parsed top-of-book event, in stream order
struct Event {
    std::string asset;
    double bid = -1.0;     // <0 = "keep previous" (absent field in a diff)
    double ask = -1.0;
    bool snapshot = false;
    std::string t;
};

// parse every event in data[lo, hi) into out (stateless; thread-safe)
void parse_range(const std::string& data, size_t lo, size_t hi,
                 std::vector<Event>* out) {
    size_t pos = lo;
    std::string line;
    while (pos < hi) {
        size_t nl = data.find('\n', pos);
        if (nl == std::string::npos || nl > hi) nl = hi;
        line.assign(data, pos, nl - pos);
        pos = nl + 1;
        if (line.find("\"meta\"") != std::string::npos) continue;
        std::string t = field(line, "t");
        size_t mv = after_key(line, "m");
        std::string inner;
        if (mv != std::string::npos && mv < line.size()) {
            if (line[mv] == '"') {
                size_t e = line.rfind('"');
                if (e > mv + 1) inner = unescape(line.substr(mv + 1, e - mv - 1));
            } else {
                inner = line.substr(mv);
            }
        }
        if (inner.empty() || t.empty()) continue;
        size_t ev = 0;
        while ((ev = inner.find("\"event_type\"", ev)) != std::string::npos) {
            size_t vs = after_key(inner, "event_type", ev);
            if (vs == std::string::npos || inner[vs] != '"') { ev += 12; continue; }
            ++vs;
            size_t ve = inner.find('"', vs);
            std::string et = inner.substr(vs, ve - vs);
            size_t next = inner.find("\"event_type\"", ve);
            size_t bound = (next == std::string::npos ? inner.size() : next);
            std::string chunk = inner.substr(ev, bound - ev);
            if (et == "book") {
                std::string a = field(chunk, "asset_id");
                if (!a.empty()) {
                    Event e2;
                    e2.asset = std::move(a);
                    e2.snapshot = true;
                    e2.bid = num(last_price_in_array(chunk, "bids"), 0.0);
                    e2.ask = num(last_price_in_array(chunk, "asks"), 1.0);
                    e2.t = t;
                    out->push_back(std::move(e2));
                }
            } else if (et == "price_change") {
                size_t pc = 0;
                while ((pc = chunk.find("\"asset_id\"", pc)) != std::string::npos) {
                    Event e2;
                    e2.asset = field(chunk, "asset_id", pc);
                    std::string bb = field(chunk, "best_bid", pc);
                    std::string ba = field(chunk, "best_ask", pc);
                    if (!bb.empty()) e2.bid = num(bb, -1.0);
                    if (!ba.empty()) e2.ask = num(ba, -1.0);
                    e2.t = t;
                    out->push_back(std::move(e2));
                    pc += 10;
                }
            }
            ev = bound;
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    int jobs = 1;
    int argi = 1;
    if (argc >= 3 && std::string(argv[1]) == "-j") {
        jobs = std::max(1, atoi(argv[2]));
        argi = 3;
    }
    if (argc <= argi) {
        std::fprintf(stderr, "usage: bookmid [-j N] file.jsonl.gz\n");
        return 2;
    }
    auto t0 = std::chrono::steady_clock::now();
    std::string data = gz_read_all(argv[argi]);
    auto t1 = std::chrono::steady_clock::now();
    if (data.empty()) {
        std::fprintf(stderr, "bookmid: cannot read %s\n", argv[1]);
        return 1;
    }
    // ---- phase 1: parallel parse over line-aligned shards ----
    size_t n = data.size();
    std::vector<size_t> cuts{0};
    for (int i = 1; i < jobs; ++i) {
        size_t c = n * i / jobs;
        while (c < n && data[c] != '\n') ++c;   // align to line boundary
        cuts.push_back(std::min(c + 1, n));
    }
    cuts.push_back(n);
    std::vector<std::vector<Event>> shards(jobs);
    std::vector<std::thread> workers;
    for (int i = 0; i < jobs; ++i)
        workers.emplace_back(parse_range, std::cref(data),
                             cuts[i], cuts[i + 1], &shards[i]);
    for (auto& w : workers) w.join();
    auto t2 = std::chrono::steady_clock::now();

    // ---- phase 2: sequential apply, original order preserved ----
    std::unordered_map<std::string, Top> best;
    best.reserve(1024);
    std::string out;
    out.reserve(1 << 22);
    out += "t,asset,bid,ask\n";
    char nbuf[32];
    auto put_num = [&](double v) {           // to_chars: ~5x faster than %.6g
        auto [end, ec] = std::to_chars(nbuf, nbuf + sizeof nbuf, v,
                                       std::chars_format::general, 6);
        out.append(nbuf, end - nbuf);
    };
    size_t emitted = 0;
    for (auto& shard : shards) {
        for (auto& e : shard) {
            Top& tp = best.try_emplace(e.asset).first->second;
            if (e.snapshot) {
                tp.bid = e.bid;
                tp.ask = e.ask;
            } else {
                if (e.bid >= 0) tp.bid = e.bid;
                if (e.ask >= 0) tp.ask = e.ask;
            }
            if (tp.bid > 0 && tp.ask > tp.bid && tp.ask <= 1.0) {
                out += e.t;
                out += ',';
                out += e.asset;
                out += ',';
                put_num(tp.bid);
                out += ',';
                put_num(tp.ask);
                out += '\n';
                ++emitted;
                if (out.size() > (1 << 21)) {
                    std::fwrite(out.data(), 1, out.size(), stdout);
                    out.clear();
                }
            }
        }
    }
    std::fwrite(out.data(), 1, out.size(), stdout);
    auto t3 = std::chrono::steady_clock::now();
    auto ms = [](auto a, auto b) {
        return std::chrono::duration_cast<std::chrono::milliseconds>(b - a)
            .count();
    };
    // phase timings make the scaling honest: parse parallelizes ~linearly,
    // end-to-end is Amdahl-bound by the serial gzip inflate
    std::fprintf(stderr,
                 "bookmid: %zu updates (%d threads) | inflate %lldms | "
                 "parse %lldms | apply+emit %lldms\n",
                 emitted, jobs, (long long)ms(t0, t1), (long long)ms(t1, t2),
                 (long long)ms(t2, t3));
    return 0;
}
