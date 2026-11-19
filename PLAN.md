# Plan

Goal: Potential Fishing Zones (PFZ) for India's coastal regions from satellite SST and chlorophyll-a, published as a weekly web map.

## Current system (phase 1, done)

```
run.py (weekly chl dates) ──> fetch.py ──> data/sst_<date>.nc, chl_<date>.nc, etopo.nc
                                 │
                                 v
                              pfz.py ──> outputs/<date>/zones.csv, zones.geojson,
                                 │       sst.png, chl.png, check.png, <region>.png
                                 v
                   outputs/index.json ──> site.py ──> docs/site/ ──> GitHub Pages
```

| File | Purpose |
|---|---|
| `regions.py` | Region bounding boxes and the full download box (6.0 – 24.5 °N, 66.0 – 94.5 °E) |
| `fetch.py` | MUR SST (`jplMURSST41`, daily, stride 2), VIIRS chlorophyll (`noaacwNPPVIIRSSQchlaWeekly`), ETOPO1 depth |
| `pfz.py` | Fronts ∩ productive water, clipped to EEZ, labelled into zones with polygon, depth and nearest-harbour advisory text |
| `harbours.py` | 54 fishing harbours: DoF Handbook 2020 names, OpenStreetMap coordinates |
| `run.py` | Batch over weekly chlorophyll dates (`last last` for the newest), writes `index.json` |
| `site.py` | Keeps the latest 8 weeks in `docs/site/` with `web/index.html` and the EEZ |
| `.github/workflows/weekly.yml` | Tuesdays: newest week, rebuild site, commit, deploy to Pages |

Current parameters (`pfz.py`):

| Parameter | Value | Note |
|---|---|---|
| `GRAD_MIN` | 0.05 °C/km | 0.07 empties Lakshadweep and Andaman & Nicobar |
| `CHL_MIN` | 0.3 mg/m³ | one value for all regions |
| `DILATE` | 2 px | joins nearby front pixels |
| `MIN_PIXELS` | 50 (~240 km²) | ~80 zones per date |

Zone counts so far: 2026-09-03: 64, 2026-09-24: 25, 2026-10-01: 81, 2026-10-08: 83.

**Problems found (2026-11-19):**
- **The map is weeks out of date.** The science-quality chlorophyll ends at 2026-10-08, ~6 weeks old, while MUR SST is current to 2026-11-17.
- **Big zones can't be acted on.** On 2026-10-08, 24 of 83 zones are over 1,000 km². Zone 77 (Gujarat, 13,939 km², 202 × 264 km) gets one line: "Jakhau: S, 79 km, depth 28 m". A curved zone's centroid can also fall outside the zone.

## Phase 2: Fresh data, actionable zones, validation

### Step 1: Fresher chlorophyll

