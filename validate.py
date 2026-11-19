import csv
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as Polygon
import numpy as np
from scipy.spatial import cKDTree

from pfz import KM_PER_DEG, region_of
from regions import REGIONS

NEAR_KM = 10  # a line or point this close to the other set counts as matched
MAX_GAP_DAYS = 3  # our output date may differ from the INCOIS date by this much


def km_xy(lon, lat):
    return np.column_stack([lon * KM_PER_DEG * np.cos(np.deg2rad(lat)), lat * KM_PER_DEG])


def incois_segments(path):
    """Midpoint, length (km) and region of every segment of the INCOIS lines."""
    rows = []
    for f in json.load(open(path))["features"]:
        for line in f["geometry"]["coordinates"]:
            line = np.array(line)
            mid = (line[1:] + line[:-1]) / 2
            xy = km_xy(line[:, 0], line[:, 1])
            length = np.hypot(*np.diff(xy, axis=0).T)
            region = region_of(line[len(line) // 2, 1], line[len(line) // 2, 0])
            rows += [(m[0], m[1], km, region, f["properties"]["uid"]) for m, km in zip(mid, length)]
    return rows


def our_date(day):
    dates = [p.parent.name for p in Path("outputs").glob("*/zones.geojson")]
    best = min(dates, key=lambda d: abs((date.fromisoformat(d) - date.fromisoformat(day)).days))
    if abs((date.fromisoformat(best) - date.fromisoformat(day)).days) > MAX_GAP_DAYS:
        sys.exit(f"no output within {MAX_GAP_DAYS} days of {day}")
    return best


def compare(day):
    ours = our_date(day)
    features = json.load(open(f"outputs/{ours}/zones.geojson"))["features"]
    zones = [f for f in features if f["geometry"]["type"] == "Polygon"]
    points = [f["properties"] for f in features if f["geometry"]["type"] == "Point"]
    segments = incois_segments(f"validation/incois/{day}.geojson")

    seg_lon = np.array([s[0] for s in segments])
    seg_lat = np.array([s[1] for s in segments])
    seg_km = np.array([s[2] for s in segments])
    seg_region = [s[3] for s in segments]

    outline = np.concatenate([f["geometry"]["coordinates"][0] for f in zones])
    near_zone = cKDTree(km_xy(outline[:, 0], outline[:, 1])).query(km_xy(seg_lon, seg_lat))[0] <= NEAR_KM
    for f in zones:
        near_zone |= Polygon(f["geometry"]["coordinates"][0]).contains_points(np.column_stack([seg_lon, seg_lat]))

    pt_lon = np.array([p["lon"] for p in points])
    pt_lat = np.array([p["lat"] for p in points])
    near_line = cKDTree(km_xy(seg_lon, seg_lat)).query(km_xy(pt_lon, pt_lat))[0] <= NEAR_KM

    rows = []
    for name in [*REGIONS, "All"]:
        s = np.array([name == "All" or r == name for r in seg_region])
        p = np.array([name == "All" or pt["region"] == name for pt in points])
        z = [f for f in zones if name == "All" or f["properties"]["region"] == name]
        rows.append({
            "region": name,
            "incois_lines": len({seg[4] for seg, keep in zip(segments, s) if keep}),
            "incois_km": round(float(seg_km[s].sum())),
            "hit_rate": round(float(seg_km[s & near_zone].sum() / seg_km[s].sum()), 2) if s.any() else "",
            "our_zones": len(z),
            "our_points": int(p.sum()),
            "precision": round(float(near_line[p].mean()), 2) if p.any() else "",
        })

    out = Path("validation") / f"{day}.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"INCOIS {day} vs ours {ours} -> {out}")
    for r in rows:
        print("  ".join(f"{v!s:>8}" if k != "region" else f"{v:<24}" for k, v in r.items()))

    plot(day, ours, zones, points, segments, seg_region)


def plot(day, ours, zones, points, segments, seg_region):
    out = Path("outputs") / "validation" / day
    out.mkdir(parents=True, exist_ok=True)
    lines = json.load(open(f"validation/incois/{day}.geojson"))["features"]
    for name in sorted({r for r in seg_region if r}):
        lat_min, lat_max, lon_min, lon_max = REGIONS[name]
        fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
        for f in zones:
            ring = np.array(f["geometry"]["coordinates"][0])
            ax.fill(ring[:, 0], ring[:, 1], color="tab:green", alpha=0.4, lw=0)
        ax.scatter([p["lon"] for p in points], [p["lat"] for p in points], s=8, c="k", label=f"our points ({ours})")
        for f in lines:
            for line in f["geometry"]["coordinates"]:
                line = np.array(line)
                ax.plot(line[:, 0], line[:, 1], c="tab:red", lw=1.5)
        ax.plot([], [], c="tab:red", label=f"INCOIS lines ({day})")
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)
        ax.set_aspect("equal")
        ax.legend(loc="lower left")
        ax.set_title(f"{name}: green = our zones")
        slug = name.lower().replace(" & ", "_").replace(" ", "_")
        fig.savefig(out / f"{slug}.png", dpi=100)
        plt.close(fig)
    print(f"maps in {out}")


if __name__ == "__main__":
    compare(sys.argv[1])
