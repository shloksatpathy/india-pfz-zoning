import csv
import itertools
import sys
from collections import defaultdict
from pathlib import Path

import pfz
import validate
from regions import REGIONS

GRADS = [0.03, 0.05, 0.07, 0.10]  # °C/km
CHLS = [0.2, 0.3, 0.5, 1.0, 2.0]  # mg/m³
SCORES = {
    "grad": lambda z: z["grad"],
    "front_km": lambda z: z["front_km"],
    "grad_x_front": pfz.strength,
}
CAPS = [5, 10, 20, None]  # advisory points per region; None = no cap
MIN_HIT = 0.5  # pick the best precision among combinations reaching this hit rate


def chl_date_for(day):
    dates = sorted(p.stem.removeprefix("chl_n20_") for p in Path("data").glob("chl_n20_*.nc"))
    return max(d for d in dates if d <= day)


def sweep(days):
    rows = []
    for day in days:
        sst, chl, depth = pfz.load(day, chl_date_for(day))
        ocean = sst.notnull() & pfz.eez_mask(sst)
        grad = pfz.gradient(sst)
        extra = pfz.load_extra(day, sst)[0]
        segments = validate.incois_segments(f"validation/incois/{day}.geojson")
        for g, c in itertools.product(GRADS, CHLS):
            mask = (grad >= g) & (chl >= c) & ocean
            labels, ids = pfz.label_zones(mask, ocean)
            zones = pfz.describe_zones(sst, chl, depth, grad, mask, labels, ids, extra)
            for (score_name, score), cap in itertools.product(SCORES.items(), CAPS):
                pfz.rank_zones(zones, score, {name: cap for name in REGIONS})
                shown = [z for z in zones if z["points"] > 0]
                features = [{"geometry": z["geometry"], "properties": {"region": z["region"]}} for z in shown]
                points = [pt for z in shown for pt in z["point_list"]]
                for r in validate.score(segments, features, points):
                    rows.append({"day": day, "grad_min": g, "chl_min": c, "score": score_name, "cap": cap or "all", **r})
        print(f"{day} done", flush=True)

    with open("validation/sweep.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summarise(rows)


def summarise(rows):
    """Per region: mean over days on which INCOIS has lines there; best precision with hit >= MIN_HIT."""
    groups = defaultdict(list)
    for r in rows:
        if r["hit_rate"] != "" and r["region"] != "All":
            groups[(r["region"], r["grad_min"], r["chl_min"], r["score"], r["cap"])].append(r)
    means = defaultdict(list)
    for (region, *combo), rs in groups.items():
        hit = sum(r["hit_rate"] for r in rs) / len(rs)
        prec = sum(r["precision"] or 0 for r in rs) / len(rs)
        pts = sum(r["our_points"] for r in rs) / len(rs)
        means[region].append((combo, len(rs), hit, prec, pts))

    print(f"{'region':<24}{'days':>5}{'grad':>6}{'chl':>5}{'score':>14}{'cap':>5}{'hit':>6}{'prec':>6}{'pts':>5}")
    for region, combos in means.items():
        reaching = [m for m in combos if m[2] >= MIN_HIT]
        best = max(reaching, key=lambda m: (m[3], m[2])) if reaching else max(combos, key=lambda m: (m[2], m[3]))
        (g, c, score, cap), days, hit, prec, pts = best
        print(f"{region:<24}{days:>5}{g:>6}{c:>5}{score:>14}{cap!s:>5}{hit:>6.2f}{prec:>6.2f}{pts:>5.0f}")


if __name__ == "__main__":
    sweep(sys.argv[1:])
