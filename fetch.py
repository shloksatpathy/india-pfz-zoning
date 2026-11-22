import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from regions import BBOX

SST_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.nc"
ETOPO_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.nc"
CHL_URL = "https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaWeekly.nc"
COASTWATCH = "https://coastwatch.noaa.gov/erddap/griddap/"
# daily chlorophyll, same variable and 0.0375° grid: sensor -> dataset
CHL_DAILY = {
    "n20": "noaacwN20VIIRSchlaDaily",  # NOAA-20 VIIRS
    "npp": "noaacwNPPVIIRSchlaDaily",  # S-NPP VIIRS
    "s3a": "noaacwS3AOLCIchlaDaily",  # Sentinel-3A OLCI
    "s3b": "noaacwS3BOLCIchlaDaily",  # Sentinel-3B OLCI
}
CHL_DAYS = 7  # daily composite window, ending at the SST date


def download(url, path):
    if path.exists():
        print(f"exists: {path}")
        return
    print(f"downloading: {path}")
    urllib.request.urlretrieve(url, path)


def erddap_dates(url):
    with urllib.request.urlopen(url) as r:
        lines = r.read().decode().splitlines()[2:]
    return [line[:10] for line in lines]


def daily_chl_days(sst_date):
    """(sensor, date) of every daily chlorophyll file in the CHL_DAYS window ending at sst_date."""
    end = date.fromisoformat(sst_date)
    start = end - timedelta(days=CHL_DAYS - 1)
    days = []
    for sensor, dataset in CHL_DAILY.items():
        times = erddap_dates(f"{COASTWATCH}{dataset}.csv?time[({start - timedelta(days=60)}):1:(last)]")
        days += [(sensor, d) for d in times if start.isoformat() <= d <= sst_date]
    return days


def fetch_daily_chl(sst_date):
    lat_min, lat_max, lon_min, lon_max = BBOX
    days = daily_chl_days(sst_date)
    for sensor, d in days:
        chl = f"chlor_a[({d})][(0.0)][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
        download(f"{COASTWATCH}{CHL_DAILY[sensor]}.nc?{chl}", Path("data") / f"chl_daily_{sensor}_{d}.nc")
    return days


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
