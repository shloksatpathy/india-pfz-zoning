# Implementation Plan

Goal: for a given date, produce Potential Fishing Zones (PFZ) for each Indian coastal region from satellite SST and chlorophyll-a, and export maps plus a zone list.

## Pipeline

```
date ──> fetch.py ──> data/sst_<date>.nc, data/chl_<date>.nc
                         │
                         v
                      pfz.py ──> fronts (SST gradient)
                         │       ∩ productive water (chl threshold)
                         │       -> labelled zones per region
                         v
             outputs/<date>/<region>.png, zones.csv, zones.geojson
```

## Files

| File | Purpose |
|---|---|
| `regions.py` | Dict of region name -> (lat_min, lat_max, lon_min, lon_max) |
| `fetch.py` | Download SST and chlorophyll NetCDF subsets from ERDDAP for one date |
| `pfz.py` | Load data, detect fronts, apply chlorophyll filter, label zones, write outputs |
| `pyproject.toml` | Dependencies via `uv`: numpy, xarray, netCDF4, scipy, matplotlib |

## Step 1: Regions (`regions.py`)

Approximate bounding boxes (covering the coast out to roughly the EEZ):

| Region | Lat (°N) | Lon (°E) |
|---|---|---|
| Gujarat | 20.0 – 24.5 | 66.0 – 73.0 |
| Maharashtra & Goa | 14.8 – 20.0 | 70.5 – 74.0 |
| Karnataka & Kerala | 8.0 – 14.8 | 74.0 – 77.5 |
| Lakshadweep | 8.0 – 12.5 | 71.0 – 74.0 |
| Tamil Nadu & Puducherry | 8.0 – 13.5 | 77.5 – 81.5 |
| Andhra Pradesh | 13.5 – 19.2 | 79.5 – 85.0 |
| Odisha & West Bengal | 19.2 – 22.5 | 84.5 – 89.0 |
| Andaman & Nicobar | 6.0 – 14.0 | 91.5 – 94.5 |

Full download box: 6.0 – 24.5 °N, 66.0 – 94.5 °E.

## Step 2: Fetch (`fetch.py`)

- Servers: `https://coastwatch.pfeg.noaa.gov/erddap/griddap/` (SST), `https://coastwatch.noaa.gov/erddap/griddap/` (chlorophyll)
- Chlorophyll lags SST by several weeks; the date must fall within both datasets' time coverage.
- SST: `jplMURSST41`, variable `analysed_sst` (°C), dims `[time][latitude][longitude]`, 0.01° daily. Request the full box with stride 2 (~0.02°, ~5 MB).
- Chlorophyll: `noaacwNPPVIIRSSQchlaWeekly`, variable `chlor_a` (mg/m³), dims `[time][altitude][latitude][longitude]`, ~0.0375° weekly. Pick the weekly composite closest to the requested date.
- Use ERDDAP's `.nc` output with `(value)` index syntax, e.g.
  `jplMURSST41.nc?analysed_sst[(2026-11-12)][(6.0):2:(24.5)][(66.0):2:(94.5)]`
- Save to `data/`. Skip download if the file already exists.
- CLI: `uv run fetch.py 2026-11-12`

## Step 3: Zones (`pfz.py`)

1. Open both files with xarray; sort by latitude; squeeze `time`/`altitude`.
2. Regrid chlorophyll onto the SST grid (`interp_like`, nearest).
3. **Fronts:** SST gradient magnitude in °C/km using `np.gradient` with grid spacing converted to km (lon spacing scaled by cos(lat)). Front pixel = gradient above threshold (start at 0.05 °C/km, tune).
4. **Productive water:** `chlor_a` above threshold (start at 0.3 mg/m³, tune per region later).
5. **PFZ mask** = front AND productive. Land and cloud pixels are NaN and drop out.
6. Dilate mask slightly (`scipy.ndimage.binary_dilation`) so fronts next to high-chl water connect, then label blobs (`scipy.ndimage.label`) and drop blobs below a minimum size (e.g. 20 pixels).
7. For each blob: centroid lat/lon, area (km²), mean SST, mean chl, and the region whose box contains the centroid.

## Step 4: Outputs

- `outputs/<date>/<region>.png`: SST background, chlorophyll contour, PFZ blobs outlined.
- `outputs/<date>/zones.csv`: one row per zone (region, lat, lon, area_km2, sst, chl).
- `outputs/<date>/zones.geojson`: zone centroids as points with the same properties.
- CLI: `uv run pfz.py 2026-11-12`

## Step 5: Validation

