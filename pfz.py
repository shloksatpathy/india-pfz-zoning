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
from scipy.spatial import cKDTree

from harbours import HARBOURS
from regions import REGIONS, THRESHOLDS

DILATE = 2  # pixels, joins nearby front pixels into one zone
MIN_PIXELS = 50  # zones smaller than this (~240 km²) are dropped
KM_PER_DEG = 111.32
SST_RANGE = (26, 32)  # °C, overlay colour scale (web/index.html legend uses the same)
LOG_CHL_RANGE = (-1.5, 1)  # log10 mg/m³, overlay colour scale
OVERLAY_STEP = 2  # overlay keeps every 2nd pixel
POINT_TILE_KM = 30  # one advisory point per tile of this size
MIN_TILE_PIXELS = 20  # ~100 km²; smaller tiles get no point, except a zone's largest tile
MAX_HARBOUR_KM = 300  # zones farther than this from every harbour are dropped
EARTH_KM = 6371.0
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def load(sst_date, chl_date):
    sst = xr.open_dataset(f"data/sst_{sst_date}.nc").analysed_sst.squeeze("time").sortby("latitude")
    chl = xr.open_dataset(f"data/chl_n20_{chl_date}.nc").chlor_a.squeeze(["time", "altitude"]).sortby("latitude")
    chl = chl.interp_like(sst, method="nearest")
    depth = -xr.open_dataset("data/etopo.nc").altitude.sortby("latitude")
    return sst, chl, depth


def km_xy(lon, lat):
    return np.column_stack([lon * KM_PER_DEG * np.cos(np.deg2rad(lat)), lat * KM_PER_DEG])


def threshold_grids(sst):
    """Per-pixel GRAD_MIN and CHL_MIN from the region of the nearest harbour."""
    lon, lat = np.meshgrid(sst.longitude.values, sst.latitude.values)
    harbours = list(HARBOURS.values())
    tree = cKDTree(km_xy(np.array([h[1] for h in harbours]), np.array([h[0] for h in harbours])))
    nearest = tree.query(km_xy(lon.ravel(), lat.ravel()))[1].reshape(lon.shape)
    grad_min = np.array([THRESHOLDS[h[2]][0] for h in harbours])[nearest]
    chl_min = np.array([THRESHOLDS[h[2]][1] for h in harbours])[nearest]
    return sst.copy(data=grad_min), sst.copy(data=chl_min)


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


def nearest_harbour(lat, lon):
    best = None
    for name, (hlat, hlon, _) in HARBOURS.items():
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
    rings = []
    for line in contour_generator(lon[cols], lat[rows], mask).lines(0.5):
        ring = np.round(line, 3).tolist()
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        rings.append(ring)

    # a ring inside an odd number of other rings is a hole
    depth = [sum(Polygon(o).contains_point(r[0]) for o in rings if o is not r) for r in rings]
    polygons = []
    for outer, d in zip(rings, depth):
        if d % 2 == 0:
            holes = [r for r, dr in zip(rings, depth) if dr == d + 1 and Polygon(outer).contains_point(r[0])]
            polygons.append([outer, *holes])
    if len(polygons) == 1:
        return {"type": "Polygon", "coordinates": polygons[0]}
    return {"type": "MultiPolygon", "coordinates": polygons}


def advisory(lat, lon, depth):
    depth_m = int(depth.sel(latitude=lat, longitude=lon, method="nearest"))
    harbour, km, direction = nearest_harbour(lat, lon)
    return {
        "lat": round(lat, 3),
        "lon": round(lon, 3),
        "depth_m": depth_m,
        "harbour": harbour,
        "bearing": direction,
        "distance_km": round(float(km)),
        "advisory": f"{harbour}: {direction}, {km:.0f} km, depth {depth_m} m",
    }


def nearest_pixel(plat, plon, lat, lon):
    i = np.argmin((plat - lat) ** 2 + (plon - lon) ** 2)
    return float(plat[i]), float(plon[i])


