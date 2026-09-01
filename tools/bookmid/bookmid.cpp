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
// build:  g++ -O2 -std=c++17 -o bookmid bookmid.cpp -lz
// usage:  ./bookmid file.jsonl.gz > mids.csv
#include <zlib.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>
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

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        std::fprintf(stderr, "usage: bookmid file.jsonl.gz\n");
        return 2;
    }
    std::string data = gz_read_all(argv[1]);
    if (data.empty()) {
        std::fprintf(stderr, "bookmid: cannot read %s\n", argv[1]);
        return 1;
    }
    std::unordered_map<std::string, Top> best;
    best.reserve(1024);
    static char obuf[1 << 20];
    std::setvbuf(stdout, obuf, _IOFBF, sizeof obuf);
    std::printf("t,asset,bid,ask\n");
    size_t pos = 0, emitted = 0;
    std::string line;                       // reused; no per-line alloc growth
    while (pos < data.size()) {
        size_t nl = data.find('\n', pos);
        if (nl == std::string::npos) nl = data.size();
        line.assign(data, pos, nl - pos);
        pos = nl + 1;
        if (line.find("\"meta\"") != std::string::npos) continue;
        std::string t = field(line, "t");
        // inner message: everything after "m": — unescape if quoted
        size_t mv = after_key(line, "m");
        std::string inner;
        if (mv != std::string::npos && mv < line.size()) {
            if (line[mv] == '"') {
                size_t e = line.rfind('"');
                if (e > mv + 1)
                    inner = unescape(line.substr(mv + 1, e - mv - 1));
            } else {
                inner = line.substr(mv);
            }
        }
        if (inner.empty() || t.empty()) continue;

        // events can be a single object or an array; scan every event_type
        size_t ev = 0;
        while ((ev = inner.find("\"event_type\"", ev)) != std::string::npos) {
            size_t vs = after_key(inner, "event_type", ev);
            if (vs == std::string::npos || inner[vs] != '"') { ev += 12; continue; }
            ++vs;
            size_t ve = inner.find('"', vs);
            std::string et = inner.substr(vs, ve - vs);
            size_t next = inner.find("\"event_type\"", ve);
            const std::string& whole = inner;   // scan bounded by [ev, next)
            size_t bound = (next == std::string::npos ? whole.size() : next);
            std::string chunk = whole.substr(ev, bound - ev);
            if (et == "book") {
                std::string a = field(chunk, "asset_id");
                if (!a.empty()) {
                    Top& tp = best[a];
                    tp.bid = num(last_price_in_array(chunk, "bids"), 0.0);
                    tp.ask = num(last_price_in_array(chunk, "asks"), 1.0);
                    if (tp.bid > 0 && tp.ask > tp.bid && tp.ask <= 1.0) {
                        std::printf("%s,%s,%.6g,%.6g\n", t.c_str(), a.c_str(),
                                    tp.bid, tp.ask);
                        ++emitted;
                    }
                }
            } else if (et == "price_change") {
                size_t pc = 0;
                while ((pc = chunk.find("\"asset_id\":", pc)) !=
                       std::string::npos) {
                    std::string a = field(chunk, "asset_id", pc);
                    Top& tp = best.try_emplace(a).first->second;
                    std::string bb = field(chunk, "best_bid", pc);
                    std::string ba = field(chunk, "best_ask", pc);
                    if (!bb.empty()) tp.bid = num(bb, tp.bid);
                    if (!ba.empty()) tp.ask = num(ba, tp.ask);
                    if (tp.bid > 0 && tp.ask > tp.bid && tp.ask <= 1.0) {
                        std::printf("%s,%s,%.6g,%.6g\n", t.c_str(), a.c_str(),
                                    tp.bid, tp.ask);
                        ++emitted;
                    }
                    pc += 11;
                }
            }
            ev = (next == std::string::npos) ? inner.size() : next;
        }
    }
    std::fprintf(stderr, "bookmid: %zu top-of-book updates\n", emitted);
    return 0;
}