- Compare a few dates against INCOIS PFZ advisories (https://incois.gov.in) for the same region.
- Tune the gradient and chlorophyll thresholds so zone counts and locations are roughly in line.

### Tuning pass 1 (no INCOIS data)

Past INCOIS advisories could not be downloaded (no archive on the website; erddap.incois.gov.in unreachable from outside India), so the first pass only reduces noise.

- Zones are clipped to India's EEZ before labelling, which removes zones in Sri Lankan and Pakistani waters.
- Sweep over two dates, zone counts:

| Date | grad °C/km | min px | Zones |
|---|---|---|---|
| 2026-10-01 | 0.05 | 20 / 50 / 100 | 182 / 81 / 31 |
| 2026-10-01 | 0.07 | 20 / 50 / 100 | 96 / 40 / 23 |
| 2026-10-08 | 0.05 | 20 / 50 / 100 | 174 / 83 / 45 |
| 2026-10-08 | 0.07 | 20 / 50 / 100 | 92 / 38 / 13 |

- Chosen: `GRAD_MIN = 0.05`, `MIN_PIXELS = 50` (~240 km²). About 80 zones per date, with zones still in every region. Stronger gradient cutoffs empty Lakshadweep and Andaman & Nicobar.
- Still to do: compare against INCOIS advisories once some are available.

## Step 6: Application interface

Goal: a map people can open in a browser (phone or desktop) to see the latest zones for their coast, without installing Python.

### Users

- **Fishers and cooperatives:** phone, weak signal. Need "where, how far, which direction, how deep" from their harbour.
- **Fisheries officers and researchers:** desktop. Need past dates, all regions, and downloadable data.

### Approach: static site, no backend

The pipeline already writes files per date, so the interface is a static page that reads them. It can be hosted free on GitHub Pages and updated by a scheduled job.

```
run.py (date range) ──> outputs/<date>/zones.geojson, sst.png, chl.png
                        outputs/index.json (dates + zone counts)
site.py ──> docs/site/  (copies latest N weeks of outputs + web/index.html)
GitHub Pages serves docs/site/
```

### 6.1 Batch runner (`run.py`)

- `uv run run.py 2026-09-03 2026-10-08` runs `fetch` + `pfz` for each weekly chlorophyll date in the range.
- Writes `outputs/index.json`: list of dates with zone counts per region.

### 6.2 Richer zone data (`pfz.py`)

- **Polygons:** export each zone's outline (traced from the label mask with matplotlib `contour`) as a GeoJSON Polygon instead of only the centroid point.
- **Depth:** sample ETOPO1 bathymetry (`etopo180` on the same ERDDAP server) at each zone centroid; add `depth_m`.
- **Advisory text:** for each zone, the nearest fishing harbour, compass bearing (16-point) and distance in km, e.g. "Veraval: SW, 45 km, depth 60 m". This mirrors the INCOIS advisory format.
- **Harbours:** `harbours.py` with name and coordinates of the major fishing harbours per region. Coordinates to be compiled from a cited source (e.g. Department of Fisheries harbour list, OpenStreetMap).

### 6.3 Map overlays

- Save SST and chlorophyll as plain georeferenced PNGs (no axes, transparent land) with their lat/lon bounds, for use as map overlays.

### 6.4 Web page (`web/index.html`)

Single HTML file using Leaflet (from cdnjs) and OpenStreetMap tiles.

- **Date picker:** dates from `index.json`; defaults to the latest.
- **Region picker:** zooms to the region box and filters the zone list.
- **Layers:** zone polygons (coloured by chlorophyll), optional SST and chlorophyll overlays, EEZ boundary.
- **Zone popup / list:** advisory text, area, SST, chlorophyll, depth.
- **Download:** links to that date's `zones.csv` and `zones.geojson`.
- **Phone first:** list view under the map, large tap targets, total page data under ~1 MB per date.

### 6.5 Publishing (`site.py` + GitHub Actions)

- `site.py` copies the latest 8 weeks of outputs and `web/index.html` into `docs/site/`.
- GitHub Pages can only serve a branch's `/` or `/docs`, so `docs/site/` is published with `actions/deploy-pages` instead.
- A weekly GitHub Actions workflow (`.github/workflows/weekly.yml`) runs `run.py last last` for the newest chlorophyll week, then `site.py`, commits `docs/site/`, and deploys it. Earlier weeks come from the committed `docs/site/outputs/`, so CI only downloads one week.

### Not in the first version

- Regional languages (Gujarati, Marathi, Malayalam, Tamil, Telugu, Odia, Bengali).
- SMS / WhatsApp push alerts.
- User accounts or saved harbours.

## Known limitations

- **Monsoon cloud cover (Jun – Sep):** VIIRS chlorophyll has large gaps; expect few or no zones. MUR SST is gap-filled, so fronts still appear.
- **Fishing ban periods:** East coast 15 Apr – 31 May, West coast 1 Jun – 31 Jul. Outputs for these dates are still produced, but are not actionable.
- **Region boxes:** zones are clipped to the EEZ, but region labels still come from rectangles; a zone is assigned to the first box containing its centroid.
- **Chlorophyll lag:** a weekly composite is paired with a daily SST, so the two layers can be a few days apart.

## Milestones

1. `pyproject.toml` + `regions.py` + `fetch.py`; download one date successfully.
2. `pfz.py` front detection and chlorophyll mask; plot to check visually.
3. Zone labelling and CSV / GeoJSON / PNG outputs.
4. Validation against INCOIS advisories and threshold tuning.
5. `run.py` batch runner and `index.json`.
6. Zone polygons, depth, harbour bearing/distance advisory text.
7. `web/index.html` map page reading local outputs.
8. `site.py`, GitHub Pages, weekly GitHub Actions update.
