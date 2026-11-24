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
5. ~~Currents and salinity.~~ Done 2026-11-23. `EXTRA` entries now carry a day count; `fetch_extra` asks for that many newest days in one query. Salinity: one SMAP day covers 37 – 86% of the sea (2026-11-14 – 20), the mean of 3 days ~97%, SMOS 3-day only 7%, so `sss` = mean of the 3 newest SMAP days. Salinity front = gradient ≥ `SSS_FRONT_MIN` = 0.05 PSU/km (its 90th percentile, 0.042 – 0.059). Currents: geostrophic, bilinear, not filled; 83% of points get a value (median 0.4 kn, 99th percentile 2.3, max 3.3; 5 – 13 kn spikes sit on coasts outside our points). New columns: zones `sss`, `sss_front` (share of the zone); points `current_kn`, `current_to` (compass direction the water flows to). Zone salinity medians: Odisha & West Bengal 22.3, Andhra Pradesh 25.8, Tamil Nadu 30.5, Andaman 30.0, west coast 34.9 – 35.9 PSU; 194 of 532 zones are below 32 PSU, i.e. nearly every east coast zone in the post-monsoon freshening, so a "< 32 PSU" plume note would mark the whole east coast; the note threshold is set in milestone 6. 25% of zones touch a salinity front. Per-date site data 0.87 MB (2026-11-20).
6. ~~New columns, popups and sweep scores.~~ Done 2026-11-23. Zone popups show chlorophyll front length, eddy label with the local sea level anomaly, wind, upwelling / downwelling and salinity; point popups and list lines show wind and current ("current 0.6 kn to NE"); a "strong wind" note (≥ 10 m/s) points to the INCOIS ocean state forecast. No river plume note: below 32 PSU covers nearly the whole east coast in Oct – Nov, so the salinity value is shown instead. The footer names the new sources. `run.choose_chl` holds the chlorophyll rule for both `run.py` and `sweep.py` (so the sweep uses the median on 2026-11-20). `sweep.py` scores: `x_chl_front` = grad × (front_km + chl_front_km), `x_eddy` × (1 + eddy_edge + cyclonic), `x_upwelling` × (1 + upwelling > 0), `x_sss_front` × (1 + sss_front), `x_all` = all four. Mean over regions with INCOIS lines (Lakshadweep excluded) and the 3 archived days, hit / precision:

   | Thresholds, cap | grad × front_km | x_chl_front | x_eddy | x_upwelling | x_sss_front | x_all |
   |---|---|---|---|---|---|---|
   | 0.05 / 0.3, 5 | 0.14 / 0.25 | 0.14 / 0.22 | 0.13 / 0.22 | 0.15 / 0.26 | 0.14 / 0.25 | 0.14 / 0.23 |
   | 0.05 / 0.3, 10 | 0.15 / 0.23 | 0.16 / 0.23 | 0.15 / 0.22 | 0.15 / 0.24 | 0.15 / 0.23 | 0.16 / 0.23 |
   | 0.05 / 0.3, 20 | 0.18 / 0.19 | 0.20 / 0.19 | 0.18 / 0.19 | 0.18 / 0.19 | 0.18 / 0.19 | 0.19 / 0.19 |

   All within ±0.03 of the current score on 3 days, as expected since INCOIS lines use SST and chlorophyll only; eddies lower precision slightly at cap 5. Best per region now: Gujarat 0.03 / 0.3, `x_chl_front`, cap 20 (hit 0.88, precision 0.30); other regions keep `grad`. The choice waits for step 7.
7. Final per-region thresholds, cap and ranking score; site rebuilt.

## Phases 6 – 8: Ship traffic and a guidance interface

Goal: show ship traffic around a selected region next to the PFZ zones, and turn the page into a guidance tool. A fisher picks a harbour or region, sees the zones, the vessels and shipping lanes around them, and gets a route to a chosen point with warnings.

