import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path as Polygon
import numpy as np
import xarray as xr
from contourpy import contour_generator
from scipy import ndimage

from harbours import HARBOURS
from regions import REGIONS

GRAD_MIN = 0.05  # °C/km, SST front threshold
CHL_MIN = 0.3  # mg/m³, productive water threshold
DILATE = 2  # pixels, joins nearby front pixels into one zone
MIN_PIXELS = 50  # zones smaller than this (~240 km²) are dropped
KM_PER_DEG = 111.32
EARTH_KM = 6371.0
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def load(date):
    sst = xr.open_dataset(f"data/sst_{date}.nc").analysed_sst.squeeze("time").sortby("latitude")
    chl = xr.open_dataset(f"data/chl_{date}.nc").chlor_a.squeeze(["time", "altitude"]).sortby("latitude")
    chl = chl.interp_like(sst, method="nearest")
    depth = -xr.open_dataset("data/etopo.nc").altitude.sortby("latitude")
    return sst, chl, depth


def sst_gradient(sst):
    y_km = sst.latitude.values * KM_PER_DEG
    x_km = sst.longitude.values * KM_PER_DEG
    gy, gx = np.gradient(sst.values, y_km, x_km)
    gx = gx / np.cos(np.deg2rad(sst.latitude.values))[:, None]
    return sst.copy(data=np.hypot(gx, gy))


def eez_mask(sst):
    geom = json.load(open("india_eez.geojson"))["geometry"]
    lon, lat = np.meshgrid(sst.longitude.values, sst.latitude.values)
    points = np.column_stack([lon.ravel(), lat.ravel()])
    inside = np.zeros(len(points), dtype=bool)
    for polygon in geom["coordinates"]:
        inside |= Polygon(polygon[0]).contains_points(points)
    return sst.copy(data=inside.reshape(lon.shape))


def label_zones(pfz, ocean):
    mask = ndimage.binary_dilation(pfz.values, iterations=DILATE) & ocean.values
    labels, n = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, range(1, n + 1))
    keep = np.flatnonzero(sizes >= MIN_PIXELS) + 1
    labels = np.where(np.isin(labels, keep), labels, 0)
    return labels, keep


def region_of(lat, lon):
    for name, (lat_min, lat_max, lon_min, lon_max) in REGIONS.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return None


