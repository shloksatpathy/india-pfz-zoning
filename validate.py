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

from harbours import HARBOURS
from pfz import km_xy, nearest_harbour
from regions import REGIONS

NEAR_KM = 10  # a line or point this close to the other set counts as matched
MAX_GAP_DAYS = 3  # our output date may differ from the INCOIS date by this much
PUBLISHED = Path("docs/site/outputs")  # our published zones, also present in CI


def incois_segments(path):
    """Midpoint, length (km) and region of every segment of the INCOIS lines."""
    rows = []
    for f in json.load(open(path))["features"]:
        for line in f["geometry"]["coordinates"]:
            line = np.array(line)
            mid = (line[1:] + line[:-1]) / 2
            xy = km_xy(line[:, 0], line[:, 1])
            length = np.hypot(*np.diff(xy, axis=0).T)
            region = HARBOURS[nearest_harbour(line[len(line) // 2, 1], line[len(line) // 2, 0])[0]][2]
            rows += [(m[0], m[1], km, region, f["properties"]["uid"]) for m, km in zip(mid, length)]
    return rows


def polygons(geometry):
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    return geometry["coordinates"]


def inside(geometry, lonlat):
    hit = np.zeros(len(lonlat), dtype=bool)
    for outer, *holes in polygons(geometry):
        h = Polygon(outer).contains_points(lonlat)
        for hole in holes:
            h &= ~Polygon(hole).contains_points(lonlat)
        hit |= h
    return hit


def our_date(day):
    """Published date nearest the INCOIS day, or None if none is within MAX_GAP_DAYS."""
    dates = [p.parent.name for p in PUBLISHED.glob("*/zones.geojson")]
    best = min(dates, key=lambda d: abs((date.fromisoformat(d) - date.fromisoformat(day)).days))
    if abs((date.fromisoformat(best) - date.fromisoformat(day)).days) > MAX_GAP_DAYS:
        return None
    return best


def score(segments, zones, points):
    """Per-region rows; zones are features with geometry and properties.region, points have lat, lon, region."""
    seg_lon = np.array([s[0] for s in segments])
    seg_lat = np.array([s[1] for s in segments])
    seg_km = np.array([s[2] for s in segments])
    seg_region = [s[3] for s in segments]

    near_zone = np.zeros(len(segments), dtype=bool)
    if zones:  # a strict threshold in a sweep can leave no zones
        outline = np.concatenate([ring for f in zones for poly in polygons(f["geometry"]) for ring in poly])
        near_zone = cKDTree(km_xy(outline[:, 0], outline[:, 1])).query(km_xy(seg_lon, seg_lat))[0] <= NEAR_KM
    for f in zones:
        near_zone |= inside(f["geometry"], np.column_stack([seg_lon, seg_lat]))

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
    return rows


def compare(day):
    ours = our_date(day)
    if ours is None:
        print(f"INCOIS {day}: no published date within {MAX_GAP_DAYS} days, not scored yet")
        return
    features = json.load(open(PUBLISHED / ours / "zones.geojson"))["features"]
    zones = [f for f in features if f["geometry"]["type"] != "Point"]
    points = [f["properties"] for f in features if f["geometry"]["type"] == "Point"]
    segments = incois_segments(f"validation/incois/{day}.geojson")
    rows = score(segments, zones, points)

    out = Path("validation") / f"{day}.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"INCOIS {day} vs ours {ours} -> {out}")
    for r in rows:
        print("  ".join(f"{v!s:>8}" if k != "region" else f"{v:<24}" for k, v in r.items()))

    plot(day, ours, zones, points, segments)


def plot(day, ours, zones, points, segments):
    out = Path("outputs") / "validation" / day
    out.mkdir(parents=True, exist_ok=True)
    lines = json.load(open(f"validation/incois/{day}.geojson"))["features"]
    for name in sorted({s[3] for s in segments}):
        lat_min, lat_max, lon_min, lon_max = REGIONS[name]
        fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
        for f in zones:
            for outer, *_ in polygons(f["geometry"]):
                ring = np.array(outer)
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


def score_new():
    """Score every archived INCOIS day that has no validation/<date>.csv yet."""
    for path in sorted(Path("validation/incois").glob("*.geojson")):
        if not (Path("validation") / f"{path.stem}.csv").exists():
            compare(path.stem)


def summary():
    """Mean hit rate and precision per region over the scored days on which INCOIS has lines there."""
    days = sorted(Path("validation").glob("20*.csv"))
    totals = {name: [] for name in REGIONS}
    for path in days:
        for r in csv.DictReader(open(path)):
            if r["region"] in totals and r["hit_rate"]:
                totals[r["region"]].append(r)
    print(f"{len(days)} scored days: {days[0].stem} – {days[-1].stem}")
    print(f"{'region':<24}{'days':>6}{'hit':>7}{'prec':>7}{'points':>8}")
    for name, rs in totals.items():
        if rs:
            hit = sum(float(r["hit_rate"]) for r in rs) / len(rs)
            prec = sum(float(r["precision"] or 0) for r in rs) / len(rs)
            pts = sum(int(r["our_points"]) for r in rs) / len(rs)
            print(f"{name:<24}{len(rs):>6}{hit:>7.2f}{prec:>7.2f}{pts:>8.0f}")
        else:
            print(f"{name:<24}{0:>6}{'–':>7}{'–':>7}{'–':>8}")


if __name__ == "__main__":
    if sys.argv[1] == "--new":
        score_new()
    elif sys.argv[1] == "--summary":
        summary()
    else:
        compare(sys.argv[1])