Split:
- **Phase 6, traffic data:** gridded weekly traffic (fishing vs merchant) per region, as a map layer and as zone and point attributes; check whether fishing effort concentrates in our zones.
- **Phase 7, interactive region view:** select a region or zone, side panel, layer toggles, time slider, near-live vessel positions.
- **Phase 8, guidance:** route from harbour to point by sea that avoids shipping lanes, with distance, heading, time, and the warnings along the way.

Constraints:
- The site is static on GitHub Pages with no server. Live data comes from scheduled GitHub Actions that write snapshot files; API keys stay in repository secrets, never in the page.
- AIS shows only vessels that carry a transponder. Most small Indian fishing boats do not, so traffic is a lower bound, mostly larger fishing vessels and merchant ships. The page must say this.
- Keep per-date site data under ~1 MB (traffic grids as PNG overlays, not vectors).

### Phase 6: Traffic data

Sources checked (2026-11-24):

| Source | What | Latency | Access |
|---|---|---|---|
| Global Fishing Watch 4Wings API, `public-global-presence:latest` | Hourly AIS positions binned to a grid, filterable by vessel type (fishing, cargo, tanker, passenger …) | ~72 – 96 h | Free API token, non-commercial only |
| Global Fishing Watch 4Wings, fishing effort dataset | Apparent fishing hours on a grid | ~72 – 96 h | Same token |
| AISStream.io | Live AIS messages over a WebSocket, filtered by bounding box | Live | Free API key |

Results of the check (milestone 1):
- **GFW works and is the source.** Presence dataset `public-global-presence:v5.0`, effort `public-global-fishing-effort:v5.0`. Newest day 2026-11-20 on 2026-11-24 (4 days). `date-range` end is exclusive. LOW resolution = 0.1° cells, `lat`/`lon` are cell centres (a box inside one cell returned the cells centred on both sides). `group-by` has no vessel type; `filters[0]=vessel_type in (...)` works. Types with data: cargo, fishing, gear (net and buoy beacons), passenger, seismic_vessel, carrier, bunker, insufficient_data; `tanker`, `support`, `other` return nothing, and ~42% of hours have no type. One week over the download box: 498,000 vessel-hours in all, cargo 159,000, gear 79,000, fishing 22,500, passenger 14,400. Each query takes 1 – 3 s; back-to-back queries sometimes fail, and the API refuses Python's default User-Agent (403).
- **Fishing vessels with AIS are almost only on the west coast.** Fishing presence inside India's EEZ per week: Karnataka & Kerala 7,020 h, Maharashtra & Goa 3,257, Gujarat 369, Lakshadweep 263, east coast and Andaman under 20 each; the busiest fishing cells are off Sri Lanka. Effort follows the same pattern. Cargo is everywhere (Gujarat 34,000 h, Andhra Pradesh 10,600, Odisha & West Bengal 6,700).
- **AISStream is not usable off India.** Over the whole download box: 2 positions in 3 minutes, 1 vessel in 10 minutes (off Chennai); Singapore in the same session: 19 vessels in 30 s. Its WebSocket handshake also needs IPv4 and a long open timeout from here. No live vessel layer (milestone 7.3 dropped).

Steps:
- `fetch.fetch_traffic`: weekly GFW presence over the download box for the 7 days ending on the SST date, split into fishing and merchant (cargo + tanker + passenger), and fishing hours. `data/traffic_<SST date>.nc`.
- `pfz.py`: new zone columns `fishing_hours`, `merchant_hours`; point columns `merchant_hours` within ~5 km and `in_lane` (merchant density above its 90th percentile, as for fronts).
- Validation: share of fishing hours inside our zones vs inside an equal area of random sea in the same region, per week. Unlike INCOIS lines this is where boats actually fished, so it is a second check; write it to `validation/effort.csv`.
- Page: two overlays (fishing, merchant) with a legend; popups show the new values; a "shipping lane" note on points with `in_lane`.

