import csv
import itertools
import sys
from collections import defaultdict
from pathlib import Path

import pfz
import validate

GRADS = [0.03, 0.05, 0.07, 0.10]  # °C/km
CHLS = [0.2, 0.3, 0.5, 1.0, 2.0]  # mg/m³


def chl_date_for(day):
    dates = sorted(p.stem.removeprefix("chl_n20_") for p in Path("data").glob("chl_n20_*.nc"))
    return max(d for d in dates if d <= day)


def sweep(days):
    rows = []
    for day in days:
        sst, chl, depth = pfz.load(day, chl_date_for(day))
        ocean = sst.notnull() & pfz.eez_mask(sst)
        grad = pfz.sst_gradient(sst)
        segments = validate.incois_segments(f"validation/incois/{day}.geojson")
        for g, c in itertools.product(GRADS, CHLS):
            mask = (grad >= g) & (chl >= c) & ocean
            labels, ids = pfz.label_zones(mask, ocean)
            zones = pfz.describe_zones(sst, chl, depth, mask, labels, ids)
            features = [{"geometry": z["geometry"], "properties": {"region": z["region"]}} for z in zones]
            points = [pt for z in zones for pt in z["point_list"]]
            for r in validate.score(segments, features, points):
                rows.append({"day": day, "grad_min": g, "chl_min": c, **r})
        print(f"{day} done", flush=True)

    with open("validation/sweep.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summarise(rows)


def summarise(rows):
    """Mean over days on which INCOIS has lines in the region."""
    groups = defaultdict(list)
    for r in rows:
        if r["hit_rate"] != "" and r["region"] != "All":
            groups[(r["region"], r["grad_min"], r["chl_min"])].append(r)
    print(f"{'region':<24}{'grad':>6}{'chl':>6}{'days':>6}{'hit':>7}{'prec':>7}{'points':>8}")
    for (region, g, c), rs in sorted(groups.items()):
        hit = sum(r["hit_rate"] for r in rs) / len(rs)
        prec = sum(r["precision"] or 0 for r in rs) / len(rs)
        pts = sum(r["our_points"] for r in rs) / len(rs)
        print(f"{region:<24}{g:>6}{c:>6}{len(rs):>6}{hit:>7.2f}{prec:>7.2f}{pts:>8.0f}")


if __name__ == "__main__":
    sweep(sys.argv[1:])
