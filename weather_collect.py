"""Phase 2 collector — model forecasts vs live weather-market prices.

Polymarket runs daily "Highest temperature in {city} on {date}?" events (one
event = ~11 binary bucket markets). The thesis: public NWP models (GFS/ECMWF/
ICON via open-meteo) forecast tomorrow's T_max better than the crowd prices
it. Each run records every live bucket's prices next to the same-moment
multi-model forecasts for that city/date, so forecast skill vs market prices
becomes measurable after resolution.

Discovery is via the weather tag on EVENTS (the markets carry no category);
cities are geocoded on the fly (cache in data-free collected/city_geo.json)
because the venue rotates cities. Only target dates within [today-1, +7] are
kept — beyond a week the models carry no signal and stale unresolved events
linger in the API.

Runs in the collectors workflow (2x daily). Output: collected/weather_obs.csv.

    python weather_collect.py
"""
import csv
import datetime as dt
import json
import pathlib
import re
import time
import urllib.request

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "collected"
OUT = D / "weather_obs.csv"
GEO = D / "city_geo.json"
MODELS = (("gfs_seamless", "fc_gfs"), ("ecmwf_ifs025", "fc_ecmwf"),
          ("icon_seamless", "fc_icon"))

FIELDS = ["t", "event_title", "city", "target_date", "market_id", "slug",
          "question", "outcomes", "prices", "volume", "neg_risk",
          "fc_gfs_c", "fc_ecmwf_c", "fc_icon_c"]


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            if i == tries - 1:
                return None
            time.sleep(2 * (i + 1))


def geocode(city, cache):
    if city in cache:
        return cache[city]
    d = get("https://geocoding-api.open-meteo.com/v1/search"
            f"?name={urllib.parse.quote(city)}&count=1")
    res = (d or {}).get("results") or []
    cache[city] = ([res[0]["latitude"], res[0]["longitude"],
                    res[0].get("timezone", "UTC")] if res else None)
    GEO.write_text(json.dumps(cache))
    return cache[city]


def target_date(title_md, slug):
    """'May 20' + a year hint from the slug -> ISO date."""
    m = re.match(r"(\w+) (\d+)", title_md)
    if not m:
        return None
    try:
        month = dt.datetime.strptime(m.group(1)[:3], "%b").month
    except ValueError:
        return None
    day = int(m.group(2))
    ym = re.search(r"-(\d{4})", slug)
    year = int(ym.group(1)) if ym else dt.date.today().year
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def forecasts(city, geo, date):
    lat, lon, tz = geo
    d = get("https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&daily=temperature_2m_max"
            f"&timezone={urllib.parse.quote(tz)}"
            f"&start_date={date}&end_date={date}"
            f"&models={','.join(m for m, _ in MODELS)}")
    daily = (d or {}).get("daily") or {}
    out = {}
    for model, name in MODELS:
        v = daily.get(f"temperature_2m_max_{model}")
        out[f"{name}_c"] = v[0] if isinstance(v, list) and v else None
    return out


def main():
    D.mkdir(exist_ok=True)
    now = round(time.time(), 1)
    today = dt.date.today()
    cache = json.loads(GEO.read_text()) if GEO.exists() else {}
    rows, fc_cache = [], {}
    for off in range(0, 800, 100):
        evs = get("https://gamma-api.polymarket.com/events?closed=false"
                  f"&limit=100&offset={off}&tag_slug=weather")
        if not evs:
            break
        for e in evs:
            m = re.match(r"Highest temperature in (.+?) on (.+?)\?",
                         e.get("title") or "")
            if not m:
                continue
            city = m.group(1).strip()
            mkts = e.get("markets") or []
            date = target_date(m.group(2), mkts[0].get("slug", "") if mkts else "")
            if not date or not (-1 <= (date - today).days <= 7):
                continue
            key = (city, str(date))
            if key not in fc_cache:
                geo = geocode(city, cache)
                fc_cache[key] = forecasts(city, geo, date) if geo else {}
                time.sleep(0.4)
            fc = fc_cache[key]
            for mk in mkts:
                rows.append({
                    "t": now, "event_title": (e.get("title") or "")[:60],
                    "city": city, "target_date": str(date),
                    "market_id": mk.get("id"),
                    "slug": (mk.get("slug") or "")[:70],
                    "question": (mk.get("question") or "")[:80],
                    "outcomes": (mk.get("outcomes") or "")[:120],
                    "prices": (mk.get("outcomePrices") or "")[:120],
                    "volume": mk.get("volumeNum") or mk.get("volume"),
                    "neg_risk": 1 if mk.get("negRisk") else 0, **fc})
        if len(evs) < 100:
            break
    write_header = not OUT.exists()
    with OUT.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        w.writerows(rows)
    got = sum(1 for r in rows if r.get("fc_gfs_c") is not None)
    print(f"weather_collect: {len(rows)} bucket rows, "
          f"{len(fc_cache)} city-dates, {got} with GFS forecast")


if __name__ == "__main__":
    main()
