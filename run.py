import json
import sys
import urllib.request
from pathlib import Path

import fetch
import pfz
from regions import BBOX, REGIONS

CHL_TIMES = "https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPVIIRSSQchlaWeekly.csv?time[({start}):1:({end})]"


def chl_dates(start, end):
    with urllib.request.urlopen(CHL_TIMES.format(start=start, end=end)) as r:
        lines = r.read().decode().splitlines()[2:]
    return [line[:10] for line in lines]


def write_index():
    entries = []
    for path in sorted(Path("outputs").glob("*/zones.geojson")):
        features = json.load(open(path))["features"]
        counts = {name: 0 for name in REGIONS}
        for f in features:
            counts[f["properties"]["region"]] += 1
        entries.append({"date": path.parent.name, "zones": len(features), "regions": counts})
    lat_min, lat_max, lon_min, lon_max = BBOX
    index = {"bounds": [[lat_min, lon_min], [lat_max, lon_max]], "regions": REGIONS, "dates": entries}
    with open("outputs/index.json", "w") as f:
        json.dump(index, f, indent=1)
    print(f"index: {len(entries)} dates")


if __name__ == "__main__":
    for date in chl_dates(sys.argv[1], sys.argv[2]):
        fetch.fetch(date)
        pfz.run(date)
    write_index()
