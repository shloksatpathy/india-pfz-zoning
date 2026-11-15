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

## Phase 2: Validation and better zones

### Step 1: Archive INCOIS advisories

INCOIS has no archive of past advisories, so collect the live ones from now on.

- The advisory pages (https://incois.gov.in/MarineFisheries/PfzAdvisory, `/TextData`) load their content with JavaScript. Find the request the page makes for the advisory data (browser network tab) and fetch that directly.
- `incois.py`: download the current advisory per sector, parse each zone into region / harbour / bearing / distance / depth (and lat/lon where given), save to `validation/incois/<date>.csv`.
- Add it to the weekly workflow as a separate daily job, so every issued advisory is kept, and commit `validation/incois/`.
- INCOIS advisories are daily and use near-real-time data; ours use the newest weekly chlorophyll, which lags by several weeks. Compare by matching dates once our pipeline reaches an archived date.

### Step 2: Comparison (`validate.py`)

- For a date with both outputs, per region:
  - share of INCOIS zone points that fall inside, or within 10 km of, one of our zone polygons (hit rate)
  - share of our zone area within 10 km of an INCOIS point (precision proxy)
  - zone counts side by side
- Write `validation/<date>.csv` and a summary table per region.
- Map per region: our polygons plus INCOIS points, for visual checks.

### Step 3: Per-region thresholds

- Move `GRAD_MIN` and `CHL_MIN` into `regions.py` per region (default to current values).
- Sweep both thresholds per region over the archived dates; pick values that maximise hit rate without zone counts far above INCOIS.
- Expected: higher `CHL_MIN` for the productive Gujarat and Odisha / West Bengal shelves, lower for Lakshadweep and Andaman & Nicobar (oligotrophic water).
- Record the sweep table and chosen values here, as in phase 1.

### Step 4: Region assignment by coast

Region boxes overlap and leave gaps (e.g. Lakshadweep inside the Karnataka & Kerala longitudes; a zone is given to the first box holding its centroid).

- Assign each zone to the region of its nearest harbour (`harbours.py` gets a region per harbour), which also matches the advisory text.
- Keep the boxes only for map zoom and region plots.
- Drop zones whose nearest harbour is beyond a cutoff (e.g. 300 km) instead of the `region_of` box test.

### Step 5: Zone polygon holes

- `outline` keeps only the longest ring. Keep all rings from the contour: outer ring plus holes (rings inside the outer one) as a GeoJSON Polygon; separate outer rings as a MultiPolygon.
- Check `zones.geojson` size stays under ~300 KB per date.

### Milestones

1. `incois.py` archiving live advisories, daily workflow job.
2. `validate.py` comparison metrics and maps for the first overlapping dates.
3. Per-region thresholds tuned from the comparison.
4. Region assignment by nearest harbour.
5. Polygons with holes.

## Known limitations

- **Monsoon cloud cover (Jun – Sep):** VIIRS chlorophyll has large gaps; expect few or no zones. MUR SST is gap-filled, so fronts still appear.
- **Fishing ban periods:** East coast 15 Apr – 31 May, West coast 1 Jun – 31 Jul. Outputs are produced but not actionable.
- **Chlorophyll lag:** the newest weekly composite is often 4 – 6 weeks old (2026-10-08 on 2026-11-15), so the published map is not current.
- **Distances are straight-line** from harbour to zone centroid and can cross land (e.g. around Kathiawar or Sri Lanka).
- **Harbours missing:** Agro, Dholai, Pazhayar, Roychowk and Petuaghat could not be located in OpenStreetMap.

## Later

- Fresher data: near-real-time daily or 3-day VIIRS chlorophyll to cut the lag.
- Regional languages for advisory text and the page; SMS / WhatsApp alerts.