Chlorophyll options checked on 2026-11-19 (ocean coverage = valid pixels over the India box's ocean):

| Dataset (CoastWatch ERDDAP) | Newest | Ocean coverage |
|---|---|---|
| `noaacwNPPVIIRSSQchlaWeekly`: S-NPP science quality, weekly (current) | 2026-10-08 | 63% |
| `noaacwN20VIIRSchlaWeekly`: NOAA-20 near real time, 7-day rolling | 2026-11-09 | ~87% |
| `nesdisVHNnoaa20chlaDaily`: NOAA-20 near real time, daily | 2026-11-15 | 10 – 47% per day |

- `fetch.py`: switch `CHL_URL` to `noaacwN20VIIRSchlaWeekly`. Same variable (`chlor_a`) and dimensions (`time, altitude, latitude, longitude`), so only the dataset ID changes.
- **Separate dates:** SST = newest MUR day, chlorophyll = newest NRT composite. The output folder is named by the SST date. `index.json` records `sst_date` and `chl_date`, and the page shows both.
- `run.py`: the NRT dataset is a 7-day composite with a new time step every day. History runs take every 7th date; the weekly job uses `last`.
- Rebuild `docs/site` from the NRT source so all 8 weeks come from one product (the current 4 dates are science quality).
- Expected age after each Tuesday run: SST ~2 days, chlorophyll ~4 – 10 days. After the first runs, check whether NRT updates arrive often enough to justify a second weekly run.
- Keep the science-quality dataset as a known alternative for validation reruns: higher quality, ~6 weeks behind.

### Step 2: Several advisory points per zone

One centre point cannot describe a zone 200 km across. INCOIS advisories list several positions per sector; do the same.

- Tile each zone's pixels on a ~30 km grid (`POINT_TILE_KM = 30`). Each tile with enough zone pixels gets one point: the zone pixel nearest that tile's pixel centroid, so the point always lies inside the zone.
- Each point gets its own harbour, bearing, distance and depth, reusing `nearest_harbour` and the ETOPO depth lookup in `pfz.py`.
- Each zone's `lat`/`lon` becomes an interior point (the zone pixel nearest the centroid) instead of the raw centroid.
- Outputs:
  - `points.csv`: one row per point (zone_id, point, lat, lon, harbour, bearing, distance_km, depth_m, advisory).
  - `zones.geojson`: zone polygons plus Point features (`kind: "point"`) with the same properties.
  - `zones.csv`: still one row per zone; its `advisory` is the point closest to its harbour.
- Web page: point markers on the map; the list is grouped by zone, with one tappable line per point.
- ~80 zones → a few hundred points; keep per-date data under ~1 MB.

### Step 3: Archive INCOIS advisories

INCOIS has no archive of past advisories, so collect the live ones from now on.

- The text pages (https://incois.gov.in/MarineFisheries/PfzAdvisory, `/TextData`) only describe the service. The PFZ WebGIS page (`/MarineFisheries/PfzWebGis`) draws the current advisory from a GeoServer WFS layer, `PFZ_Automation:pfzlines`, as GeoJSON lines with state, sector, year and Julian day.
- `incois.py`: fetch that layer, thin each line to ~1 km vertex spacing, save `validation/incois/<date>.geojson` (~20 KB per day). Lines are better than parsed text for comparison: distances can be measured to the line itself.
- `.github/workflows/incois.yml`: daily at 13:00 IST, commits `validation/incois/`.
- With NRT chlorophyll (step 1), our dates trail INCOIS by days rather than weeks, so archived advisories can be compared within about 10 days.

### Step 4: Comparison (`validate.py`)

- For a date with both outputs, per region:
  - share of INCOIS line length inside, or within 10 km of, one of our zone polygons (hit rate)
  - share of our advisory points (step 2) within 10 km of an INCOIS line (precision proxy)
  - zone and point counts side by side
- Write `validation/<date>.csv` and a summary table per region.
- Map per region: our polygons and points plus INCOIS lines, for visual checks.

### Step 5: Per-region thresholds

- Move `GRAD_MIN` and `CHL_MIN` into `regions.py` per region (default to current values).
- Sweep both thresholds per region over the archived dates; pick values that maximise hit rate without zone counts far above INCOIS.
- Expected: higher `CHL_MIN` for the productive Gujarat and Odisha / West Bengal shelves, lower for Lakshadweep and Andaman & Nicobar (oligotrophic water). Tighter thresholds there also shrink the oversized zones.
- Record the sweep table and chosen values here, as in phase 1.

### Step 6: Region assignment by coast

Region boxes overlap and leave gaps (e.g. Lakshadweep inside the Karnataka & Kerala longitudes; a zone is given to the first box holding its centroid).

- Assign each zone to the region of its nearest harbour (`harbours.py` gets a region per harbour), which also matches the advisory text.
- Keep the boxes only for map zoom and region plots.
- Drop zones whose nearest harbour is beyond a cutoff (e.g. 300 km) instead of the `region_of` box test.

### Step 7: Zone polygon holes

- `outline` keeps only the longest ring. Keep all rings from the contour: outer ring plus holes (rings inside the outer one) as a GeoJSON Polygon; separate outer rings as a MultiPolygon.
- Check `zones.geojson` size stays under ~300 KB per date.

### Milestones

1. ~~NRT chlorophyll and separate SST / chlorophyll dates; site rebuilt from NRT.~~ Done 2026-11-19: 8 weeks 2026-09-29 – 2026-11-17, zones per date 118, 78, 74, 44, 36, 61, 48, 51.
2. ~~Advisory points per zone (`points.csv`, map markers, grouped list).~~ Done 2026-11-19: 112 – 493 points per date; the 4,361 km² Gujarat zone on 2026-11-17 has 12 points from Veraval to Porbandar. Points show on the map from zoom 7.
3. ~~`incois.py` archiving live advisories, daily workflow job.~~ Done 2026-11-19: first archive 2026-11-18, 30 lines (Gujarat 7, Kerala 7, Maharashtra 6, Karnataka 5, Lakshadweep 2, Andaman 2, Goa 1).
4. `validate.py` comparison metrics and maps for the first overlapping dates.
5. Per-region thresholds tuned from the comparison.
6. Region assignment by nearest harbour.
7. Polygons with holes.

## Known limitations

- **Monsoon cloud cover (Jun – Sep):** VIIRS chlorophyll has large gaps; expect few or no zones. MUR SST is gap-filled, so fronts still appear.
- **Fishing ban periods:** East coast 15 Apr – 31 May, West coast 1 Jun – 31 Jul. Outputs are produced but not actionable.
- **Near-real-time chlorophyll:** the NRT composite is 4 – 10 days old and lower quality than the science-quality product; SST and chlorophyll dates differ by up to ~1 week.
- **Advisory points are tile-based:** they are spread over the zone on a ~30 km grid, not traced along the front line.
- **Distances are straight-line** from harbour to point and can cross land (e.g. around Kathiawar or Sri Lanka).
- **Harbours missing:** Agro, Dholai, Pazhayar, Roychowk and Petuaghat could not be located in OpenStreetMap.

## Later

- Rolling median of NOAA-20 daily NRT chlorophyll (~4 days old) if the 7-day NRT composite proves too stale.
- Regional languages for advisory text and the page; SMS / WhatsApp alerts.
