import json
import sys
from datetime import date, timedelta
from pathlib import Path

import fetch
import pfz
from regions import BBOX, REGIONS

SST_TIMES = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.csv?time[(last)]"
CHL_TIMES = "https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaWeekly.csv?time[({start}):1:(last)]"
STEP_DAYS = 7
CHL_LOOKBACK_DAYS = 60  # chlorophyll can trail SST by more than a week
STALE_DAYS = 10  # weekly chlorophyll older than SST by more: use the multi-sensor daily median (web/index.html warns at the same lag)


def date_pairs(start, end):
    end = date.fromisoformat(end)
    sst_dates = []
    while end >= date.fromisoformat(start):
        sst_dates.append(end.isoformat())
        end -= timedelta(days=STEP_DAYS)
    first = date.fromisoformat(sst_dates[-1]) - timedelta(days=CHL_LOOKBACK_DAYS)
    chl_dates = fetch.erddap_dates(CHL_TIMES.format(start=first))
    return [(s, max(c for c in chl_dates if c <= s)) for s in reversed(sst_dates)]


def write_index(root):
    entries = []
    for path in sorted(Path(root).glob("*/zones.geojson")):
        geojson = json.load(open(path))
        zones = [f for f in geojson["features"] if f["geometry"]["type"] != "Point"]
        counts = {name: 0 for name in REGIONS}
        for f in zones:
            counts[f["properties"]["region"]] += 1
        entries.append({
            "date": path.parent.name,
            "sst_date": geojson["sst_date"],
            "chl_date": geojson["chl_date"],
            "chl_source": geojson["chl_source"],
            "chl_days": geojson["chl_days"],
            "zones": len(zones),
            "regions": counts,
        })
    lat_min, lat_max, lon_min, lon_max = BBOX
    index = {"bounds": [[lat_min, lon_min], [lat_max, lon_max]], "regions": REGIONS, "dates": entries}
    with open(Path(root) / "index.json", "w") as f:
        json.dump(index, f, indent=1)
    print(f"index: {len(entries)} dates")


if __name__ == "__main__":
    if sys.argv[1] == "last":
        start = end = fetch.erddap_dates(SST_TIMES)[0]
    else:
        start, end = sys.argv[1], sys.argv[2]
    for sst_date, chl_date in date_pairs(start, end):
        fetch.fetch(sst_date)
        for name in fetch.EXTRA:
            fetch.fetch_extra(name, sst_date)
        chl_days = None
        if (date.fromisoformat(sst_date) - date.fromisoformat(chl_date)).days > STALE_DAYS:
            chl_days = fetch.fetch_daily_chl(sst_date)
            chl_date = max(d for _, d in chl_days)
        else:
            fetch.fetch_chl(chl_date)
        pfz.run(sst_date, chl_date, chl_days)
    write_index("outputs")
