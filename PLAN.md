# Plan

Goal: Potential Fishing Zones (PFZ) for India's coastal regions from satellite SST and chlorophyll-a, published as a weekly web map, checked against INCOIS advisories.

## Current system (phases 1 – 2, done)

```
run.py ──> fetch.py ──> data/sst_<date>.nc, chl_n20_<date>.nc, etopo.nc
              │
              v
           pfz.py ──> outputs/<SST date>/zones.csv, points.csv, zones.geojson,
              │       sst.png, chl.png, check.png, <region>.png
              v
outputs/index.json ──> site.py ──> docs/site/ ──> GitHub Pages (weekly.yml)

incois.py ──> validation/incois/<date>.geojson (daily, incois.yml)
validate.py, sweep.py ──> validation/<date>.csv, validation/sweep.csv
```

| File | Purpose |
|---|---|
| `regions.py` | Region boxes (map zoom, plots), download box, `THRESHOLDS` per region |
| `fetch.py` | MUR SST (`jplMURSST41`, PFEG ERDDAP), NOAA-20 NRT 7-day chlorophyll (`noaacwN20VIIRSchlaWeekly`, CoastWatch ERDDAP), ETOPO1 depth |
| `pfz.py` | Fronts ∩ productive water (per-pixel thresholds from the nearest harbour's region), EEZ clip, zones with holes, advisory points |
| `harbours.py` | 54 fishing harbours with region: DoF Handbook 2020 names, OpenStreetMap coordinates |
| `run.py` | `run.py last`: newest SST day + newest chlorophyll on or before it; ranges step 7 days |
| `site.py` | Latest 8 weeks in `docs/site/` with `web/index.html` and the EEZ |
| `incois.py` | Archives the current INCOIS PFZ lines (WFS layer `PFZ_Automation:pfzlines`) |
| `validate.py` | Per region: hit rate (INCOIS line length within 10 km of our zones) and precision (our points within 10 km of INCOIS lines) |
| `sweep.py` | `GRAD_MIN` × `CHL_MIN` grid scored against archived INCOIS days |
| `.github/workflows/weekly.yml` | Tuesdays: `run.py last` (3 tries), rebuild site, commit, deploy |
| `.github/workflows/incois.yml` | Daily 13:00 IST: archive INCOIS lines, commit |

Parameters:

| Parameter | Value | Where |
|---|---|---|
| `GRAD_MIN`, `CHL_MIN` | 0.05 °C/km, 0.3 mg/m³ in every region | `regions.py` `THRESHOLDS` |
| `DILATE`, `MIN_PIXELS` | 2 px, 50 px (~240 km²) | `pfz.py` |
| `POINT_TILE_KM`, `MIN_TILE_PIXELS` | 30 km, 20 px (~100 km²) | `pfz.py` |
| `MAX_HARBOUR_KM` | 300 km | `pfz.py` |

Published dates (2026-11-22): 2026-10-06 – 2026-11-20, 41 – 86 zones and 120 – 237 advisory points per date.

**Validation so far.** INCOIS archive: 2026-11-18 – 20 (west coast and islands, one Tamil Nadu day). Sweep means per region at `CHL_MIN` 0.3 (hit rate / precision / our points per day):

| Region (days with INCOIS lines) | grad 0.03 | grad 0.05 (current) | grad 0.07 |
|---|---|---|---|
| Gujarat (3) | 1.00 / 0.09 / 90 | 0.75 / 0.19 / 47 | 0.41 / 0.25 / 17 |
| Maharashtra & Goa (3) | 0.94 / 0.11 / 83 | 0.18 / 0.09 / 21 | 0.06 / 0.17 / 5 |
| Karnataka & Kerala (3) | 0.56 / 0.31 / 48 | 0.13 / 0.44 / 8 | 0.04 / 0.22 / 1 |
| Tamil Nadu & Puducherry (1) | 0.43 / 0.08 / 59 | 0.38 / 0.15 / 34 | 0.05 / 0.12 / 8 |
| Andaman & Nicobar (3) | 0.02 / 0.00 / 19 | 0.00 / 0.00 / 3 | 0.00 / 0.00 / 0 |
| Lakshadweep (2) | 0.00 / 0.00 / 1 | 0.00 / 0.00 / 0 | 0.00 / 0.00 / 0 |

- The gradient threshold dominates; `CHL_MIN` between 0.2 and 1.0 barely changes the west coast.
- Lowering `GRAD_MIN` catches most INCOIS lines but multiplies our points, so precision stays at or below 0.44 everywhere: we mark far more places than INCOIS does (INCOIS: 30 lines on 2026-11-18 across all regions).
- All three days used the same stalled chlorophyll (2026-11-09), so the results are preliminary.

## Phase 3: Fewer, ranked zones and final thresholds

Problem: the map shows every zone that passes the thresholds, so a fisher sees 100 – 240 points with no order of importance, and most of them have no INCOIS counterpart. Thresholds alone can raise hit rate or precision, not both.

### Step 1: Score every day automatically

So scores accumulate without manual runs.

- `validate.py` reads our published zones from `docs/site/outputs/` (already in the repo and in CI) instead of the local `outputs/`.
- `incois.yml`: after archiving, run `validate.py --new`, which scores every archived day without a `validation/<date>.csv` when a published date is within 3 days, and commit `validation/`. Maps go to the ignored `outputs/validation/`.
- `validate.py --summary`: mean hit rate and precision per region over all `validation/<date>.csv`, printed as a table, for PLAN.md updates.

### Step 2: Rank zones

Give each zone a strength so the strongest come first.

- In `describe_zones`, add per zone: `grad` (mean SST gradient over its front ∩ productive pixels, °C/km) and `front_km` (length of front pixels, ~pixel count × pixel size).
- Candidate scores, compared in step 4:
  - `grad` (front sharpness)
  - `front_km` (front length)
  - `grad × front_km`
- `rank`: 1 = strongest within its region; stored in `zones.csv`, `points.csv` and `zones.geojson`.

### Step 3: Cap points per region

INCOIS issues about 1 – 14 lines per region per day, while we issue up to ~90 points.

- `MAX_POINTS` per region in `regions.py` (start: all, i.e. no cap). Points are taken from zones in rank order until the cap; lower-ranked zones stay in `zones.geojson` with `rank` but get no advisory points.
- Web page: list sorted by rank within the selected region; a "Show all zones" toggle shows unranked zones as outlines only.

### Step 4: Sweep with ranking and cap

- Extend `sweep.py` with the score (step 2) and `MAX_POINTS` 5 / 10 / 20 / all as extra dimensions; keep `GRAD_MIN` and `CHL_MIN` dimensions.
- Pick, per region, the combination with the best precision at a hit rate of at least ~0.5 (or the best hit rate where 0.5 is out of reach).
- First run on the archive available then (preliminary); record the table here.

### Step 5: Choose values (after ~3 weeks of archive, ≈ 2026-12-09)

- Rerun the step 4 sweep on all archived days, ideally with chlorophyll updating again (check `chl_date` in `docs/site/outputs/index.json`).
- Set `THRESHOLDS`, `MAX_POINTS` and the ranking score in the code; rebuild `docs/site` for the 8 published weeks; record the final sweep table and values here.
- Check that east coast regions have enough INCOIS days to tune; otherwise keep the phase 1 values there and say so.

### Step 6: Lakshadweep

Hit rate is 0 at every setting.

- Plot INCOIS Lakshadweep lines over our SST gradient and chlorophyll for each archived day (`validate.py` maps plus `check.png`).
- Find out whether the lines follow weaker fronts than 0.03 °C/km, sit in chlorophyll gaps, or follow something we do not detect; decide on a region-specific rule or record it as a limitation.

### Milestones

1. ~~Daily automatic scoring in `incois.yml`; `validate.py --summary`.~~ Done 2026-11-22: `validate.py --new` scores every archived day without a `validation/<date>.csv` against `docs/site/outputs/` (days with no published date within 3 days wait for a later one). 3 days scored so far.
2. Zone strength scores and per-region `rank`.
3. `MAX_POINTS` cap; web list by rank with "Show all zones".
4. Sweep over score × cap × thresholds; preliminary table.
5. Final per-region values (≈ 2026-12-09 or later); site rebuilt.
6. Lakshadweep investigation.

## Known limitations

- **Monsoon cloud cover (Jun – Sep):** VIIRS chlorophyll has large gaps; expect few or no zones. MUR SST is gap-filled, so fronts still appear.
- **Fishing ban periods:** East coast 15 Apr – 31 May, West coast 1 Jun – 31 Jul. Outputs are produced but not actionable.
- **Near-real-time chlorophyll:** 4 – 10 days old when updating, lower quality than the science-quality product, and it can stall: it stayed at 2026-11-09 through at least 2026-11-22.
- **ERDDAP access from GitHub:** PFEG ERDDAP answered HTTP 403 to GitHub runners for a while on 2026-11-19; the weekly job retries 3 times.
- **Advisory points are tile-based:** spread over the zone on a ~30 km grid, not traced along the front line.
- **Distances are straight-line** from harbour to point and can cross land (e.g. around Kathiawar or Sri Lanka).
- **Harbours missing:** Agro, Dholai, Pazhayar, Roychowk and Petuaghat could not be located in OpenStreetMap; zones off Daman count as Maharashtra & Goa (nearest listed harbour Mumbai).
- **INCOIS comparison is one-sided:** INCOIS lines are drawn by analysts and may skip valid fronts, so low precision is not only our error.

## Later

- Rolling median of NOAA-20 daily NRT chlorophyll (~4 days old) and a staleness warning on the page when the composite stalls.
- Regional languages for advisory text and the page; SMS / WhatsApp alerts.