Milestones:
1. ~~Try GFW and AISStream over the download box.~~ Done 2026-11-24, results above: GFW for weekly grids, AISStream dropped.
2. ~~`fetch_traffic` and the traffic grids for the 8 published weeks.~~ Done 2026-11-24. `fetch.fetch_traffic` finds the newest GFW day on or before the SST date (daily query in a 1° box off Mumbai), then downloads the 7 days ending on it for fishing presence, merchant presence (cargo + passenger) and fishing effort: `data/traffic_<SST date>.json` (~360 KB, cells as [lat, lon, hours]). Token from `GFW_TOKEN` (local `.env`, repository secret for the weekly job). Merchant hours are steady at 173,000 – 180,000 per week; fishing presence 21,000 – 39,000. Maps: `docs/images/lanes_2026-11-20.png`, `docs/images/fishing_2026-11-20.png`.
3. ~~Zone and point traffic columns; effort check over the 8 weeks.~~ Done 2026-11-24. `pfz.load_traffic` puts the cells on a 0.1° grid; each SST pixel takes its cell's hours, and a zone sums them by area share. New columns: zones `fishing_hours`, `merchant_hours`, `effort_hours` (vessel-hours in the zone that week); points `merchant_hours` (the point's 0.1° cell) and `in_lane` (≥ `LANE_HOURS` = 6 h; the 90th percentile of EEZ cells is 6 – 7 h every week and those cells hold 85 – 87% of merchant hours). Existing columns unchanged in all 8 weeks. 385 of 1,411 points (27%) lie in a lane: Gujarat 154 / 339, Maharashtra & Goa 74 / 151, Karnataka & Kerala 67 / 193, Tamil Nadu 43 / 164, Odisha & West Bengal 34 / 313, Andhra Pradesh 6 / 180. Zones with any fishing presence 32%, any effort 19%. Effort check (`pfz.effort_check` → `validation/effort.csv`): per region, share of AIS fishing effort inside zones with points against their share of the sea within 300 km of the region's harbours. Over the 8 weeks: Karnataka & Kerala (9,000 h effort per week, the only region with much) zones hold 5.3% of effort on 3.4% of the sea, ratio 1.56, but 0.22 – 5.68 week to week; Maharashtra & Goa (1,850 h) 0.36; Gujarat (610 h) 0.22; Tamil Nadu (635 h) 0.16; other regions have too little effort to say. So AIS fishing effort does not confirm the zones outside Karnataka & Kerala; AIS boats there are mostly larger trawlers, and effort may follow habit and port distance more than fronts.
4. ~~Overlays, popups and lane note on the page; weekly job fetches traffic.~~ Done 2026-11-24. Layers "Fishing vessels (AIS)" (`fishing.png`, all cells, orange) and "Shipping lanes (AIS)" (`merchant.png`, only cells ≥ 6 h, pink to purple; showing every cell covered most of the sea) with legends, 1 – 100+ h on a log scale. Zone panel: fishing and merchant vessel-hours; point popup and list: "shipping lane" note with the hours. The dates line names the AIS week; the footer names GFW and says small boats without AIS are missing. 2026-11-20 site data 0.96 MB. `weekly.yml` passes `GFW_TOKEN` from the repository secret.

### Phase 7: Interactive region view

- **Select:** a region list and a harbour search; clicking a region or zone zooms to it and opens a side panel instead of a popup.
- **Side panel:** zones in the region ranked, with their ocean values and traffic; clicking a zone highlights it and its points.
- **Layers:** toggles for zones, points, SST, chlorophyll, fishing traffic, merchant traffic, eddies, live vessels.
- **Time slider:** step through the 8 published weeks, zones and traffic together.
- **Near-live vessels:** `traffic_live.py` in a scheduled Action (every ~3 h) collects AIS positions in the download box for a few minutes and writes `docs/site/live.json` (latest position, type, speed, course per vessel; no names). Vessel markers coloured by type with a heading arrow and the snapshot time; older than 6 h is shown as stale.
- Stays in `web/index.html` with Leaflet; no build step.

