import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from regions import BBOX

SST_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41.nc"
ETOPO_URL = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/etopo180.nc"
CHL_URL = "https://coastwatch.noaa.gov/erddap/griddap/noaacwN20VIIRSchlaWeekly.nc"
COASTWATCH = "https://coastwatch.noaa.gov/erddap/griddap/"
PFEG = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/"
# daily chlorophyll, same variable and 0.0375° grid: sensor -> dataset
CHL_DAILY = {
    "n20": "noaacwN20VIIRSchlaDaily",  # NOAA-20 VIIRS
    "npp": "noaacwNPPVIIRSchlaDaily",  # S-NPP VIIRS
    "s3a": "noaacwS3AOLCIchlaDaily",  # Sentinel-3A OLCI
    "s3b": "noaacwS3BOLCIchlaDaily",  # Sentinel-3B OLCI
}
CHL_DAYS = 7  # daily composite window, ending at the SST date
# other ocean parameters, daily: name -> (dataset URL, variables, index for the extra altitude axis or "", days averaged)
EXTRA = {
    "sla": (f"{COASTWATCH}noaacwBLENDEDsshDaily", ["sla"], "", 1),
    "wind": (f"{PFEG}erdQCwindproducts3day", ["wind_speed", "ekman_upwelling"], "[(10.0)]", 1),  # Metop-C ASCAT, 3-day
    "cur": (f"{COASTWATCH}noaacwBLENDEDNRTcurrentsDaily", ["u_current", "v_current"], "", 1),  # geostrophic, altimetry
    "sss": (f"{COASTWATCH}noaacwSMAPsssDaily", ["sss"], "[(0.0)]", 3),  # SMAP; one day covers 40 - 85% of the sea, 3 days ~97%
}
EXTRA_LOOKBACK_DAYS = 10
# AIS traffic, Global Fishing Watch 4Wings API (token in GFW_TOKEN): name -> (dataset, vessel type filter or None)
GFW_URL = "https://gateway.api.globalfishingwatch.org/v3/4wings/report"
TRAFFIC = {
    "fishing": ("public-global-presence:latest", "vessel_type in ('fishing')"),
    "merchant": ("public-global-presence:latest", "vessel_type in ('cargo','passenger')"),
    "effort": ("public-global-fishing-effort:latest", None),  # apparent fishing hours
}
TRAFFIC_DAYS = 7  # ending on the newest GFW day on or before the SST date (GFW lags ~4 days)


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


def fetch_extra(name, sst_date):
    """Newest days on or before sst_date of an EXTRA dataset, saved as data/<name>_<sst_date>.nc."""
    url, variables, alt, n = EXTRA[name]
    start = date.fromisoformat(sst_date) - timedelta(days=EXTRA_LOOKBACK_DAYS)
    days = [d for d in erddap_dates(f"{url}.csv?time[({start}):1:(last)]") if d <= sst_date][-n:]
    lat_min, lat_max, lon_min, lon_max = BBOX
    box = f"[({days[0]}):1:({days[-1]})]{alt}[({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
    query = ",".join(f"{v}{box}" for v in variables)
    download(f"{url}.nc?{query}", Path("data") / f"{name}_{sst_date}.nc")


def gfw_report(dataset, vessel_filter, start, end, box, temporal="ENTIRE"):
    """4Wings report rows (lat, lon = 0.1° cell centre, hours) for days start .. end - 1 in box (lat_min, lat_max, lon_min, lon_max)."""
    params = {
        "format": "JSON",
        "datasets[0]": dataset,
        "spatial-resolution": "LOW",
        "temporal-resolution": temporal,
        "date-range": f"{start},{end}",
    }
    if vessel_filter:
        params["filters[0]"] = vessel_filter
    lat_min, lat_max, lon_min, lon_max = box
    ring = [[lon_min, lat_min], [lon_max, lat_min], [lon_max, lat_max], [lon_min, lat_max], [lon_min, lat_min]]
    request = urllib.request.Request(
        f"{GFW_URL}?{urllib.parse.urlencode(params)}",
        data=json.dumps({"geojson": {"type": "Polygon", "coordinates": [ring]}}).encode(),
        # GFW refuses the default Python-urllib agent
        headers={"Authorization": f"Bearer {os.environ['GFW_TOKEN']}", "Content-Type": "application/json", "User-Agent": "india-pfz-zoning"},
    )
    with urllib.request.urlopen(request, timeout=300) as r:
        entries = json.load(r)["entries"][0]
    return list(entries.values())[0] or []


def fetch_traffic(sst_date):
    """Weekly AIS presence (fishing, merchant) and fishing effort on 0.1° cells, saved as data/traffic_<sst_date>.json."""
    path = Path("data") / f"traffic_{sst_date}.json"
    if path.exists():
        print(f"exists: {path}")
        return
    print(f"downloading: {path}")
    sst_day = date.fromisoformat(sst_date)
    # newest day with data: daily presence in a small box off Mumbai
    days = gfw_report(TRAFFIC["merchant"][0], None, sst_day - timedelta(days=14), sst_day + timedelta(days=1), (18.5, 19.5, 72.0, 73.0), "DAILY")
    end = max(date.fromisoformat(r["date"]) for r in days)
    start = end - timedelta(days=TRAFFIC_DAYS - 1)
    data = {"dates": [start.isoformat(), end.isoformat()]}
    for name, (dataset, vessel_filter) in TRAFFIC.items():
        rows = gfw_report(dataset, vessel_filter, start, end + timedelta(days=1), BBOX)
        data[name] = [[r["lat"], r["lon"], r["hours"]] for r in rows]
    json.dump(data, open(path, "w"))


def fetch(sst_date):
    lat_min, lat_max, lon_min, lon_max = BBOX
    data = Path("data")
    data.mkdir(exist_ok=True)

    sst = f"analysed_sst[({sst_date})][({lat_min}):2:({lat_max})][({lon_min}):2:({lon_max})]"
    download(f"{SST_URL}?{sst}", data / f"sst_{sst_date}.nc")

    etopo = f"altitude[({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
    download(f"{ETOPO_URL}?{etopo}", data / "etopo.nc")


def fetch_chl(chl_date):
    lat_min, lat_max, lon_min, lon_max = BBOX
    chl = f"chlor_a[({chl_date})][(0.0)][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
    download(f"{CHL_URL}?{chl}", Path("data") / f"chl_n20_{chl_date}.nc")


if __name__ == "__main__":
    fetch(sys.argv[1])
    fetch_chl(sys.argv[2])