def tile_points(plat, plon):
    ty = np.floor(plat * KM_PER_DEG / POINT_TILE_KM)
    tx = np.floor(plon * KM_PER_DEG * np.cos(np.deg2rad(plat.mean())) / POINT_TILE_KM)
    tiles, tile_of, counts = np.unique(np.column_stack([ty, tx]), axis=0, return_inverse=True, return_counts=True)
    points = []
    for t in range(len(tiles)):
        if counts[t] < MIN_TILE_PIXELS and t != np.argmax(counts):
            continue
        inside = tile_of.ravel() == t
        points.append(nearest_pixel(plat[inside], plon[inside], plat[inside].mean(), plon[inside].mean()))
    return points


def describe_zones(sst, chl, depth, pfz, labels, ids):
    lat = sst.latitude.values
    lon = sst.longitude.values
    dlat = np.gradient(lat)[:, None] * KM_PER_DEG
    dlon = np.gradient(lon)[None, :] * KM_PER_DEG * np.cos(np.deg2rad(lat))[:, None]
    cell_km2 = dlat * dlon

    core = labels * pfz.values
    areas = ndimage.sum(cell_km2, labels, ids)
    mean_sst = ndimage.mean(sst.values, core, ids)
    mean_chl = ndimage.mean(chl.values, core, ids)
    boxes = ndimage.find_objects(labels)

    zones = []
    for label, area, s, c in zip(ids, areas, mean_sst, mean_chl):
        rows, cols = np.nonzero(labels[boxes[label - 1]] == label)
        plat = lat[boxes[label - 1][0]][rows]
        plon = lon[boxes[label - 1][1]][cols]
        zlat, zlon = nearest_pixel(plat, plon, plat.mean(), plon.mean())
        points = [advisory(plat_, plon_, depth) for plat_, plon_ in tile_points(plat, plon)]
        closest = min(points, key=lambda pt: pt["distance_km"])
        if closest["distance_km"] > MAX_HARBOUR_KM:
            continue
        region = HARBOURS[closest["harbour"]][2]
        zone_id = len(zones) + 1
        points = [{"zone_id": zone_id, "point": n + 1, "region": region, **pt} for n, pt in enumerate(points)]
        zones.append({
            "id": zone_id,
            "region": region,
            "lat": round(zlat, 3),
            "lon": round(zlon, 3),
            "area_km2": round(float(area), 1),
            "sst": round(float(s), 2),
            "chl": round(float(c), 3),
            "depth_m": int(depth.sel(latitude=zlat, longitude=zlon, method="nearest")),
            "points": len(points),
            "harbour": closest["harbour"],
            "bearing": closest["bearing"],
            "distance_km": closest["distance_km"],
            "advisory": closest["advisory"],
            "geometry": outline(labels, label, boxes[label - 1], lat, lon),
            "point_list": points,
        })
    return zones


FIELDS = ["id", "region", "lat", "lon", "area_km2", "sst", "chl", "depth_m", "points", "harbour", "bearing", "distance_km", "advisory"]
POINT_FIELDS = ["zone_id", "point", "region", "lat", "lon", "depth_m", "harbour", "bearing", "distance_km", "advisory"]


def write_tables(out, zones, sst_date, chl_date):
    rows = [{k: z[k] for k in FIELDS} for z in zones]
    points = [pt for z in zones for pt in z["point_list"]]
    with open(out / "zones.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with open(out / "points.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=POINT_FIELDS)
        writer.writeheader()
        writer.writerows(points)

    features = [
        {
            "type": "Feature",
            "geometry": z["geometry"],
            "properties": row,
        }
        for z, row in zip(zones, rows)
    ] + [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [pt["lon"], pt["lat"]]},
            "properties": {"kind": "point", **pt},
        }
        for pt in points
    ]
    with open(out / "zones.geojson", "w") as f:
        json.dump({"type": "FeatureCollection", "sst_date": sst_date, "chl_date": chl_date, "features": features}, f)


