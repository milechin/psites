# psites
A python command line script for searching, ordering, and downloading data from Planet for multiple sites defined by GeoJson files containing a polygon for the area of interest.

This script has four commands: **search**, **order**, **check**, and **download**.  You can get help for each of these command by including the `-h` flag.

```bash
python psites.py search -h
```


# Example
## Setup
1. Clone the repository onto your local machine.
   ```bash
   git clone https://github.com/milechin/psites.git
   ```

2. The `example` directory contains two sub-directories, `aoi_geojson` and `output`.
   The `aoi_geojson` directory has two example GeoJSON files which contain a polygon representing the area of interest.  You can replace these with your own GeoJSON files for the sites of interest for you. The following are the requirements of the GeoJSON file:
   * The GeoJSON must contain one single polygon.
   * The filename of the GeoJSON is used throughout this script to track search results and to place orders.  So choose a name that is meaningful.
  
    **TIP:** One can create GeoJSON polygon files by going to https://geojson.io/
     
4. The python script `psites.py` is the executing script.  You will need to have Python 3 installed. This script was tested with Python 3.10.12 on the BU's Shared Compute Cluster.

## Search for Items
1. 

