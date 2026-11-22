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


def write_mask(sst_path):
    sst = xr.open_dataset(sst_path).analysed_sst.squeeze("time").sortby("latitude")
    ocean = sst.notnull().coarsen(latitude=2, longitude=2, boundary="trim").max()
    np.savez_compressed(MASK, ocean=ocean.values, lat=ocean.latitude.values, lon=ocean.longitude.values)


@cache
def routes():
    """Grid lat, lon, and per ocean cell the index of the nearest harbour by sea and its distance (km)."""
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
    graph = sparse.csr_matrix((np.concatenate(km), (np.concatenate(src), np.concatenate(dst))), shape=(ny * nx,) * 2)

    cells = np.flatnonzero(ocean.ravel())
    clat, clon = np.repeat(lat, nx)[cells], np.tile(lon, ny)[cells]
    starts = [cells[np.argmin((clat - h[0]) ** 2 + ((clon - h[1]) * np.cos(np.deg2rad(h[0]))) ** 2)] for h in HARBOURS.values()]
    dist = dijkstra(graph, directed=False, indices=starts)
    return lat, lon, dist.argmin(axis=0), dist.min(axis=0)


def nearest(lat_pts, lon_pts):
    """Index into HARBOURS and sea-route km of the nearest harbour, for arrays of points."""
    lat, lon, best, best_km = routes()
    i = np.clip(np.rint((np.asarray(lat_pts) - lat[0]) / (lat[1] - lat[0])).astype(int), 0, len(lat) - 1)
    j = np.clip(np.rint((np.asarray(lon_pts) - lon[0]) / (lon[1] - lon[0])).astype(int), 0, len(lon) - 1)
    cell = i * len(lon) + j
    return best[cell], best_km[cell]


if __name__ == "__main__":
    write_mask(sys.argv[1])
