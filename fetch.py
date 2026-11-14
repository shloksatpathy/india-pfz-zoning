import sys
import urllib.request
from pathlib import Path

from regions import BBOX

SST_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.nc"
CHL_URL = "https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPVIIRSSQchlaWeekly.nc"


def download(url, path):
    if path.exists():
        print(f"exists: {path}")
        return
    print(f"downloading: {path}")
    urllib.request.urlretrieve(url, path)


def fetch(date):
    lat_min, lat_max, lon_min, lon_max = BBOX
    data = Path("data")
    data.mkdir(exist_ok=True)

    sst = f"analysed_sst[({date})][({lat_min}):2:({lat_max})][({lon_min}):2:({lon_max})]"
    download(f"{SST_URL}?{sst}", data / f"sst_{date}.nc")

    chl = f"chlor_a[({date})][(0.0)][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
    download(f"{CHL_URL}?{chl}", data / f"chl_{date}.nc")


if __name__ == "__main__":
    fetch(sys.argv[1])
