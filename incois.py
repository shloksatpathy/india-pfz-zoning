import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path

# Current INCOIS PFZ lines, from the WFS layer behind https://incois.gov.in/MarineFisheries/PfzWebGis
URL = (
    "https://incois.gov.in/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0&request=GetFeature"
    "&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
)
STEP_DEG = 0.01  # keep line vertices ~1 km apart


def thin(line):
    kept = [line[0]]
    for lon, lat in line[1:-1]:
        if abs(lon - kept[-1][0]) >= STEP_DEG or abs(lat - kept[-1][1]) >= STEP_DEG:
            kept.append([lon, lat])
    kept.append(line[-1])
    return [[round(lon, 3), round(lat, 3)] for lon, lat in kept]


def archive():
    with urllib.request.urlopen(URL) as r:
        features = json.load(r)["features"]
    if not features:
        print("no INCOIS PFZ lines today")
        return

    p = features[0]["properties"]
    day = (date(p["Year"], 1, 1) + timedelta(days=int(p["Julian_day"]) - 1)).isoformat()
    path = Path("validation/incois") / f"{day}.geojson"
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        {
            "type": "Feature",
            "geometry": {"type": "MultiLineString", "coordinates": [thin(line) for line in f["geometry"]["coordinates"]]},
            "properties": {
                "uid": f["properties"]["UID"],
                "state": f["properties"]["State_Name"],
                "sector": f["properties"]["SECTORBOUN"],
                "length_km": round(f["properties"]["Length"], 1),
            },
        }
        for f in features
    ]
    with open(path, "w") as f:
        json.dump({"type": "FeatureCollection", "date": day, "features": lines}, f)
    print(f"{len(lines)} INCOIS PFZ lines for {day} written to {path}")


if __name__ == "__main__":
    archive()
