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
1. To search for items run the search command with three required arguments:
    ```bash
    python psites.py search <min_year> <max_year> <path to geojson files>
    ```

    For this example we will search for items collected in 2016 for sites defined by GeoJSON files in directory `./example/aoi_geojson`:
    ```bash
    python psites.py search 2016 2017 ./example/aoi_geojson
    ```
2. If the environment variable `PL_API_KEY` is not set to your API Key, the script will prompt for your Planet API Key, as shown in the following output example:
    ```console
    [~]$ python psites.py search 2016 2017 ./example/aoi_geojson
    Found 2 GeoJSON files. In directory: 
    ./example/aoi_geojson

    GeoJSON Files found:
    PlumIsland.geojson
    ProvinceTown.geojson


    Authenticating with Planet Server....Please provide API key below, or define it by setting the PL_API_KEY environment variable before running the code.
    Planet API Key ( or q to quit) :
    ```

    Copy and paste your API Key into the terminal and hit Enter/Return.

3. For each GeoJSON file a search result will appear in the console.  You may need to scroll up to see it.  Below is an example of the search result for PlumIsland.

    ```console
    ############################################
    ###### SUMMARY OF SEARCH RESULTS  ##########
    ############################################
    ---------------- SITE: PLUMISLAND --------------------

    SUMMARY OF SITE: 
	    Site Name: PlumIsland
	    AOI Geometry Path: ./example/aoi_geojson/PlumIsland.geojson 
    SEARCH CRITERIA: 
	    Download Permission Filter On: True
	    Year Range: 2016-2017
	    Cloud Cover Range: 0.0-0.5

    Total items found: 276



   YEAR: 2016
	    Total Items: 276 
	    Item Type: PSScene

	    Asset Name                    Count  % of total Items
	    basic_analytic_4b             215    78%
	    basic_analytic_4b_rpc         215    78%
	    basic_analytic_4b_xml         215    78%
	    basic_udm2                    276    100%
	    ortho_analytic_3b             220    80%
	    ortho_analytic_3b_xml         220    80%
	    ortho_analytic_4b             215    78%
	    ortho_analytic_4b_sr          85     31%
	    ortho_analytic_4b_xml         215    78%
	    ortho_udm2                    276    100%
	    ortho_visual                  276    100%
    ```
    The search result will group the results by year.  For each year it will indicate the "Total Items" found and the "Item Type" (When placing an order, you will need to specify an "Item Type".). The table that follows show the asset types derived from the "items".  Not all the items are included in the creation of assetts and so the count and percent of total items are included.  

    Further down the summary, the Item Type and Asset Type definitions are printed out.  Below is an example of the output showing definitions for "PSScene" item type and "basic_analytic_4b_rpc" asset name:
   ``` console
    ITEM TYPE DEFINITIONS
    PSScene
    PlanetScope Scene 
    Description: 8-band PlanetScope imagery that is framed as captured. 


    ASSET NAME DEFINITIONS
    basic_analytic_4b_rpc
    Display Name: Unprojected top of atmosphere radiance (4 Band) rational polynomial coefficients for rectification 
    Description: Rational polynomial coefficient for unorthorectified analytic image stored as 12-bit digital numbers.
   ...

   ```

## Place an Order
1. Planet provides downloads in "bundle" packages. Using the link below, find the appropriate 'bundle' that contain the 'item type' and 'assets' of interest to you.
https://developers.planet.com/apis/orders/product-bundles-reference/

2. To place the order use the **order** command and specify the same arguments as for the search, but include the bundle and item option.
   ```bash
   psites.py order -bundle <bundle_name> -item <item_name> <min_year> <max_year> <path to geojson files>
   ```
   
   For our example we will request the "analytic_udm2" bundle of item "PSScene":
   ```bash
   psites.py order -bundle analytic_udm2 -item PSScene 2016 2017 ./example/aoi_geojson
   ```

