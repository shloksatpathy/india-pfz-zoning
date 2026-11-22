# name: (lat_min, lat_max, lon_min, lon_max)
REGIONS = {
    "Gujarat": (20.0, 24.5, 66.0, 73.0),
    "Maharashtra & Goa": (14.8, 20.0, 70.5, 74.0),
    "Karnataka & Kerala": (8.0, 14.8, 74.0, 77.5),
    "Lakshadweep": (8.0, 12.5, 71.0, 74.0),
    "Tamil Nadu & Puducherry": (8.0, 13.5, 77.5, 81.5),
    "Andhra Pradesh": (13.5, 19.2, 79.5, 85.0),
    "Odisha & West Bengal": (19.2, 22.5, 84.5, 89.0),
    "Andaman & Nicobar": (6.0, 14.0, 91.5, 94.5),
}

BBOX = (6.0, 24.5, 66.0, 94.5)

# Per-region thresholds: (GRAD_MIN °C/km SST front, CHL_MIN mg/m³ productive water).
# A pixel uses the values of the region of its nearest harbour. Phase 1 values; see PLAN.md step 5.
THRESHOLDS = {
    "Gujarat": (0.05, 0.3),
    "Maharashtra & Goa": (0.05, 0.3),
    "Karnataka & Kerala": (0.05, 0.3),
    "Lakshadweep": (0.05, 0.3),
    "Tamil Nadu & Puducherry": (0.05, 0.3),
    "Andhra Pradesh": (0.05, 0.3),
    "Odisha & West Bengal": (0.05, 0.3),
    "Andaman & Nicobar": (0.05, 0.3),
}

# Advisory points per region, given to zones in rank order (None = no cap). See PLAN.md phase 3.
MAX_POINTS = {name: None for name in REGIONS}
