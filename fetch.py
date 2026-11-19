import sys
import urllib.request
from pathlib import Path

from regions import BBOX

SST_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.nc"
ETOPO_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.nc"
CHL_URL = "https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaWeekly.nc"


def download(url, path):
    if path.exists():
        print(f"exists: {path}")
        return
    print(f"downloading: {path}")
    urllib.request.urlretrieve(url, path)


def fetch(sst_date, chl_date):
    lat_min, lat_max, lon_min, lon_max = BBOX
    data = Path("data")
    data.mkdir(exist_ok=True)

    sst = f"analysed_sst[({sst_date})][({lat_min}):2:({lat_max})][({lon_min}):2:({lon_max})]"
    download(f"{SST_URL}?{sst}", data / f"sst_{sst_date}.nc")

    chl = f"chlor_a[({chl_date})][(0.0)][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
    download(f"{CHL_URL}?{chl}", data / f"chl_n20_{chl_date}.nc")

    etopo = f"altitude[({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
    download(f"{ETOPO_URL}?{etopo}", data / "etopo.nc")


if __name__ == "__main__":
    fetch(sys.argv[1], sys.argv[2])
