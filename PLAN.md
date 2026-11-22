# Plan

Goal: Potential Fishing Zones (PFZ) for India's coastal regions from satellite SST and chlorophyll-a, published as a weekly web map, checked against INCOIS advisories.

## Current system (phases 1 – 3, done except final values)

```
run.py ──> fetch.py ──> data/sst_<date>.nc, chl_n20_<date>.nc, etopo.nc
              │
              v
           pfz.py ──> outputs/<SST date>/zones.csv, points.csv, zones.geojson,
              │       sst.png, chl.png, check.png, <region>.png
              v
outputs/index.json ──> site.py ──> docs/site/ ──> GitHub Pages (weekly.yml, deploy.yml)

incois.py ──> validation/incois/<date>.geojson ──> validate.py ──> validation/<date>.csv  (daily, incois.yml)
sweep.py ──> validation/sweep.csv
```

| File | Purpose |
|---|---|
| `regions.py` | Region boxes (map zoom, plots), download box, `THRESHOLDS` and `MAX_POINTS` per region |
| `fetch.py` | MUR SST (`jplMURSST41`, PFEG ERDDAP), NOAA-20 NRT 7-day chlorophyll (`noaacwN20VIIRSchlaWeekly`, CoastWatch ERDDAP), ETOPO1 depth |
| `pfz.py` | Fronts ∩ productive water (per-pixel thresholds from the nearest harbour's region), EEZ clip, zones with holes, ranking (`rank_zones`), advisory points |
| `harbours.py` | 54 fishing harbours with region: DoF Handbook 2020 names, OpenStreetMap coordinates |
| `run.py` | `run.py last`: newest SST day + newest chlorophyll on or before it; ranges step 7 days |
| `site.py` | Latest 8 weeks in `docs/site/` with `web/index.html` and the EEZ |
| `incois.py` | Archives the current INCOIS PFZ lines (WFS layer `PFZ_Automation:pfzlines`) |
| `validate.py` | `--new`: per region hit rate (INCOIS line length within 10 km of our zones with points) and precision (our points within 10 km of INCOIS lines); `--summary` |
| `sweep.py` | `GRAD_MIN` × `CHL_MIN` × ranking score × point cap, scored against archived INCOIS days |
| `.github/workflows/weekly.yml` | Tuesdays: `run.py last` (3 tries), rebuild site, commit, deploy |
| `.github/workflows/incois.yml` | Daily 13:00 IST: archive INCOIS lines, score new days, commit |
| `.github/workflows/deploy.yml` | Deploys the committed `docs/site` on every push that changes it |

Parameters:

| Parameter | Value | Where |
|---|---|---|
| `GRAD_MIN`, `CHL_MIN` | 0.05 °C/km, 0.3 mg/m³ in every region | `regions.py` `THRESHOLDS` |
| `MAX_POINTS` | `None` (no cap) in every region | `regions.py` |
| Ranking score | `grad × front_km` | `pfz.py` `strength` |
| `DILATE`, `MIN_PIXELS` | 2 px, 50 px (~240 km²) | `pfz.py` |
| `POINT_TILE_KM`, `MIN_TILE_PIXELS` | 30 km, 20 px (~100 km²) | `pfz.py` |
| `MAX_HARBOUR_KM` | 300 km | `pfz.py` |

Published dates (2026-11-22): 2026-10-06 – 2026-11-20, 41 – 86 zones and 120 – 237 advisory points per date. The page lists zones by region and rank, with "Show all zones" for zones without points.

**Validation so far** (INCOIS 2026-11-18 – 20, one stalled chlorophyll composite, so preliminary). Best combination per region from `sweep.py` (best precision with hit rate ≥ 0.5, else best hit rate):

| Region (days) | Current: hit / prec / points | Best: grad, chl, score, cap | Best: hit / prec / points |
|---|---|---|---|
| Gujarat (3) | 0.75 / 0.19 / 47 | 0.05, 0.2, grad, 10 | 0.50 / 0.37 / 10 |
| Maharashtra & Goa (3) | 0.18 / 0.09 / 21 | 0.03, 1.0, front_km, 5 | 0.57 / 0.40 / 5 |
| Karnataka & Kerala (3) | 0.13 / 0.44 / 8 | 0.03, 0.3, grad, all | 0.56 / 0.31 / 48 |
| Tamil Nadu & Puducherry (1) | 0.38 / 0.15 / 34 | 0.03, 0.2, grad, all | 0.45 / 0.04 / 120 |
| Andaman & Nicobar (3) | 0.00 / 0.00 / 3 | 0.03, 0.2, grad, all | 0.53 / 0.01 / 102 |
| Lakshadweep (2) | 0.00 / 0.00 / 0 | – | 0.00 everywhere |

- Ranking plus a cap doubles precision in Gujarat and Maharashtra & Goa with 5 – 10 points per region.
- Lakshadweep cannot be matched: INCOIS lines there lie on SST gradients of 0.005 – 0.023 °C/km with low, often cloud-masked chlorophyll; thresholds low enough to reach them mark 30,000 – 166,000 km² at precision ≤ 0.02. Regular thresholds stay.

## Phase 4: Fresher chlorophyll, accurate advisories, final values

Problems (2026-11-22):
- **Chlorophyll is 2 weeks old.** The NOAA-20 NRT 7-day composite has stayed at 2026-11-09 since at least 2026-11-19, while SST is current to 2026-11-20.
- **Distances cross land.** Advisory distances are straight lines, so a zone in the Gulf of Kutch can be measured from Veraval across Kathiawar, and Palk Bay zones across Sri Lanka. The nearest harbour is chosen the same way.
- **Harbours missing:** Agro, Dholai, Pazhayar, Roychowk and Petuaghat (not found in OpenStreetMap).

Chlorophyll options checked on 2026-11-22 (CoastWatch ERDDAP; all `chlor_a` on the same 0.0375° grid with `time, altitude, latitude, longitude`):

| Dataset | Sensor | Newest | One-day coverage of the box's ocean |
|---|---|---|---|
| `noaacwN20VIIRSchlaWeekly` (current) | NOAA-20 VIIRS, 7-day | 2026-11-09 | ~87% |
| `noaacwN20VIIRSchlaDaily` | NOAA-20 VIIRS | 2026-11-15 | 10 – 47% |
| `noaacwNPPVIIRSchlaDaily` | S-NPP VIIRS | 2026-11-13 | – |
| `noaacwS3AOLCIchlaDaily` | Sentinel-3A OLCI | 2026-11-19 | ~26% (2026-11-19) |
| `noaacwS3BOLCIchlaDaily` | Sentinel-3B OLCI | 2026-11-19 | < 1% (2026-11-19) |

### Step 1: Multi-sensor chlorophyll composite

- `fetch.py`: for the 7 days ending at the SST date, download each available day of the four daily datasets above (up to 28 files, ~1.5 MB each) to `data/chl_<sensor>_<date>.nc`.
- `pfz.py`: chlorophyll = per-pixel median over all downloaded days and sensors; `chl_date` = newest day used. Record the days and sensors used and the ocean coverage share in `zones.geojson` and `index.json`.
- Check the sensors agree before mixing: median OLCI / VIIRS ratio on pixels both see. If it is beyond ~±20%, record it and decide (scale OLCI or drop it).
- Compare with the current weekly composite on the archived INCOIS days at current settings (`validate.py` scores, coverage, age). Switch only if coverage and scores are at least as good.
- Keep the weekly composite in the code path until the switch is decided.

### Step 2: Staleness warning

- `web/index.html`: when `sst_date − chl_date` is more than 10 days, show a warning line above the list ("Chlorophyll is N days older than SST").
- `site.py` / `index.json`: nothing new needed, both dates are already there.

### Step 3: Missing harbours from INCOIS landing centres

- INCOIS publishes 1,223 landing centres with coordinates (WFS layer `PFZ_LandingCentres:LandingCenters_29Apr2024`, the layer behind their PFZ WebGIS page). It has Dholai (20.74 °N, 72.90 °E), Pazhayar (11.35 °N, 79.83 °E) and Petuaghat (21.79 °N, 87.88 °E).
- Add these three to `harbours.py` with the source in the header. Roychowk is not in the layer and "Agro" stays ambiguous, so both remain missing.
- Expected effect: zones off Daman go back to Gujarat (Dholai), Palk Bay / Cauvery delta zones get a closer Tamil Nadu harbour.

### Step 4: Sea-route distances

- Build an ocean grid at ~0.05° from the MUR land mask (land = NaN SST), 8-connected, and run `scipy.sparse.csgraph.dijkstra` from every harbour (snapped to the nearest ocean cell). Cache the distance fields in `data/sea_km.npz` (rebuilt when `harbours.py` changes).
- Advisory distance = sea-route km; the nearest harbour (and therefore region and per-pixel thresholds) = smallest sea-route distance. Bearing stays the straight compass direction from the harbour, as in INCOIS advisories.
- Check cases: Gulf of Kutch zones (Jakhau vs Veraval), Gulf of Khambhat, Palk Bay, Andaman east coast. Record how many points change harbour and by how much the distance changes.

### Step 5: Final per-region values (carried over from phase 3, ≈ 2026-12-09)

- Needs ~3 weeks of INCOIS archive and the chlorophyll source decided in step 1, since thresholds depend on it.
- Download SST for every archived INCOIS day, rerun `sweep.py` on all of them with the chosen chlorophyll source.
- Set `THRESHOLDS`, `MAX_POINTS` and the ranking score; regions with fewer than 5 INCOIS days, and Lakshadweep, keep the phase 1 values. Rebuild the 8 published weeks; record the final table and values here.

### Milestones

1. Multi-sensor 7-day chlorophyll median; comparison with the weekly composite; switch decision.
2. Staleness warning on the page.
3. Dholai, Pazhayar, Petuaghat from INCOIS landing centres.
4. Sea-route distances and nearest harbour by sea.
5. Final per-region thresholds, cap and ranking score (≈ 2026-12-09 or later); site rebuilt.

## Known limitations

- **Monsoon cloud cover (Jun – Sep):** satellite chlorophyll has large gaps; expect few or no zones. MUR SST is gap-filled, so fronts still appear.
- **Fishing ban periods:** East coast 15 Apr – 31 May, West coast 1 Jun – 31 Jul. Outputs are produced but not actionable.
- **Near-real-time chlorophyll:** lower quality than science-quality products, and NOAA's NRT products can stall (NOAA-20 7-day at 2026-11-09 through at least 2026-11-22).
- **ERDDAP access from GitHub:** PFEG ERDDAP answers HTTP 403 to GitHub runners at times (2026-11-19, 2026-11-22; `upwell.pfeg.noaa.gov` forwards to the same server). The weekly job retries 3 times; when it still fails, the site keeps the last committed data, and `deploy.yml` publishes any `docs/site` change pushed by hand.
- **Advisory points are tile-based:** spread over the zone on a ~30 km grid, not traced along the front line.
- **Lakshadweep:** INCOIS lines there follow very weak SST gradients and low or cloud-masked chlorophyll; our method finds no matching zones.
- **INCOIS comparison is one-sided:** INCOIS lines are drawn by analysts and may skip valid fronts, so low precision is not only our error.

## Later

- Regional languages for advisory text and the page; SMS / WhatsApp alerts.
- Compare our advisories with INCOIS per landing centre (the landing-centre layer carries INCOIS's own direction, distance and depth ranges).
