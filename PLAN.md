# Plan

Goal: Potential Fishing Zones (PFZ) for India's coastal regions from satellite SST and chlorophyll-a, published as a weekly web map, checked against INCOIS advisories.

## Current system (phases 1 – 4, done except final values)

```
run.py ──> fetch.py ──> data/sst_<date>.nc, chl_n20_<date>.nc, etopo.nc
              │
              v
           pfz.py ──> outputs/<SST date>/zones.csv, points.csv, zones.geojson,
              │       sst.png, chl.png, check.png, <region>.png
              │  sea.py (sea_mask.npz): nearest harbour and distance by sea
              v
outputs/index.json ──> site.py ──> docs/site/ ──> GitHub Pages (weekly.yml, deploy.yml)

incois.py ──> validation/incois/<date>.geojson ──> validate.py ──> validation/<date>.csv  (daily, incois.yml)
sweep.py ──> validation/sweep.csv
```

| File | Purpose |
|---|---|
| `regions.py` | Region boxes (map zoom, plots), download box, `THRESHOLDS` and `MAX_POINTS` per region |
| `fetch.py` | MUR SST (`jplMURSST41`, PFEG ERDDAP), NOAA-20 NRT 7-day chlorophyll (`noaacwN20VIIRSchlaWeekly`, CoastWatch ERDDAP), the four daily chlorophyll datasets (`fetch_daily_chl`), ETOPO1 depth |
| `pfz.py` | Fronts ∩ productive water (per-pixel thresholds from the nearest harbour's region), EEZ clip, zones with holes, ranking (`rank_zones`), advisory points; `daily_chl` = multi-sensor median (not used in production) |
| `sea.py` | Sea-route distance and nearest harbour by sea (Dijkstra over a 0.04° ocean grid, `sea_mask.npz`) |
| `harbours.py` | 57 fishing harbours with region: DoF Handbook 2020 names, OpenStreetMap coordinates (3 from INCOIS landing centres) |
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
| `MAX_HARBOUR_KM` | 300 km by sea | `pfz.py` |
| `STALE_DAYS` | 10 days (page warning when chlorophyll is older than SST by more) | `web/index.html` |

Published dates (2026-11-22): 2026-10-06 – 2026-11-20, 41 – 86 zones and 120 – 237 advisory points per date. The page lists zones by region and rank, with "Show all zones" for zones without points, and warns when chlorophyll is stale.

**Phase 4 results (2026-11-22):**
- Multi-sensor 7-day chlorophyll median (NOAA-20 + S-NPP VIIRS, Sentinel-3A/B OLCI daily): 0 – 1 days old and 86 – 97% coverage against 9 – 11 days and 83% for the weekly composite; scores against INCOIS tie; OLCI reads 16 – 20% below VIIRS. Kept out of production.
- Dholai, Pazhayar, Petuaghat added from INCOIS landing centres: 13 zones off Daman back to Gujarat.
- Distances, nearest harbour, region and thresholds by sea route: 82 of 1,434 points changed harbour; Gulf of Kutch points now measured from Jakhau instead of across Kathiawar.

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

## Phase 5: Chlorophyll source rule, more ocean parameters, final values

Problems (2026-11-23):
- **Chlorophyll stall.** The NOAA-20 7-day composite is still at 2026-11-09 (14 days behind); the next Tuesday run would publish chlorophyll 13 days older than SST. The daily datasets are newer: NOAA-20 and S-NPP VIIRS 2026-11-15, Sentinel-3A/B OLCI 2026-11-20.
- **Zones use two parameters only.** Fronts and chlorophyll find productive water but say nothing about eddies, upwelling, currents, river plumes or whether the sea is safe to go out.
- **INCOIS archive is still 3 days.** INCOIS has published no new lines since 2026-11-20 (Julian day 324), so the final values (carried over) still wait.

Other parameters checked on 2026-11-23 (NOAA ERDDAP; all cover the download box):

| Parameter | Dataset | Server | Grid | Newest | Variables |
|---|---|---|---|---|---|
| Sea level anomaly | `noaacwBLENDEDsshDaily` (altimetry, NRT) | CoastWatch | 0.25° | 2026-11-21 | `sla` (m) |
| Geostrophic currents | `noaacwBLENDEDNRTcurrentsDaily` | CoastWatch | 0.25° | 2026-11-20 | `u_current`, `v_current` (m/s) |
| Wind, Ekman upwelling | `erdQCwindproducts3day` (Metop-C ASCAT, 3-day) | PFEG | 0.33° | 2026-11-20 | `wind_speed`, `ekman_upwelling` (m/s) |
| Sea surface salinity | `noaacwSMAPsssDaily` (SMAP, NRT) | CoastWatch | 0.25° | 2026-11-21 | `sss` (PSU) |
| Chlorophyll fronts | derived from the chlorophyll already downloaded | – | 0.02° | – | – |

Not usable: mixed-layer depth (HYCOM on PFEG ends in 2018), `nesdisSSH1day` (ends 2026-09-28), NCEI blended NRT winds (end 2023-03-05), the eddy significance index `noaacweddymesidaily` (2026-11-03).

How the new parameters are used (decided 2026-11-23): zones are still found from SST fronts and chlorophyll. Each zone and point gets the new values as attributes on the page and in the CSVs, and they enter the ranking score. INCOIS lines come from SST and chlorophyll only, so the sweep can show only that a factor does not lower agreement, not that it helps; a factor goes into the final score only if it does not lower agreement.

### Step 1: Chlorophyll source rule

- `run.py` / `pfz.py`: use the weekly composite when `sst_date − chl_date ≤ STALE_DAYS` (10, the page's warning limit); otherwise use the multi-sensor 7-day median (`fetch_daily_chl` + `pfz.daily_chl`), with `chl_date` = newest day used.
- Record the source (`weekly` / `median`) in `zones.geojson` and `index.json`; the page shows it in the dates line ("Chlorophyll: 7-day composite dated …" or "Chlorophyll: 4-sensor median, … – …"). The staleness warning stays.
- No OLCI scaling (16 – 20% low against VIIRS, within the median's spread); revisit only if a median week scores clearly below the weekly weeks.
- Rebuild the published weeks whose chlorophyll is more than 10 days older than SST (2026-11-20 now; the weekly run of 2026-11-24 picks the median by itself).

### Step 2: Chlorophyll fronts

- `pfz.py`: gradient of log10 chlorophyll on the SST grid (same `km_xy` spacing as the SST gradient), per zone `chl_front_km` = length of zone pixels above a gradient threshold.
- Pick the threshold from its distribution over the 8 published weeks (e.g. the 90th percentile over ocean pixels); record it here.
- Zone attribute `chl_front_km`; candidate ranking factor.

### Step 3: Sea level anomaly and eddies

- `fetch.py`: `sla` for the SST date from `noaacwBLENDEDsshDaily` (`data/sla_<date>.nc`, ~75 × 115 cells).
- `pfz.py`: bilinear interpolation onto the SST grid. Per zone: mean `sla` (cm) and an eddy label: cyclonic (`sla ≤ −5 cm`), anticyclonic (`≥ +5 cm`) or none. Eddy edges: share of the zone where the SLA gradient is in the top 10%.
- Candidate ranking factors: cyclonic or eddy-edge zones up. Check cases: the Bay of Bengal (strong eddies in Nov – Dec), the Arabian Sea off Gujarat.

### Step 4: Wind and upwelling

- `fetch.py`: `wind_speed` and `ekman_upwelling` for the SST date from `erdQCwindproducts3day` (PFEG, same 403 risk and retries as SST; `data/wind_<date>.nc`).
- Per zone and point: mean wind speed (m/s) and Ekman upwelling (m/day, positive = upwelling).
- Page: a "strong wind" note on zones and points where wind ≥ 10 m/s (~20 knots, Beaufort 5); zones are not dropped. The note says to check the INCOIS ocean state forecast.
- Candidate ranking factor: upwelling > 0. Expected along the southwest coast (Karnataka & Kerala) only in the monsoon months; check its sign there now.

### Step 5: Currents and salinity

- `fetch.py`: `u_current`, `v_current` from `noaacwBLENDEDNRTcurrentsDaily` and `sss` from `noaacwSMAPsssDaily` (`data/cur_<date>.nc`, `data/sss_<date>.nc`), each the newest day on or before the SST date.
- Per point: current speed (knots) and the compass direction it flows to, shown in the advisory popup ("current 0.6 kn to NE"), so boats know which way a zone drifts.
- Per zone: mean salinity (PSU); a river plume note where `sss < 32` (Bay of Bengal off Odisha and West Bengal, Ganges – Brahmaputra outflow). Candidate ranking factor: salinity front (salinity gradient) inside the zone.

### Step 6: Outputs and page

- `zones.csv`, `points.csv`, `zones.geojson`: new columns `chl_front_km`, `sla_cm`, `eddy`, `wind_ms`, `upwelling_m_day`, `sss`, and per point `current_kn`, `current_to`.
- Popups and list lines show the values; the footer names the new sources. Keep per-date data under ~1 MB.
- `sweep.py`: `SCORES` gains `grad × front_km` multiplied by each factor (1 + share of the zone that is eddy edge, upwelling, chlorophyll front or salinity front) and their product.

### Step 7: Final per-region values (carried over, ≈ 2026-12-09 or later)

- Needs ~3 weeks of INCOIS archive. Chlorophyll source per day: the step 1 rule.
- Download SST, chlorophyll and the new parameters for every archived INCOIS day; rerun `sweep.py` on all of them.
- Set `THRESHOLDS`, `MAX_POINTS` and the ranking score (with whichever factors do not lower agreement); regions with fewer than 5 INCOIS days, and Lakshadweep, keep the phase 1 values. Rebuild the 8 published weeks; record the final table and values here.

### Milestones

1. ~~Chlorophyll source rule; stale week(s) rebuilt with the median.~~ Done 2026-11-23. `run.py` uses the weekly composite when it is at most `STALE_DAYS` = 10 days older than SST, else `fetch_daily_chl` + `pfz.daily_chl`; `zones.geojson` and `index.json` carry `chl_source` and `chl_days`, and the page names the source and sensors. Of the 8 published weeks only 2026-11-20 switched (weekly 2026-11-09 → median of 17 daily images 2026-11-14 – 20, 90% ocean coverage): 84 → 87 zones, 235 → 212 points. INCOIS scores on the days matched to it, all regions, hit / precision: 2026-11-19 0.39 / 0.10 → 0.45 / 0.13, 2026-11-20 0.27 / 0.07 → 0.32 / 0.08 (Karnataka & Kerala 0.28 → 0.44 and 0.19 → 0.28 hit). The other 7 weeks are unchanged.
2. ~~Chlorophyll fronts as a zone attribute.~~ Done 2026-11-23. `pfz.chl_gradient`: gradient of log10 chlorophyll on a 0.04° grid (2 × 2 mean of the SST-grid chlorophyll, close to its 0.0375° source), back on the SST grid. Its 90th percentile over ocean pixels is 0.017 – 0.024 per km in all 8 published weeks, so `CHL_FRONT_MIN` = 0.02 log10(mg/m³)/km (~5% change per km). `chl_front_km` = front pixels × pixel width anywhere in the zone (new `zones.csv` column). Over the 8 weeks (532 zones): 84% of zones have a chlorophyll front, median 69 km, 90th percentile 296 km; Spearman correlation with the current strength 0.51, so it adds information rather than repeating the SST front.
3. ~~Sea level anomaly and eddy labels.~~ Done 2026-11-23. `fetch.fetch_extra` downloads the newest day on or before the SST date of each `EXTRA` dataset (`data/sla_<SST date>.nc`, 75 KB); `pfz.load_extra` returns the grids on the SST grid and their dates (`extra_dates` in `zones.geojson`). The raw SLA carries a basin-wide offset (median +5 cm over the box), so a fixed ±5 cm would mark half the sea anticyclonic. Eddy anomaly = SLA minus its mean over a 17-cell (~4°) window: ±5 cm then marks ~10% of the sea cyclonic and ~13% anticyclonic. Eddy edge = SLA gradient ≥ 0.14 cm/km (its 90th percentile, stable 0.12 – 0.16 over the 8 weeks). New `zones.csv` columns: `sla_cm` (local anomaly), `eddy` (cyclonic / anticyclonic / none, empty without altimetry), `eddy_edge` (share of the zone). Over the 8 weeks (532 zones): 68 cyclonic, 117 anticyclonic, 325 none, 22 without data (coastal). Odisha & West Bengal and Andhra Pradesh have the most eddy zones; Lakshadweep and Andaman none. 37% of zones touch an eddy edge. Map: `docs/images/sla_2026-11-20.png` (cyclonic eddies at ~15 °N 85 °E and ~11 °N 82 °E). Coastal caveats: a positive band along the Andhra coast (likely the real November coastal sea level rise) and ±15 cm strips in the Gulf of Khambhat (shallow-water altimetry error).
4. ~~Wind and upwelling.~~ Done 2026-11-23 (the page note moves to milestone 6 with the other page changes). `EXTRA["wind"]`: `wind_speed` and `ekman_upwelling` from `erdQCwindproducts3day` (PFEG, 68 KB per date; ascending latitude queries work on its descending axis). ASCAT masks cells near the coast, which left 38% of advisory points without wind, so the wind grid's gaps take the nearest ocean cell's value before interpolation (`pfz.fill_nearest`); upwelling is not filled. New columns: zones `wind_ms`, `upwelling_m_day` (Ekman, × 86,400 from m/s); points `wind_ms`. Over the 8 weeks: point wind median 4.8 m/s, 90th percentile 7.4, max 12.1; 15 of 1,411 points ≥ 10 m/s (14 of them off Odisha on 2026-11-17). Upwelling per zone: 10th – 90th percentile −0.64 to +0.64 m/day, positive in 46% of zones (Andaman 70%, Maharashtra & Goa 67%, Gujarat 28%), as expected outside the monsoon.
5. Currents and salinity.
6. New columns, popups and sweep scores.
7. Final per-region thresholds, cap and ranking score; site rebuilt.

## Known limitations

- **Monsoon cloud cover (Jun – Sep):** satellite chlorophyll has large gaps; expect few or no zones. MUR SST is gap-filled, so fronts still appear.
- **Fishing ban periods:** East coast 15 Apr – 31 May, West coast 1 Jun – 31 Jul. Outputs are produced but not actionable.
- **Near-real-time chlorophyll:** lower quality than science-quality products, and NOAA's NRT products can stall (NOAA-20 7-day at 2026-11-09 through at least 2026-11-23).
- **ERDDAP access from GitHub:** PFEG ERDDAP answers HTTP 403 to GitHub runners at times (2026-11-19, 2026-11-22; `upwell.pfeg.noaa.gov` forwards to the same server). The weekly job retries 3 times; when it still fails, the site keeps the last committed data, and `deploy.yml` publishes any `docs/site` change pushed by hand.
- **Advisory points are tile-based:** spread over the zone on a ~30 km grid, not traced along the front line.
- **Lakshadweep:** INCOIS lines there follow very weak SST gradients and low or cloud-masked chlorophyll; our method finds no matching zones.
- **INCOIS comparison is one-sided:** INCOIS lines are drawn by analysts and may skip valid fronts, so low precision is not only our error. It also cannot confirm parameters INCOIS does not use (eddies, wind, currents, salinity).
- **Altimetry near the coast:** sea level in shallow gulfs (Khambhat, Kutch) shows strong strips that are likely errors, so eddy labels there are unreliable.
- **Coarse extra parameters:** sea level, currents, salinity and wind are 0.25 – 0.33° (~28 – 37 km), coarser than the 0.02° fronts; they describe a zone's surroundings, not its edges, and are missing within ~25 km of the coast for altimetry and SMAP.

## Later

- Regional languages for advisory text and the page; SMS / WhatsApp alerts.
- Compare our advisories with INCOIS per landing centre (the landing-centre layer carries INCOIS's own direction, distance and depth ranges).
- Mixed-layer depth from a current ocean model (none on NOAA ERDDAP).
