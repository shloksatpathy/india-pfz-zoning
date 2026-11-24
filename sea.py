"""Sea-route distances from every harbour, so advisory distances go around land.

The ocean grid is MUR's land mask coarsened to 0.04° (a cell is ocean if any 0.02° pixel in it
is), 8-connected; Dijkstra runs from each harbour's nearest ocean cell.
Build the mask once with: uv run sea.py data/sst_<date>.nc
"""
import sys
from functools import cache

import numpy as np
import xarray as xr
from scipy import sparse
from scipy.sparse.csgraph import dijkstra

from harbours import HARBOURS

MASK = "sea_mask.npz"
KM_PER_DEG = 111.32
LANE_PENALTY = 1  # a km inside a shipping-lane cell costs 1 + this: halves lane km, 95% of routes ≤ 12% longer
SIMPLIFY_DEG = 0.01  # route lines keep vertices that bend more than ~1 km; 0.02 cut land at Chennai harbour


def write_mask(sst_path):
    sst = xr.open_dataset(sst_path).analysed_sst.squeeze("time").sortby("latitude")
    ocean = sst.notnull().coarsen(latitude=2, longitude=2, boundary="trim").max()
    np.savez_compressed(MASK, ocean=ocean.values, lat=ocean.latitude.values, lon=ocean.longitude.values)


@cache
def edges():
    """Grid lat, lon, ocean mask, and the 8-connected edges between ocean cells (source, target, km)."""
    m = np.load(MASK)
    ocean, lat, lon = m["ocean"], m["lat"], m["lon"]
    ny, nx = ocean.shape
    idx = np.arange(ny * nx).reshape(ny, nx)
    dy = (lat[1] - lat[0]) * KM_PER_DEG
    dx = (lon[1] - lon[0]) * KM_PER_DEG * np.cos(np.deg2rad(lat))[:, None]

    src, dst, km = [], [], []
    for di, dj in [(0, 1), (1, 0), (1, 1), (1, -1)]:
        rows = slice(0, ny - di)
        a = slice(max(0, -dj), nx - max(0, dj))
        b = slice(max(0, dj), nx - max(0, -dj))
        rows_b = slice(di, ny)
        ok = ocean[rows, a] & ocean[rows_b, b]
        step = np.hypot(dy * di, dx[rows] * dj) * np.ones(ok.shape)
        src.append(idx[rows, a][ok])
        dst.append(idx[rows_b, b][ok])
        km.append(step[ok])
    return lat, lon, ocean, np.concatenate(src), np.concatenate(dst), np.concatenate(km)


def harbour_cell(name):
    """Index of the ocean cell nearest to a harbour."""
    lat, lon, ocean = edges()[:3]
    cells = np.flatnonzero(ocean.ravel())
    clat, clon = np.repeat(lat, len(lon))[cells], np.tile(lon, len(lat))[cells]
    h = HARBOURS[name]
    return cells[np.argmin((clat - h[0]) ** 2 + ((clon - h[1]) * np.cos(np.deg2rad(h[0]))) ** 2)]


@cache
def routes():
    """Grid lat, lon, and per ocean cell the index of the nearest harbour by sea and its distance (km)."""
    lat, lon, ocean, src, dst, km = edges()
    graph = sparse.csr_matrix((km, (src, dst)), shape=(ocean.size,) * 2)
    dist = dijkstra(graph, directed=False, indices=[harbour_cell(name) for name in HARBOURS])
    return lat, lon, dist.argmin(axis=0), dist.min(axis=0)


def cell_of(lat_pt, lon_pt):
    lat, lon = edges()[:2]
    i = int(np.clip(np.rint((lat_pt - lat[0]) / (lat[1] - lat[0])), 0, len(lat) - 1))
    j = int(np.clip(np.rint((lon_pt - lon[0]) / (lon[1] - lon[0])), 0, len(lon) - 1))
    return i * len(lon) + j


def simplify(line, tolerance):
    """Douglas-Peucker in degrees: drop vertices closer than tolerance to the line between kept ones."""
    a, b = line[0], line[-1]
    v, w = b - a, line - a
    d = np.abs(v[0] * w[:, 1] - v[1] * w[:, 0]) / max(np.hypot(*v), 1e-12)
    k = int(np.argmax(d))
    if d[k] <= tolerance:
        return np.array([a, b])
    return np.vstack([simplify(line[: k + 1], tolerance)[:-1], simplify(line[k:], tolerance)])


def lane_routes(trips, lane):
    """Routes from harbours to points that cost (1 + LANE_PENALTY) per km in shipping-lane cells.
    trips: [(harbour name, lat, lon)]; lane: bool grid on the sea grid.
    Returns per trip (line [[lat, lon], ...] simplified, route km, km in lanes)."""
    lat, lon, ocean, src, dst, km = edges()
    in_lane = lane.ravel().astype(float)
    cost = km * (1 + LANE_PENALTY * (in_lane[src] + in_lane[dst]) / 2)
    graph = sparse.csr_matrix((cost, (src, dst)), shape=(ocean.size,) * 2)
    names = sorted({h for h, _, _ in trips})
    _, pred = dijkstra(graph, directed=False, indices=[harbour_cell(n) for n in names], return_predecessors=True)
    clat, clon = np.repeat(lat, len(lon)), np.tile(lon, len(lat))
    out = []
    for harbour, plat, plon in trips:
        row = pred[names.index(harbour)]
        cells = [cell_of(plat, plon)]
        while row[cells[-1]] >= 0:
            cells.append(row[cells[-1]])
        cells = np.array(cells[::-1])
        y, x = clat[cells], clon[cells]
        step = np.hypot(np.diff(y), np.diff(x) * np.cos(np.deg2rad(y[1:]))) * KM_PER_DEG
        lane_step = (in_lane[cells[1:]] + in_lane[cells[:-1]]) / 2
        line = simplify(np.column_stack([y, x]), SIMPLIFY_DEG)
        out.append((np.round(line, 3).tolist(), float(step.sum()), float((step * lane_step).sum())))
    return out


def nearest(lat_pts, lon_pts):
    """Index into HARBOURS and sea-route km of the nearest harbour, for arrays of points."""
    lat, lon, best, best_km = routes()
    i = np.clip(np.rint((np.asarray(lat_pts) - lat[0]) / (lat[1] - lat[0])).astype(int), 0, len(lat) - 1)
    j = np.clip(np.rint((np.asarray(lon_pts) - lon[0]) / (lon[1] - lon[0])).astype(int), 0, len(lon) - 1)
    cell = i * len(lon) + j
    return best[cell], best_km[cell]


if __name__ == "__main__":
    write_mask(sys.argv[1])