def nearest_harbour(lat, lon):
    best = None
    for name, (hlat, hlon) in HARBOURS.items():
        p1, p2 = np.deg2rad(hlat), np.deg2rad(lat)
        dlon = np.deg2rad(lon - hlon)
        a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
        km = 2 * EARTH_KM * np.arcsin(np.sqrt(a))
        if best is None or km < best[1]:
            y = np.sin(dlon) * np.cos(p2)
            x = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dlon)
            bearing = np.rad2deg(np.arctan2(y, x)) % 360
            best = (name, km, COMPASS[int((bearing + 11.25) // 22.5) % 16])
    return best


def outline(labels, label, box, lat, lon):
    rows = slice(max(box[0].start - 1, 0), box[0].stop + 1)
    cols = slice(max(box[1].start - 1, 0), box[1].stop + 1)
    mask = (labels[rows, cols] == label).astype(float)
    lines = contour_generator(lon[cols], lat[rows], mask).lines(0.5)
    ring = np.round(max(lines, key=len), 3).tolist()
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def describe_zones(sst, chl, depth, pfz, labels, ids):
    lat = sst.latitude.values
    lon = sst.longitude.values
    dlat = np.gradient(lat)[:, None] * KM_PER_DEG
    dlon = np.gradient(lon)[None, :] * KM_PER_DEG * np.cos(np.deg2rad(lat))[:, None]
    cell_km2 = dlat * dlon

    core = labels * pfz.values
    centers = ndimage.center_of_mass(labels > 0, labels, ids)
    areas = ndimage.sum(cell_km2, labels, ids)
    mean_sst = ndimage.mean(sst.values, core, ids)
    mean_chl = ndimage.mean(chl.values, core, ids)
    boxes = ndimage.find_objects(labels)

    zones = []
    for label, (row, col), area, s, c in zip(ids, centers, areas, mean_sst, mean_chl):
        zlat = float(np.interp(row, np.arange(len(lat)), lat))
        zlon = float(np.interp(col, np.arange(len(lon)), lon))
        region = region_of(zlat, zlon)
        if region is None:
            continue
        depth_m = int(depth.sel(latitude=zlat, longitude=zlon, method="nearest"))
        harbour, km, direction = nearest_harbour(zlat, zlon)
        zones.append({
            "id": len(zones) + 1,
            "region": region,
            "lat": round(zlat, 3),
            "lon": round(zlon, 3),
            "area_km2": round(float(area), 1),
            "sst": round(float(s), 2),
            "chl": round(float(c), 3),
            "depth_m": depth_m,
            "harbour": harbour,
            "bearing": direction,
            "distance_km": round(float(km)),
            "advisory": f"{harbour}: {direction}, {km:.0f} km, depth {depth_m} m",
            "outline": outline(labels, label, boxes[label - 1], lat, lon),
        })
    return zones


def write_tables(out, zones):
    rows = [{k: v for k, v in z.items() if k != "outline"} for z in zones]
    with open(out / "zones.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [z["outline"]]},
            "properties": row,
        }
        for z, row in zip(zones, rows)
    ]
    with open(out / "zones.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)


def plot_region(out, date, name, sst, chl, labels, zones):
    lat_min, lat_max, lon_min, lon_max = REGIONS[name]
    box = dict(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    s = sst.sel(**box)
    c = chl.sel(**box)
    z = sst.copy(data=labels > 0).sel(**box)

    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    s.plot(ax=ax, cmap="RdYlBu_r", cbar_kwargs={"label": "SST (°C)", "shrink": 0.7})
    ax.contour(c.longitude, c.latitude, c >= CHL_MIN, levels=[0.5], colors="green", linewidths=0.6)
    ax.contourf(z.longitude, z.latitude, z, levels=[0.5, 1.5], colors="none", hatches=["////"])
    ax.contour(z.longitude, z.latitude, z, levels=[0.5], colors="black", linewidths=1)
    for zone in zones:
        if zone["region"] == name:
            ax.annotate(str(zone["id"]), (zone["lon"], zone["lat"]), fontsize=7, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_title(f"{name} — {date}\nblack: PFZ, green: chl ≥ {CHL_MIN} mg/m³")
    slug = name.lower().replace(" & ", "_").replace(" ", "_")
    fig.savefig(out / f"{slug}.png", dpi=110)
    plt.close(fig)


def plot_check(out, date, sst, grad, chl, pfz):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)

    sst.plot(ax=axes[0], cmap="RdYlBu_r", cbar_kwargs={"label": "SST (°C)"})
    axes[0].contour(sst.longitude, sst.latitude, grad >= GRAD_MIN, levels=[0.5], colors="k", linewidths=0.4)
    axes[0].set_title(f"SST + fronts (≥ {GRAD_MIN} °C/km)")

    np.log10(chl).plot(ax=axes[1], cmap="viridis", vmin=-1.5, vmax=1, cbar_kwargs={"label": "log10 chl (mg/m³)"})
    axes[1].set_title("Chlorophyll-a")

    land = sst.isnull()
    land.where(land).plot(ax=axes[2], cmap="Greys", add_colorbar=False, vmin=0, vmax=2)
    pfz.where(pfz).plot(ax=axes[2], cmap="autumn", add_colorbar=False)
    axes[2].set_title(f"PFZ mask (front AND chl ≥ {CHL_MIN})")

    for ax in axes:
        ax.set_aspect("equal")
    fig.suptitle(date)
    fig.savefig(out / "check.png", dpi=110)
    plt.close(fig)


def run(date):
    out = Path("outputs") / date
    out.mkdir(parents=True, exist_ok=True)

    sst, chl, depth = load(date)
    ocean = sst.notnull() & eez_mask(sst)
    grad = sst_gradient(sst)
    pfz = (grad >= GRAD_MIN) & (chl >= CHL_MIN) & ocean
    labels, ids = label_zones(pfz, ocean)
    zones = describe_zones(sst, chl, depth, pfz, labels, ids)

    plot_check(out, date, sst, grad, chl, pfz)
    write_tables(out, zones)
    for name in REGIONS:
        plot_region(out, date, name, sst, chl, labels, zones)

    print(f"{len(zones)} zones written to {out}")
    for name in REGIONS:
        count = sum(z["region"] == name for z in zones)
        print(f"  {name}: {count}")
    return zones


if __name__ == "__main__":
    run(sys.argv[1])
