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

2. The `example` directory contains a directory called `aoi_geojson`.
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
   python psites.py order -bundle analytic_udm2 -item PSScene 2016 2017 ./example/aoi_geojson
   ```


   If you get an Exception like the one below:
   ```console
   Exception: Order name 'PlumIsland_2016_2017*' already exists on the Planet Server.
   Use --order_name_prefix flag to make order name unique or change the name of the geojson file.
   ```
   This indicates that the order name already exists.  Ordernames are used to track which orders are associated with which GeoJSON site.  To make the order name unique, include the `--order_name_prefix <string>` to add a prefix to the order name.  For example:
   ```bash
   python psites.py order --order_name_prefix 01 -bundle analytic_udm2 -item PSScene 2016 2017 ./example/aoi_geojson
   ```
   The command above will generate an order name `01_PlumIsland_2016_2017*`

3. Depending how big your order is for a site, the script may split it up into "chunks".  If Planet API accepts the order, the "status" will be "Accepted", as is shown below for sites "PlumIsland" and "ProvinceTown":
   ```console
   Preparing order for PlumIsland
   Number of chunks: 1

   Order Name: 04_PlumIsland_2016_2017_chunk_0 
   Status: Accepted 
   Order ID: 4be0c600-9600-4768-b9b1-156987fb5a17

   Preparing order for ProvinceTown
   Number of chunks: 1

   Order Name: 04_ProvinceTown_2016_2017_chunk_0 
   Status: Accepted 
   Order ID: 7a9cf439-faf1-4101-b1bd-fbc9424bba43
   ```

## Check on Order Status
1. The order may take some time to process by the Planet's server.  You can check the status of your order by using the **check** commmand.  When you placed the order in the previous step, a suggested check command is printed to the console that you can use to check the status of the specific order you placed.
   ```console
   ...
   To check on order, use the command below:

   psites.py check -min_y 2016 -max_y 2017 -gjson ./example/aoi_geojson 
   ```

2. When running a **check** command, three summary tables may appear in the console.
   * Failed Orders - A list of orders that were accepted but failed for some reason.
   * Not Ready Orders - Orders that are still being processed by Planet Servers.
   * Ready Orders - Orders that have successfully processed and ready for download.
  
     Below is an example output from the **check** command.
     ```console
     ######## FAILED ORDERS ###########
     Order Name                          Status   Created On                ID                                            Last Message
     ProvinceTown_2016_2017_chunk_0      failed   2024-01-31T17:51:34.395Z  7a9cf439-faf1-4101-b1bd-fbc9424bba43          Quota check failed - Over quota
     
     ########### READY ORDERS ###########
     Order Name                          Status   Created On                ID                                       Last Message
     ProvinceTown_2016_2017_chunk_0      success  2024-01-24T16:53:20.420Z  a9737d01-5940-400d-9c88-566377b2624f     Manifest delivery completed

     ```
## Downloading Data
When running the **check** command, the last line printed to the console provides the **download** command you can use to download the orders you see summarized above.  Below is an example console print out you might get:
   
```console
...
Use the following download command to download the files for successful orders listed above:
psites.py download -min_y 2016 -max_y 2017 -gjson ./example/aoi_geojson  <YOUR OUTPUT PATH>
```

Make sure to substitute "\<YOUR OUTPUT PATH\>" with the directory path of where you want to download the items to.  In this directory, a directory for each site will be created and the data will be downloaded to those directories.  

If you have some files that fail to download, run the **download** command again.  The script will skip any files that were already downloaded already.
