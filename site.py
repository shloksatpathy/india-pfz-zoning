import shutil
from pathlib import Path

from run import write_index

WEEKS = 8
FILES = ["zones.geojson", "zones.csv", "sst.png", "chl.png"]
SITE = Path("docs/site")


def build():
    (SITE / "outputs").mkdir(parents=True, exist_ok=True)
    for src in Path("outputs").glob("*/zones.geojson"):
        dest = SITE / "outputs" / src.parent.name
        dest.mkdir(exist_ok=True)
        for name in FILES:
            shutil.copy(src.parent / name, dest / name)

    dates = sorted(p.parent for p in (SITE / "outputs").glob("*/zones.geojson"))
    for old in dates[:-WEEKS]:
        shutil.rmtree(old)

    write_index(SITE / "outputs")
    shutil.copy("web/index.html", SITE / "index.html")
    shutil.copy("india_eez.geojson", SITE / "india_eez.geojson")
    print(f"site: {len(dates[-WEEKS:])} dates in {SITE}")


if __name__ == "__main__":
    build()
