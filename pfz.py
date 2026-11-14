import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

GRAD_MIN = 0.05  # °C/km, SST front threshold
CHL_MIN = 0.3  # mg/m³, productive water threshold
KM_PER_DEG = 111.32


def load(date):
    sst = xr.open_dataset(f"data/sst_{date}.nc").analysed_sst.squeeze("time").sortby("latitude")
    chl = xr.open_dataset(f"data/chl_{date}.nc").chlor_a.squeeze(["time", "altitude"]).sortby("latitude")
    chl = chl.interp_like(sst, method="nearest")
    return sst, chl


def sst_gradient(sst):
    y_km = sst.latitude.values * KM_PER_DEG
    x_km = sst.longitude.values * KM_PER_DEG
    gy, gx = np.gradient(sst.values, y_km, x_km)
    gx = gx / np.cos(np.deg2rad(sst.latitude.values))[:, None]
    return sst.copy(data=np.hypot(gx, gy))


def plot_check(date, sst, grad, chl, pfz):
    out = Path("outputs") / date
    out.mkdir(parents=True, exist_ok=True)
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


def run(date):
    sst, chl = load(date)
    grad = sst_gradient(sst)
    pfz = (grad >= GRAD_MIN) & (chl >= CHL_MIN)
    print(f"gradient p50/p90/p99: {np.nanpercentile(grad, [50, 90, 99]).round(3)} °C/km")
    print(f"front pixels: {int((grad >= GRAD_MIN).sum())}, productive pixels: {int((chl >= CHL_MIN).sum())}, pfz pixels: {int(pfz.sum())}")
    plot_check(date, sst, grad, chl, pfz)


if __name__ == "__main__":
    run(sys.argv[1])
