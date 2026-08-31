"""ECMWF D-1 sidecar for the weather dataset — one ranged previous-runs call
per city (°C; convert to family units downstream).

    python fetch_ecmwf_d1.py
"""
import csv, gzip, json, time, urllib.request, urllib.parse, pathlib
from collections import defaultdict

UA = {"User-Agent": "research saviswarup@gmail.com"}
D = pathlib.Path(__file__).parent / "data"


def get(u, tries=3):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(
                urllib.request.Request(u, headers=UA), timeout=40).read())
        except Exception:
            time.sleep(3 * (i + 1))
    return None


def main():
    geo = json.loads((D / "city_geo2.json").read_text())
    pairs = defaultdict(set)
    with gzip.open(D / "weather_families.csv.gz", "rt") as f:
        for r in csv.DictReader(f):
            pairs[r["city"]].add(r["date"])
    out = {}
    for city, dates in pairs.items():
        g = geo.get(city)
        if not g:
            continue
        d = get("https://previous-runs-api.open-meteo.com/v1/forecast"
                f"?latitude={g['lat']}&longitude={g['lon']}"
                "&hourly=temperature_2m_previous_day1"
                f"&timezone={urllib.parse.quote(g['tz'])}"
                f"&start_date={min(dates)}&end_date={max(dates)}"
                "&models=ecmwf_ifs025")
        h = (d or {}).get("hourly", {})
        daymax = defaultdict(lambda: -1e9)
        for t, v in zip(h.get("time", []), h.get("temperature_2m_previous_day1", [])):
            if v is not None and v > daymax[t[:10]]:
                daymax[t[:10]] = v
        for day in dates:
            if daymax.get(day, -1e9) > -1e8:
                out[(city, day)] = round(daymax[day], 2)
        time.sleep(0.3)
    with gzip.open(D / "weather_ecmwf_d1.csv.gz", "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "date", "fc_ecmwf_d1"])
        for (c, dt), v in sorted(out.items()):
            w.writerow([c, dt, v])
    print(f"ecmwf D-1 sidecar: {len(out):,} city-dates")


if __name__ == "__main__":
    main()