Milestones:
1. ~~Region / harbour selection and side panel.~~ Done 2026-11-24. `index.json` carries `harbours` (name → lat, lon, region). Header: date, region and a harbour select grouped by region; choosing a harbour sets its region, puts a marker on it, and lists only zones with points from that harbour, nearest first, with only that harbour's points. Clicking a zone on the map or in the list outlines it, fits the map and shows its values and points in the panel ("← All zones" goes back); a point opens its popup. Wide screens (≥ 900 px): map left, 420 px panel right, full height; phones keep map above, list below. Regions are chosen in the select only (their boxes overlap, so they are not drawn as clickable areas).
2. ~~Layer toggles and time slider.~~ Done 2026-11-24. A "Layers" box in the panel replaces Leaflet's layer control: zones, advisory points (still from zoom 7), SST, chlorophyll, eddies, EEZ boundary; grids sit in their own map pane under the zones. New `eddy.png` per date (`pfz.write_eddy_overlay`): local sea level anomaly, blue −15 to red +15 cm, written at a quarter of the overlay resolution since sea level is 0.25° (24 KB; 2026-11-20 site data 0.90 MB), with a legend when shown. A week slider in the header replaces the date select; region and harbour stay selected across weeks. Traffic and live vessel toggles come with phases 6 and 7.3.
3. ~~`traffic_live.py`, its workflow and the vessel layer.~~ Dropped 2026-11-24: AISStream sees about one vessel per 10 minutes off India (milestone 6.1); the weekly GFW grid stays the only traffic.

### Phase 8: Guidance

- **Route:** pick a harbour and an advisory point; `sea.py` Dijkstra gets a cost layer that adds a penalty for merchant lanes, so the route crosses them short and straight. Shown as a line with distance (km, nautical miles), initial heading, and time at a chosen speed (default 8 kn).
- **Along the route:** wind and current at the point, lane crossings, EEZ edge, fishing ban period, strong wind, stale chlorophyll; a short summary on top of the panel.
- Routes are precomputed per point to its nearest harbour (and the next 2 nearest) in `pfz.py`, so the page does no routing; stays within the data budget or loads per region on demand.
- Printable / shareable advisory per point (URL with region, zone and point).

Milestones:
1. ~~Lane-penalised routes in `sea.py`.~~ Done 2026-11-24. `sea.edges` holds the 0.04° ocean grid's 8-connected edges (shared with the nearest-harbour distances, unchanged: with no penalty the routes reproduce `distance_km` within 0.5 km). `sea.lane_routes` runs Dijkstra from each harbour with edge cost km × (1 + `LANE_PENALTY` × share of the edge in lane cells), lanes = merchant 0.1° cells ≥ `LANE_HOURS`, and walks the predecessors back from each point; lines are simplified (Douglas-Peucker, `SIMPLIFY_DEG` = 0.01°). Penalty on 2026-11-20's 212 points: 0 → 4,586 lane km in all, 1 → 2,061 (95th percentile detour 11.6%, max 37%), 2 → 1,631 (27.5%, 97%), 5 → 1,496 (38%, 154%), so `LANE_PENALTY` = 1. 44% of routes still touch a lane (harbour or point in one). Land check over the 8 weeks (1,411 routes, segments sampled every 0.01°, 3+ samples on land): none with 0.01° simplification; 0.02° cut ~1 km of land at Chennai harbour, Paradip and Porbandar. Diagonal steps touch land cells only at corners. Routes go to each point's nearest harbour only, not the next 2 (the harbour list already shows a harbour's own points).
2. ~~Routes and warnings in the outputs and the side panel.~~ Done 2026-11-24. `pfz.add_routes`: every advisory point gets `route_km`, `lane_km`, `eez_km` (`points.csv` and GeoJSON) and its route line (GeoJSON only; median 4 vertices, max 25; 2026-11-20 site data 0.99 MB). `eez_km` = distance to sea outside India's EEZ that reaches the edge of the download box (neighbours' waters, high seas); counting every sea pixel outside the EEZ polygon put estuaries and creeks along the coast at 0 – 20 km. Over the 8 weeks 44 of 1,411 points are within 20 km of the edge: Gujarat 19 (Sir Creek, Jakhau), Odisha & West Bengal 12 (Bangladesh), Tamil Nadu 11 (Palk Strait), Andaman 2; 879 routes run through a lane for some km. Page: choosing a point (list or map) draws the dashed route from its harbour and shows a box above the zone: route km and nautical miles, first heading, time at a boat speed (default 8 kn, editable), wind and current, and warnings: km of route in shipping lanes, point in a lane, EEZ edge < 20 km, strong wind, fishing ban period on that coast by today's date (east incl. Andaman 15 Apr – 31 May, west incl. Lakshadweep 1 Jun – 31 Jul), stale chlorophyll. Screenshot: `docs/images/route_2026-11-20.png`.
3. ~~Shareable per-point links and a print view.~~ Done 2026-11-24. The page keeps the selection in the URL hash (`#date=2026-11-17&zone=21&point=1`; zone only, or date only); opening such a link sets the week slider and selects the zone and point. The route box has "Copy link" and "Print"; the print stylesheet keeps the map, the route box with its warnings, the zone details and the sources, and hides the controls, lists and layer box; on print the map is resized and refitted to the route.

