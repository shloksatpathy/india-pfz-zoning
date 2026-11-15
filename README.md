# India PFZ Zoning

Potential Fishing Zone (PFZ) mapping for the coasts of India using free satellite ocean data from NOAA ERDDAP.

## Idea

Fish gather where cold, nutrient-rich water meets warmer water (thermal fronts) and where phytoplankton is abundant. This project:

1. Downloads sea surface temperature (SST) and chlorophyll-a for Indian coastal waters.
2. Finds SST fronts from the temperature gradient.
3. Keeps fronts that overlap productive (high chlorophyll) water.
4. Labels the resulting zones by coastal region and exports maps and GeoJSON.

## Data sources

| Variable | ERDDAP dataset | Resolution | Cadence |
|---|---|---|---|
| SST | `jplMURSST41` (MUR SST v4.1) | 0.01° | Daily |
| Chlorophyll-a | `noaacwNPPVIIRSSQchlaWeekly` (VIIRS SNPP) | ~0.0375° | Weekly |

Servers: https://coastwatch.pfeg.noaa.gov/erddap/ (SST) and https://coastwatch.noaa.gov/erddap/ (chlorophyll), no login required

Depth at each zone centroid comes from ETOPO1 (`etopo180` on the same SST server).

Harbour names come from the Department of Fisheries *Handbook on Fisheries Statistics 2020* (Tables 13.2 and 13.3: major harbours and commissioned fishing harbours; Lakshadweep landing centres). Coordinates come from OpenStreetMap via Nominatim (© OpenStreetMap contributors, ODbL). Agro, Dholai, Pazhayar, Roychowk and Petuaghat are left out because they could not be located reliably. Bearing and distance are straight-line from the harbour to the zone centroid.

Zones are clipped to India's EEZ (`india_eez.geojson`, outer boundaries of the mainland + Lakshadweep and Andaman & Nicobar EEZs) from [Marine Regions](https://www.marineregions.org), licensed CC-BY 4.0.

## Coastal regions

| Region | Coast |
|---|---|
| Gujarat | West |
| Maharashtra & Goa | West |
| Karnataka & Kerala | West |
| Lakshadweep | Arabian Sea islands |
| Tamil Nadu & Puducherry | East |
| Andhra Pradesh | East |
| Odisha & West Bengal | East |
| Andaman & Nicobar | Bay of Bengal islands |

## Layout

```
india-pfz-zoning/
├── regions.py     # coastal region bounding boxes
├── fetch.py       # download SST and chlorophyll from ERDDAP
├── pfz.py         # front detection + chlorophyll filter -> zones
├── run.py         # batch runner over weekly chlorophyll dates
├── harbours.py    # fishing harbour coordinates for advisory text
├── web/index.html # Leaflet map page reading outputs/
├── site.py        # builds docs/site/ (latest 8 weeks + map page)
└── outputs/       # per-date maps (PNG), zones.csv, zones.geojson
```

## Usage

```
uv run fetch.py 2026-10-08
uv run pfz.py 2026-10-08
```

The date must be covered by both datasets (chlorophyll lags SST by a few weeks).

To process every weekly chlorophyll date in a range and write `outputs/index.json` (dates with zone counts per region):

```
uv run run.py 2026-09-03 2026-10-08
```

Outputs in `outputs/<date>/`:
- `check.png`: whole-India SST fronts, chlorophyll, and PFZ mask
- `<region>.png`: per-region map with numbered zones
- `zones.csv`: one row per zone (region, centroid lat/lon, area_km2, sst, chl, depth_m, nearest harbour, bearing, distance_km, advisory text such as `Veraval: SW, 45 km, depth 60 m`)
- `zones.geojson`: zone outlines as polygons with the same properties
- `sst.png`, `chl.png`: map overlays (no axes, land transparent, rows resampled to Web Mercator) covering the full download box

## Web map

`uv run site.py` copies the latest 8 weeks of outputs, the map page and the EEZ into `docs/site/`. To view it locally:

```
uv run site.py
python -m http.server -d docs/site
```

A weekly GitHub Actions workflow processes the newest chlorophyll week, rebuilds `docs/site/`, commits it and deploys it to GitHub Pages.

## Example output (2026-10-08)

All of India: SST with fronts outlined (left), chlorophyll-a (middle), and pixels that are both a front and productive water (right).

![SST fronts, chlorophyll and PFZ mask for India](docs/images/check_2026-10-08.png)

Gujarat: the largest zone follows the cold upwelling front along the Saurashtra coast and the Gulf of Kutch. Black hatched areas are zones (numbered), green lines enclose chlorophyll ≥ 0.3 mg/m³.

![Gujarat PFZ map](docs/images/gujarat_2026-10-08.png)

Odisha & West Bengal: zones on the shelf off the Hooghly and Subarnarekha river mouths.

![Odisha and West Bengal PFZ map](docs/images/odisha_west_bengal_2026-10-08.png)

Largest zones that day, from `zones.csv`:

| id | region | lat | lon | area_km2 | sst (°C) | chl (mg/m³) |
|---|---|---|---|---|---|---|
| 77 | Gujarat | 22.508 | 68.778 | 13938.8 | 28.75 | 2.575 |
| 52 | Andhra Pradesh | 18.522 | 84.799 | 6895.0 | 29.84 | 0.496 |
| 24 | Andhra Pradesh | 15.049 | 81.209 | 4643.2 | 30.86 | 0.536 |
| 11 | Andhra Pradesh | 13.567 | 80.923 | 3830.7 | 30.42 | 0.488 |
| 27 | Andhra Pradesh | 15.436 | 80.421 | 2919.4 | 30.50 | 0.841 |

## Status

Milestones 1–3 and 5–8 of [PLAN.md](PLAN.md) done, plus EEZ clipping and a first threshold tuning pass. Comparison with INCOIS advisories is pending: no downloadable archive of past advisories was found.

## References

- INCOIS PFZ advisory service: https://incois.gov.in
- NOAA CoastWatch ERDDAP: https://coastwatch.pfeg.noaa.gov/erddap/