def plot_region(out, date, name, sst, chl, labels, zones):
    lat_min, lat_max, lon_min, lon_max = REGIONS[name]
    box = dict(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    s = sst.sel(**box)
    c = chl.sel(**box)
    z = sst.copy(data=labels > 0).sel(**box)

    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    s.plot(ax=ax, cmap="RdYlBu_r", cbar_kwargs={"label": "SST (°C)", "shrink": 0.7})
    chl_min = THRESHOLDS[name][1]
    ax.contour(c.longitude, c.latitude, c >= chl_min, levels=[0.5], colors="green", linewidths=0.6)
    ax.contourf(z.longitude, z.latitude, z, levels=[0.5, 1.5], colors="none", hatches=["////"])
    ax.contour(z.longitude, z.latitude, z, levels=[0.5], colors="black", linewidths=1)
    for zone in zones:
        if zone["region"] == name:
            ax.annotate(str(zone["id"]), (zone["lon"], zone["lat"]), fontsize=7, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_title(f"{name} — {date}\nblack: PFZ, green: chl ≥ {chl_min} mg/m³")
    slug = name.lower().replace(" & ", "_").replace(" ", "_")
    fig.savefig(out / f"{slug}.png", dpi=110)
    plt.close(fig)


def plot_check(out, date, sst, grad, grad_min, chl, pfz):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), constrained_layout=True)

    sst.plot(ax=axes[0], cmap="RdYlBu_r", cbar_kwargs={"label": "SST (°C)"})
    axes[0].contour(sst.longitude, sst.latitude, grad >= grad_min, levels=[0.5], colors="k", linewidths=0.4)
    axes[0].set_title("SST + fronts (per-region gradient threshold)")

    np.log10(chl).plot(ax=axes[1], cmap="viridis", vmin=LOG_CHL_RANGE[0], vmax=LOG_CHL_RANGE[1], cbar_kwargs={"label": "log10 chl (mg/m³)"})
    axes[1].set_title("Chlorophyll-a")

    land = sst.isnull()
    land.where(land).plot(ax=axes[2], cmap="Greys", add_colorbar=False, vmin=0, vmax=2)
    pfz.where(pfz).plot(ax=axes[2], cmap="autumn", add_colorbar=False)
    axes[2].set_title("PFZ mask (front AND productive water)")

    for ax in axes:
        ax.set_aspect("equal")
    fig.suptitle(date)
    fig.savefig(out / "check.png", dpi=110)
    plt.close(fig)


def mercator_rows(da):
    lat = da.latitude.values
    y = np.log(np.tan(np.pi / 4 + np.deg2rad(lat) / 2))
    target = np.rad2deg(2 * np.arctan(np.exp(np.linspace(y[0], y[-1], len(lat) // OVERLAY_STEP))) - np.pi / 2)
    return da.sel(latitude=target, method="nearest").isel(longitude=slice(None, None, OVERLAY_STEP))


def write_overlays(out, sst, chl):
    plt.imsave(out / "sst.png", mercator_rows(sst).values[::-1], cmap="RdYlBu_r", vmin=SST_RANGE[0], vmax=SST_RANGE[1])
    log_chl = np.log10(mercator_rows(chl).values[::-1])
    plt.imsave(out / "chl.png", log_chl, cmap="viridis", vmin=LOG_CHL_RANGE[0], vmax=LOG_CHL_RANGE[1])


def run(sst_date, chl_date):
    out = Path("outputs") / sst_date
    out.mkdir(parents=True, exist_ok=True)

    sst, chl, depth = load(sst_date, chl_date)
    ocean = sst.notnull() & eez_mask(sst)
    grad = sst_gradient(sst)
    grad_min, chl_min = threshold_grids(sst)
    pfz = (grad >= grad_min) & (chl >= chl_min) & ocean
    labels, ids = label_zones(pfz, ocean)
    zones = describe_zones(sst, chl, depth, pfz, labels, ids)

    plot_check(out, sst_date, sst, grad, grad_min, chl, pfz)
    write_tables(out, zones, sst_date, chl_date)
    write_overlays(out, sst, chl)
    for name in REGIONS:
        plot_region(out, sst_date, name, sst, chl, labels, zones)

    print(f"{len(zones)} zones written to {out} (chlorophyll {chl_date})")
    for name in REGIONS:
        count = sum(z["region"] == name for z in zones)
        print(f"  {name}: {count}")
    return zones


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