## Known limitations

- **Monsoon cloud cover (Jun – Sep):** satellite chlorophyll has large gaps; expect few or no zones. MUR SST is gap-filled, so fronts still appear.
- **Fishing ban periods:** East coast 15 Apr – 31 May, West coast 1 Jun – 31 Jul. Outputs are produced but not actionable.
- **Near-real-time chlorophyll:** lower quality than science-quality products, and NOAA's NRT products can stall (NOAA-20 7-day at 2026-11-09 through at least 2026-11-23).
- **ERDDAP access from GitHub:** PFEG ERDDAP answers HTTP 403 to GitHub runners at times (2026-11-19, 2026-11-22; `upwell.pfeg.noaa.gov` forwards to the same server). The weekly job retries 3 times; when it still fails, the site keeps the last committed data, and `deploy.yml` publishes any `docs/site` change pushed by hand.
- **Routes are indicative:** they run on a 0.04° (~4.4 km) ocean grid where a cell counts as sea if any part of it is, so inshore legs may hug or cut the coastline; they avoid shipping lanes only as seen in last week's AIS, and ignore depth, reefs, nets and weather.
- **Advisory points are tile-based:** spread over the zone on a ~30 km grid, not traced along the front line.
- **Lakshadweep:** INCOIS lines there follow very weak SST gradients and low or cloud-masked chlorophyll; our method finds no matching zones.
- **INCOIS comparison is one-sided:** INCOIS lines are drawn by analysts and may skip valid fronts, so low precision is not only our error. It also cannot confirm parameters INCOIS does not use (eddies, wind, currents, salinity).
- **Altimetry near the coast:** sea level in shallow gulfs (Khambhat, Kutch) shows strong strips that are likely errors, so eddy labels there are unreliable.
- **AIS traffic is a lower bound:** most small Indian fishing boats carry no AIS, so fishing traffic shows almost only west coast trawlers; GFW data are ~4 days old and ~42% of vessel-hours have no vessel type.
- **Coarse extra parameters:** sea level, currents, salinity and wind are 0.25 – 0.33° (~28 – 37 km), coarser than the 0.02° fronts; they describe a zone's surroundings, not its edges, and are missing within ~25 km of the coast for altimetry and SMAP.

## Later

- Regional languages for advisory text and the page; SMS / WhatsApp alerts.
- Compare our advisories with INCOIS per landing centre (the landing-centre layer carries INCOIS's own direction, distance and depth ranges).
- Mixed-layer depth from a current ocean model (none on NOAA ERDDAP).
