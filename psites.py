#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed May 19 14:27:44 2021

@author: Dennis Milechin, Research Computing Services, Boston University

@sources: This script was developed using documentation from Planet APIs website: https://developers.planet.com/docs/apis/

@Citation: 
author = Planet Labs PBC
organization = Planet
title = Planet Application Program Interface: In Space for Life on Earth
year = 2018--
url = "https://api.planet.com"

"""

import sys
import os
import json
import requests
import time
import errno
from datetime import datetime as dt
import fnmatch

# Setup Planet Data API base URL
base_url = "https://api.planet.com/data/v1"
stats_url = "{}/stats".format(base_url)
quick_url = "{}/quick-search".format(base_url)
orders_url = 'https://api.planet.com/compute/ops/orders/v2'
subs_url = "https://api.planet.com/subscriptions/v1"
date_format = '%Y-%m-%dT%H:%M:%S.%fZ'
api_key = None
default_item_type = ["PSScene", "REOrthoTile", "REScene", "SkySatScene", "SkySatScene", "SkySatCollect", "SkySatVideo", "Sentinel2L1C", "Landsat8L1G"]


class aoi:
    
    def __init__(self,  geom_path, min_year, max_year, min_cloud=0.0, max_cloud=0.5, allowed=True):
        
        self.site_name = os.path.splitext(os.path.basename(geom_path))[0]
        
        if(isinstance(geom_path, str) == False or os.path.isfile(geom_path) == False):
            raise ValueError("AOI GeoJSON file '{}' does not exist.".format(geom_path))

        self.geom_path = geom_path
        self.min_year = min_year
        self.max_year = max_year
        self.api_interval = "year"
        self.api_cloud_cover_min = min_cloud
        self.api_cloud_cover_max = max_cloud
        self.api_filter = setup_filter(minyear=min_year, 
                                       maxyear=max_year, 
                                       allowed= allowed, 
                                       api_cloud_cover_min= min_cloud, 
                                       api_cloud_cover_max=max_cloud )
        self.allowed = allowed
        self.search_results = None
        self.permission_tracker = None
        self.quick_result = None
        
        
        with open(geom_path, "r") as file:
            geo = json.load(file)
            
            if len(geo['features']) > 1:
                raise Exception("The GeoJSON has multiple polygons. Only one polygon is allowed for this tool.\n {}".format(geom_path))
            
            geom_type = geo["features"][0]['geometry']['type']
            
            if  geom_type.lower() != "polygon":
                raise Exception("This program only supports polygon features in GeoJSON file. This one contains {}.".format(geom_type))
            
            
            self.aoi_feature = geo["features"][0]['geometry']
            
                
    def __str__(self):
        
        return "\nSUMMARY OF SITE: \n" + \
                    "\tSite Name: " + self.site_name + "\n" + \
                    "\tAOI Geometry Path: "+ self.geom_path + " \n" + \
                "SEARCH CRITERIA: " + "\n" +\
                    "\tDownload Permission Filter On: " + str(self.allowed) +"\n" + \
                    "\tYear Range: " + str(self.min_year) + "-" + str(self.max_year) +"\n" + \
                    "\tCloud Cover Range: " + str(self.api_cloud_cover_min) + "-" + str(self.api_cloud_cover_max) +"\n"
   
     
    def __write_log__(self, text):
        """
        Prints text to the console with the current time and the name of the specific site the text is
        associated with.

        Parameters
        ----------
        site : str
            Site Name.
        text : str
            Text to be printed to the console.

        Returns
        -------
        None.

        """
        print(str(dt.now())+": ("+ self.site_name +")\t" + text)
        
    
        
        
    def item_search(self, quick_url=quick_url, item_types=default_item_type):
        """
        Submits an API requests to retrieve meta data for items that match the filter criteria.

        Parameters
        ----------
        quick_url : TYPE, optional
            DESCRIPTION. The default is quick_url. The url for searching Planet API

        Returns
        -------
        None.

        """
        
        print("Asking Planet for results.")
        
        # Get the API Key
        PLANET_API_KEY = os.environ["PL_API_KEY"] 
        
        # Setup the session to communicate with Planet's API
        session = requests.Session()
        session.auth = (PLANET_API_KEY, "")
        
        # Reset quick_result object
        self.quick_result = []
        self.id_list = []
        self.order_chunks = None
        
        # Create a dict to store how many items contain the desired assetts
        permission_tracker = []
        year_tracker = {}
          
        coords = self.aoi_feature["coordinates"]      # Feature coordinates
        api_filter = self.api_filter    # Filter to use for the search
        
        # Create a geometry filter component
        geometry_filter = {"type": "GeometryFilter",
            "field_name": "geometry",
            "config": {
              "type": "Polygon",
              "coordinates": coords
            }
        }
            
            # Append the geometry filter component to the api_filter object
        api_filter["config"].append(geometry_filter)
        
        # Setup the request data
        request = { "filter" : api_filter, "item_types" : item_types }
    
        # Send the POST request to the API stats endpoint
        res = session.post(quick_url, json=request)
        
        # Check the status code
        if(res.status_code != 200):
            self.__write_log__("Quick search  failed with code {}".format(res.status_code))
            self.__write_log__(json.dumps(res.json(), indent=2))
        else:
            
            geojson = res.json()    # retrieve API results
            self.quick_result.extend(geojson["features"])      # Save API results to aoi object
            
            
            # Check if 0 results were returned, if yes, continue to the next feature
            if(len(geojson["features"]) == 0):
                self.__write_log__("0 IDs returned in quick search.")
            
            # The API return may contain multiple pages of results.
            # Retrieve each page via "_next" until the feature count is 0.
            page = 1

                # Save ID for item in a list
            
            
            while(len(geojson["features"]) > 0):
                print("\rProcessing page {}".format(page), end="")
                # Extract the file IDs to be downloaded and append them to id_list
                for feature in geojson["features"]:
                    self.id_list.append(feature["id"])
                    
                    aq_year = str(dt.strptime(feature["properties"]["acquired"], date_format).year)
                    item_type = feature["properties"]["item_type"]
                    
                    if aq_year not in year_tracker.keys():
                        year_tracker[aq_year] = {item_type : {"assets_tracker": {}, "item_count": 1 }}
                    elif (item_type not in year_tracker[aq_year].keys()):
                        year_tracker[aq_year][item_type] = {"assets_tracker": {}, "item_count": 1 }
                    else:
                        year_tracker[aq_year][item_type]["item_count"] = year_tracker[aq_year][item_type]["item_count"] + 1
                        
                    

                    for asset in feature["assets"]:
                        if asset in year_tracker[aq_year][item_type]["assets_tracker"].keys():
                            year_tracker[aq_year][item_type]["assets_tracker"][asset]  = year_tracker[aq_year][item_type]["assets_tracker"][asset] + 1
                        else:
                            year_tracker[aq_year][item_type]["assets_tracker"][asset]  = 1
                            
                    for permission in feature["_permissions"]:
                        parsed_perm = permission.split(sep=".")[1].split(sep=":")[0]
                        if parsed_perm not in permission_tracker:
                            permission_tracker.append(parsed_perm)
                            
                 
                page = page + 1
                
                # Get the next page.  Sleep for 5 seconds so we are not hammering the server. 
                next_url = geojson["_links"]["_next"]
                
                time.sleep(0.1)
                    
                res = session.get(next_url)
                
                # Check if API call is a success
                if(res.status_code != 200):
                    self.__write_log__("Next page retrieval failed with code {}".format(res.status_code))
                    self.__write_log__(json.dumps(res.json(), indent=2))
                    self.__write_log__("Failed to retrieve entire list of results.  Check the status code to determine if its a server issue or user issue.")
                
                # Append the results to the json file already created.
                geojson = res.json()
                
                self.quick_result.extend(geojson["features"]) 
            
            print("\n")
            self.api_filter = api_filter
            
                  
        self.search_results = year_tracker
        self.permission_tracker = permission_tracker
    
    def print_search(self):   
        
        if(self.search_results == None):
            print("No search results to show.")
            
        year_tracker = self.search_results
        
        # Summary of results
        print("Total items found: {}\n\n".format(len(self.id_list)))
        
        item_type_list = []
        asset_type_list = []
        
        for year in sorted(year_tracker.keys()):
            print("\nYEAR: {}".format(year))
            for item_type in sorted(year_tracker[year].keys()):
                
                if item_type not in item_type_list:
                    item_type_list.append(item_type)
                
                print("\tTotal Items: {} \n\tItem Type: {}".format(year_tracker[year][item_type]["item_count"], item_type))
                print("\n\t{:30}{:<6} {:5}".format("Asset Name", "Count", "% of total Items"))
                for key in sorted(year_tracker[year][item_type]["assets_tracker"].keys()):
                    
                    if key not in asset_type_list:
                        asset_type_list.append(key)
                    
                    percent = year_tracker[year][item_type]["assets_tracker"][key] / year_tracker[year][item_type]["item_count"] 
                    
                    
                    print("\t{:30}{:<6} {:.0%}".format(key, year_tracker[year][item_type]["assets_tracker"][key], percent))

        if self.allowed == False:
            print("\n\nAssets Allowed to Download: {}\n".format(self.permission_tracker))
        
        print("\nITEM TYPE DEFINITIONS")   
        
        PLANET_API_KEY = os.environ["PL_API_KEY"] 
        with requests.Session() as session:
            session.auth = (PLANET_API_KEY, "")
            response = session.get("https://api.planet.com/data/v1/item-types")
            
            for x in response.json()["item_types"]:
                
                if x["id"] in item_type_list:
                    print("{} \n{} \nDescription: {} \n".format(x["id"], x["display_name"], x["display_description"]))
            
        print("\nASSET NAME DEFINITIONS")   
        
        PLANET_API_KEY = os.environ["PL_API_KEY"] 
        with requests.Session() as session:
            session.auth = (PLANET_API_KEY, "")
            response = session.get("https://api.planet.com/data/v1/asset-types")
            
            for x in response.json()["asset_types"]:
                
                if x["id"] in asset_type_list:
                    print("{}\nDisplay Name: {} \nDescription: {} \n".format(x["id"], x["display_name"], x["display_description"]))

            


        
        
class aoi_order(aoi):
    def __init__(self, 
                 geom_path, 
                 min_year, 
                 max_year, 
                 item_type,
                 bundle,
                 prefix,     
                 min_cloud=0.0, 
                 max_cloud=0.5, 
                 allowed=True):
        super().__init__(geom_path, min_year, max_year, min_cloud, max_cloud, allowed)
        
        
        self.item_type = item_type
        self.bundle = bundle
        self.prefix = prefix + "_" if prefix != None else ""
        
        current_orders = get_order_list()
        
        self.order_name = const_order_name(self.prefix, self.site_name, self.min_year, self.max_year)
        
        for order in current_orders:
            if fnmatch.fnmatch(order["name"], self.order_name + "*") == True:
                raise Exception("Order name '{}*' already exists on the Planet Server.  Use --order_name_prefix".format(self.order_name) +
                                " flag to make order name unique or change the name of the geojson file.\n\n" +
                                "Fetch the order list from Planet Server by running the following command: \n" + 
                                "python {} check".format(os.path.basename(__file__)))
        
        self.item_search(item_types=[item_type])
    
    def __str__(self):
        text = super().__str__()
        
        append =  "\nORDER DETAILS: \n" + \
                    "\tItem Type: {}\n".format(self.item_type) + \
                    "\tProduct Bundle: {}\n".format(self.bundle) +\
                    "\tOrder Name Prefix: {}\n".format(self.prefix) +\
                    "\tCheck Existing Orders: {}\n".format(self.check) +\
                    "\tTotal Items to Download: {}\n\n".format(len(self.id_list))
        
        return text + append
    
    
    def place_order(self, order_url=orders_url):
        
        summary_text = "Preparing order for {}".format(self.site_name)
        chunks = [self.id_list[x:x+400] for x in range(0, len(self.id_list), 400)]
        summary_text = "{}\nNumber of chunks: {}\n".format(summary_text, len(chunks))
        self.order_chunks = chunks
        if(len(chunks) >= 80):
            self.order_chunks = None
            raise Exception("More than 80 chunks will exceed Planet API order capacity.  Update search criteria to reduce number of results returned.")
            
        print(summary_text)
        
        
        headers = {'content-type': 'application/json'}
        PLANET_API_KEY = os.getenv('PL_API_KEY')
        
        with requests.Session() as session:
            # Authenticate
            session.auth = (PLANET_API_KEY, "")
            for count, chunk in enumerate(self.order_chunks):
                order_name = "{}_chunk_{}".format(self.order_name, count)
                
                request = {  
                   "name": order_name,
                   "order_type": "partial",
                   "products":[
                      {  
                         "item_ids": chunk,
                         "item_type": self.item_type,
                          
                         "product_bundle": self.bundle
                      }
                   ],
                   "tools": [
                    {
                      "clip": {
                        "aoi": {
                          "type": "Polygon",
                          "coordinates": self.aoi_feature["coordinates"]
                        }
                      }
                    }
                  ]
                }
                
               
                status = None
                order_id = None
                
                response = session.post(order_url, data=json.dumps(request), headers=headers)
                
                if(response.status_code != 202):
                    status = "Failed: {}".format(json.dumps(response.json(), indent=2))
                else:
                    order_id = response.json()['id']
                    status = "Accepted"
                
                print("Order Name: {} \nStatus: {} \nOrder ID: {}\n".format(order_name, status, order_id))
                
                    
        
           
def const_order_name(prefix, site_name, min_year, max_year):
    return "{}{}_{}_{}".format(prefix, site_name,  min_year, max_year)               

def check_base_server(subs_url=subs_url):
    """
    Checks if we can connect to the server using the API key provided

    Parameters
    ----------
    subs_url : str, optional
        The default is subs_url. Subscription URL to use for the test

    Returns
    -------
    PLANET_API_KEY : str
        The API Key used to connect to the Planet API service.

    """
    
    print("Authenticating with Planet Server....", end="")
    # Extract the API key from the environment variable
    PLANET_API_KEY = os.getenv('PL_API_KEY')
    
    # Check if the key exists, if not request for it
    if(isinstance(PLANET_API_KEY, str) == False or len(PLANET_API_KEY) == 0):
        print("Please provide API key below, or define it by setting" + \
                " the PL_API_KEY environment variable before running the code.")
                    
        PLANET_API_KEY = input('Planet API Key ( or q to quit) : ')
        
        if(PLANET_API_KEY.lower() == 'q'):
            sys.exit()
    
    # Loop until authentication is successful or 'q' is hit
    while True:
        
        # Setup test session
        session = requests.Session()
        session.auth = (PLANET_API_KEY, "")
        res = session.get(subs_url)
        
        # Check status code
        if(res.status_code == 401):
            # If code is 401 this is an authentication error.  Ask user to update API key.
            PLANET_API_KEY = input('Authentication failed.  Check to make sure you typed in the correct API key. Planet API Key ( or q to quit) : ')
            
            # If 'q' is entered, quit program
            if(PLANET_API_KEY.lower() == 'q'):
                sys.exit()
                
        elif(res.status_code != 200):
            # If code is not 401 then there was an issue connecting with server.
            print("Error connecting with server.  Status Code: {}".format(res.status_code))
            sys.exit()
        else:
            # Otherwise it is a success, break from loop
            print("Success\n")
            break
            
    
    # Set environment variable PL_API_KEY with the key
    os.environ["PL_API_KEY"] = PLANET_API_KEY
    
    
    


def setup_filter(minyear, maxyear, allowed, api_cloud_cover_min=0.0, api_cloud_cover_max=0.5 ):
    """
    Setup a basic search filter to use with Planet API

    Parameters
    ----------
    minyear : int
        Starting year search.
    maxyear : int
        End year search, excludes the maxyear.
    assets : list
        Assetts to search.
    api_cloud_cover_min : double, optional
        The default is 0.0. Minimal cloud cover in range of 0.0 - 1.0, where 1.0 is 100%.
    api_cloud_cover_max : double
        The default is 0.50. Maximum cloud cover in range of 0.0 - 1.0, where 1.0 is 100%.

    Returns
    -------
    and_filter : dict
        Filter object for Planet API.

    """
    
    # Date filter
    date_filter = {
        "type": "DateRangeFilter", # Type of filter -> Date Range
        "field_name": "acquired", # The field to filter on: "acquired" -> Date on which the "image was taken"
        "config": {
            "gte": "{}-01-01T00:00:00.000Z".format(minyear), # "gte" -> Greater than or equal to
            "lt":"{}-01-01T00:00:00Z".format(maxyear)
            }
        }
    
    # Ground control filter
    ground_control =  {
                    "type": "StringInFilter",
                    "config": ["true"],
                    "field_name": "ground_control"
                  }
    # Quality category filter
    quality_category = {
                    "type": "StringInFilter",
                    "config": ["standard"],
                    "field_name": "quality_category"
                  }
    # Cloud cover filter
    cloud_cover =  {
                     "type": "RangeFilter",
                     "field_name": "cloud_cover",
                     "config": {"gte": api_cloud_cover_min, "lte": api_cloud_cover_max}
                  }
    


    if(allowed == True):
        # Permission filter
        permission = {
            "type":"PermissionFilter",
            "config":[
                "assets:download"
                ]
            }

        # Combine the filters into one object.
        and_filter = {
            "type": "AndFilter",
            "config": [ 
                cloud_cover,
                quality_category,
                ground_control,
                date_filter,
                permission
                ]
            }
    else:
        and_filter = {
            "type": "AndFilter",
            "config": [ 
                cloud_cover,
                quality_category,
                ground_control,
                date_filter
                ]
            }
    
    return and_filter


def get_gjson_filelist(geojson_path):
    
    if(isinstance(geojson_path, str) == False or os.path.isdir(geojson_path) == False):
        raise ValueError("AOI GeoJSON directory '{}' does not exist.".format(geojson_path))
        
        
    # Find the GEOJSON files in the directory
    paths_list = os.listdir(geojson_path)
    paths_list = [site for site in paths_list if ".geojson" == os.path.splitext(site)[1].lower()]
    paths_list = [ os.path.join(geojson_path, file) for file in paths_list ]
    paths_list.sort()
    
    if len(paths_list) == 0:
        raise Exception("No geojson files found in: \n {}".format(geojson_path))
    
    print("Found {} GeoJSON files. In directory: \n {}\n".format(len(paths_list), geojson_path))
    
    print("GeoJSON Files found:")
    [print(os.path.basename(filename)) for filename in paths_list ]
    
    print("\n")
    return paths_list

def get_order_list(order_url=orders_url):
    
    PLANET_API_KEY = os.getenv('PL_API_KEY')
    
    orders_list = []
    with requests.Session() as session:
        # Authenticate
        session.auth = (PLANET_API_KEY, "")
        
        
        response = session.get(order_url)
        
        if(response.status_code == 200):
            
            order_resp = response.json()
            if("orders" in order_resp):
                orders_list.extend(order_resp["orders"])
        
        
        while("next" in response.json()["_links"]):
            
            time.sleep(3)
            next_url = response.json()["_links"]["next"]
            response = session.get(next_url)
            
            if(response.status_code == 200):
                order_resp = response.json()
                
                if("orders" in order_resp):
                    orders_list.extend(order_resp["orders"])
                    
    return orders_list


def filter_order_list(order_list, date_search=None, name_search=None, const_oname_list=None):
        
    filtered_olist = []
    
    for order in order_list:
        
        name_keep=False
        date_keep=False
        s_name_keep=False
    
        name_keep = True if (name_search == None or fnmatch.fnmatch(order["name"], name_search)) else False

            
        order_date = dt.strptime(order["created_on"], date_format)
        date_keep= True if (date_search == None or (date_search.date() == order_date.date())) else False

    
        if const_oname_list == None:
            s_name_keep=True
        else:
            for s_name in const_oname_list:
                if fnmatch.fnmatch(order["name"], s_name) == True:
                    s_name_keep = True
        
            
        if name_keep and date_keep and s_name_keep:
            filtered_olist.append(order)
    
    return filtered_olist


def search(geometry_path, min_year, max_year, min_cloud, max_cloud, allowed):

    json_files = get_gjson_filelist(geometry_path)
    
    
    # Check if the Planet base server is up and running
    check_base_server()
    
    # Create an aoi object for each site
    aoi_list = [aoi(geom_path = site, 
                    min_year = min_year,
                    max_year = max_year,
                    min_cloud = min_cloud,
                    max_cloud = max_cloud,
                    allowed = allowed
                    ) for site in json_files]

    
    for site in aoi_list:
        print( "------- SEARCH INITIATED FOR {} --------".format(site.site_name))
        print(site)
        site.item_search()
    
    print("############################################")
    print("###### SUMMARY OF SEARCH RESULTS  ##########")
    print("############################################")
    for site in aoi_list:
        print( "---------------- SITE: {} --------------------".format(site.site_name.upper()))
        print(site)
        site.print_search()
        
  
        
def order(geometry_path, 
         min_year, 
         max_year, 
         min_cloud, 
         max_cloud, 
         api_item_type, 
         product_bundle,
         prefix):

    
    json_files = get_gjson_filelist(geometry_path)
    
    
    # Check if the Planet base server is up and running
    check_base_server()  
    
    order_list = [aoi_order(geom_path = site, 
                    min_year = min_year,
                    max_year = max_year,
                    min_cloud = min_cloud,
                    max_cloud = max_cloud,
                    item_type = api_item_type,
                    bundle = product_bundle,
                    prefix = prefix
                    ) for site in json_files]
    
    
    for site in order_list:
        site.place_order()
        
    
    
def print_order_summary(filtered_olist):
    
    
    template = "{:35} {:8} {:25} {:40} {}"               
    print(template.format("Order Name","Status", "Created On", "ID", "Last Message"))   
    for order in filtered_olist:
        print(template.format(order["name"], order["state"], order["created_on"], order["id"], order["last_message"]))

    


def check(order_name_search=None, 
          order_url=orders_url, 
          order_date_search=None,
          min_year=None,
          max_year=None,
          geometry_path=None, 
          prefix=None):
    
    
    prefix = prefix + "_" if prefix != None else ""
    s_order_names = None
    
    if geometry_path != None:
        s_order_names = []
        json_files = get_gjson_filelist(geometry_path)
        
        for jfile in json_files:
            site_name = os.path.splitext(os.path.basename(jfile))[0]
            order_name = const_order_name(prefix, site_name, min_year, max_year)
            s_order_names.append(order_name + "*")
            
            
    date_search=None
    if order_date_search != None:
        try:
            date_search = dt.strptime(order_date_search, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError("{} \n\n Verify the -date, --order_date is formatted properly, as YYYY-MM-DD.\n Your entry: {}".format(e, order_date_search))
    
    
    orders_list = get_order_list() 
               
    if len(orders_list) == 0:
        raise ValueError("No orders found.")
        
    filtered_olist = filter_order_list(orders_list, 
                      date_search=date_search,
                      name_search=order_name_search,
                      const_oname_list=s_order_names)
    
    
    if len(filtered_olist) == 0:
        print("\n\nNo orders found using specified filter criteria.")
        
        if(order_name_search != None):
              print("--order_name {}".format(order_name_search))
        if(order_date_search != None):
              print("--order_date {}".format(order_date_search))
              
        success_orders = None
    else:
        
        
        failed_orders = [x for x in filtered_olist if x["state"] in ['failed']]
        success_orders = [x for x in filtered_olist if x["state"] in ['success', 'partial']]
        not_ready = [x for x in filtered_olist if x["state"] not in ['success', 'failed', 'partial']]
        
        if len(failed_orders) > 0:
            print("\n######## FAILED ORDERS ###########")
            print_order_summary(failed_orders) 
        
        if len(not_ready) > 0:
            print("\n\n########### NOT READY ORDERS ###########")
            print_order_summary(not_ready)
        
        if len(success_orders) > 0:
            print("\n\n########### READY ORDERS ###########")
            print_order_summary(success_orders)
            
        print("\n\n")
       
            
    return success_orders
        
        
def get_data(order_list, output_dir):
    
    print(" --- DOWNLOADING DATA ----")
    summary = {}

    PLANET_API_KEY = os.getenv('PL_API_KEY')
    
    
    if not os.path.exists(output_dir):
        try:
            print("\n\nNOTE: Output directory '{}' does not exist.  Creating directory.".format(output_dir))
            os.makedirs(output_dir)
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    
    with requests.Session() as session:
        # Authenticate
        session.auth = (PLANET_API_KEY, "")
        
        order_num=1
        
        for order in order_list:
            url = order["_links"]["_self"]
            order_name = order["name"]
            order_id = order["id"]
            
            print("Downloading order {} ({} of {}).".format(order_name, order_num, len(order_list)))
            print("Saving files to: {}".format(output_dir))
            r = session.get(url)
            if(r.status_code != 200):
                print("\n Failed to retrieve order {}. Status code: {}....Skipping".format(order_name, r.status_code))
                continue
            
            response = r.json()
            
            files_available = [os.path.basename(r['name']) for r in response['_links']['results']]
            need_to_download = [item for item in files_available if os.path.isfile(os.path.join(output_dir, item)) == False]

            failed_count = 0
            skipped_count = len(files_available) - len(need_to_download)
            success_count = 0 + skipped_count
            failed_files =[]
            
            if len(need_to_download) == 0:
                print("All files already downloaded, skipping this order.\n")
                order_num += 1
                
            else:
                for item in response['_links']['results']:
                    
                    item_basename = os.path.basename(item["name"])
                    dest = os.path.join(output_dir, item_basename)
                    url = item["location"]
                    
                    if item_basename not in need_to_download:
                        continue
                    
                    #site.__write_log__('downloading {} to {}'.format(item_basename, dest, url))
                    
                    r = requests.get(url, allow_redirects=True)
                    
                    if(r.status_code == 200):
                        with open(dest, "wb") as file1:
                            file1.write(r.content)
                            success_count += 1
                            
                    else:
                        print('\nERROR: File {} not downloaded. Status code {}\n'.format(r.status_code, item_basename))
                        failed_count += 1
                        json_r = r.json()
                        failed_files.append({"filename": item_basename, "status_code": r.status_code, "message": json_r})
                        time.sleep(3)
                        
                    output = "\rPending: {} Downloaded: {} Failed: {}".format(len(files_available)-success_count, success_count, failed_count)
                    print("{:100}".format(output),  end='', flush=True) 
                    
            
            print("DONE with order {}\n\n".format(order_name))
            
            
            order_num += 1
            json_file = os.path.join(output_dir, "{}.json".format(order_name))
            summary[order_name] = {"failed" : failed_count, "skipped":skipped_count, "success": success_count, "order_id": order_id, "failed_files":failed_files, "json": json_file}
            
            with open(json_file, "w") as download_stats_json:
                json.dump(summary, download_stats_json, indent=4, sort_keys=True)
                
            
    return summary


# [{'order_name': 'Boston_2016_2017_chunk_2', 'failed': 2, 'skipped': 387, 'success': 1874, 'order_id': 'a9737d01-5940-400d-9c88-566377b2624f', 'failed_files': [{'filename': '20161026_132339_1_0d05_3B_udm2_clip.tif', 'status_code': 500}, {'filename': '20161024_142108_1_0c45_3B_AnalyticMS_metadata_clip.xml', 'status_code': 500}]}]

def print_download_summary(summary, output_dir):
    
    print(" --- DOWNLOAD SUMMARY ----")
    template = "{:35} {:<10} {:<10} {:40}"    
    print(template.format("Order Name","Downloaded", "Failed", "JSON"))
    
    for order in summary:
        print(template.format(order, summary[order]["success"], summary[order]["failed"], summary[order]["json"]))
        
    print("\n\nNOTE:If you have failed downloads, run the download command again.  The script will only download files that don't exist in {}".format(output_dir))

def download(output_dir, 
             order_url=orders_url, 
             order_name_search=None, 
             order_date_search=None,
             min_year = None,
             max_year = None,
             geometry_path = None, 
             prefix=None
            ):
    
    check_base_server() 
    prefix = prefix + "_" if prefix != None else ""
    
    # Check if output directory exists
    if not os.path.exists(output_dir):
        try:
            print("NOTE: Output directory '{}' does not exist.  Creating directory.".format(output_dir))
            os.makedirs(output_dir)
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
        
    
    
    if geometry_path != None:
        
        json_files = get_gjson_filelist(geometry_path)
        
        aoi_list = [aoi(geom_path = site, 
                        min_year = min_year,
                        max_year = max_year
                        ) for site in json_files]
        
        for site in aoi_list:
            output_site_dir = os.path.join(output_dir, site.site_name)    
            
                        
            order_name = const_order_name(prefix, site.site_name, site.min_year, site.max_year) 
            print("\n\n###########################################################")
            print("   SUMMARY FOR ORDER: {}".format(order_name))
            print("###########################################################")
            
            if not os.path.exists(output_site_dir):
                try:
                    print("NOTE: Site directory '{}' does not exist.  Creating directory.".format(output_site_dir))
                    os.makedirs(output_site_dir)
                except OSError as exc: # Guard against race condition
                    if exc.errno != errno.EEXIST:
                        raise
            
            order_list = check( order_name_search=order_name+ "*", 
                   order_date_search=order_date_search)
            
            if order_list == None:
                print("No succesful orders to download.")
                continue
            
            site_output_dir = os.path.join(output_site_dir, order_name)
            
            summary = get_data(order_list, site_output_dir)
    
            print_download_summary(summary, output_site_dir)
    else:
         
        print("\n\n###########################################################")
        print("   SUMMARY OF ORDERS")
        print("###########################################################")
        
        order_list = check( order_name_search=order_name_search, 
               order_date_search=order_date_search)
        
        if order_list == None:
            print("No succesful orders to download.")
        
        summary = get_data(order_list, output_dir)

        print_download_summary(summary, output_dir)
        

            
            



if __name__ == "__main__":
    
    import argparse
    parser = argparse.ArgumentParser()

    subparser = parser.add_subparsers(dest="command", required=True)
    
    parser_search = subparser.add_parser('search', help='Search for items available.')
    
    parser_search.add_argument("-min_c", "--min_cloud", help="Minimum Cloud Cover in Percent.", type=float,  default=0.0)
    parser_search.add_argument("-max_c", "--max_cloud", help="Maximum Cloud Cover in Percent.", type=float,  default=0.50)
    parser_search.add_argument("-p", "--permission", help="Show results for items you account allows to download.", default=True, action=argparse.BooleanOptionalAction)
    parser_search.add_argument("min_year", help="Starting year of interest, YYYY format", type=int)
    parser_search.add_argument("max_year", help="Ending year of interest, YYYY format", type=int)
    parser_search.add_argument("geojson_files", help="Path to directory containing GeoJSON Files representing Area of Interest", type=str)

    
    subparser_order = subparser.add_parser("order", help='Place the order.')

    subparser_order.add_argument("-min_c", "--min_cloud", help="Minimum Cloud Cover in Percent.", type=float,  default=0.00)
    subparser_order.add_argument("-max_c", "--max_cloud", help="Maximum Cloud Cover in Percent.", type=float,  default=0.50)
    subparser_order.add_argument("-item", "--api_item_type", help="Planet item types to order.", type=str, default="PSScene")
    subparser_order.add_argument("-bundle", "--api_product_bundle", help="Planet bundle names used for placing orders.", type=str, default="analytic_udm2")
    subparser_order.add_argument("-prefix", "--order_name_prefix", help="Add a prefix to the order name in order, to make it unique.", type=str)
    subparser_order.add_argument("min_year", help="Starting year of interest, YYYY format", type=int)
    subparser_order.add_argument("max_year", help="Ending year of interest, YYYY format", type=int)
    subparser_order.add_argument("geojson_files", help="Path to directory containing GeoJSON Files representing Area of Interest", type=str)

    subparser_check = subparser.add_parser("check", help='Check orders.')
    subparser_check.add_argument("-gjson", "--geojson_files", help="Path to directory containing GeoJSON Files representing Area of Interest", type=str, default=None)
    subparser_check.add_argument("-min_y","--min_year", help="Starting year of interest, YYYY format", type=int, default=None)
    subparser_check.add_argument("-max_y", "--max_year", help="Ending year of interest, YYYY format", type=int, default=None)
    subparser_check.add_argument("-oname", "--order_name", help="Filter results by order name. Use '*' as wildcard, e.g. Boston* or *2016_2017* ", type=str, default=None)
    subparser_check.add_argument("-odate", "--order_date", help="Filter results by order date, format YYYY-MM-DD.", type=str, default=None)
    subparser_check.add_argument("-prefix", "--order_name_prefix", help="Add a prefix to the order name in order, to make it unique.", type=str)
    
    
    subparser_download = subparser.add_parser("download", help='Check orders.')
    subparser_download.add_argument("-gjson", "--geojson_files", help="Path to directory containing GeoJSON Files representing Area of Interest", type=str, default=None)
    subparser_download.add_argument("-min_y","--min_year", help="Starting year of interest, YYYY format", type=int, default=None)
    subparser_download.add_argument("-max_y", "--max_year", help="Ending year of interest, YYYY format", type=int, default=None)
    subparser_download.add_argument("-oname", "--order_name", help="Filter results by order name. Use '*' as wildcard, e.g. Boston* or *2016_2017* ", type=str, default=None)
    subparser_download.add_argument("-odate", "--order_date", help="Filter results by order date, format YYYY-MM-DD.", type=str, default=None)
    subparser_download.add_argument("output_dir", help="Directory where images are saved.", type=str)
    subparser_download.add_argument("-prefix", "--order_name_prefix", help="Add a prefix to the order name in order, to make it unique.", type=str)
    

    args = parser.parse_args()
    
    if args.command == "search":
        
        search(geometry_path = args.geojson_files,
             min_year = args.min_year,
             max_year = args.max_year,
             min_cloud = args.min_cloud,
             max_cloud = args.max_cloud,
             allowed = args.permission
             )
        
        
        print("\n\nNEXT STEP:\n ")
        print("1.) Using the link below, find the appropriate 'bundle(s)' that contain the 'item type' and 'assets' of interest to you."+ \
                  "\nhttps://developers.planet.com/apis/orders/product-bundles-reference/")
            
        print("\n2.) Run the following command with appropriate substitutions.")
        print("{} order -bundle <bundle_name> -item <item_name> min_year max_year path_to_geojson".format(os.path.basename(__file__)))
        print("\nEXAMPLE:")
        print("python {} order -bundle analytic_udm2 -item PSScene {} {} {}".format(os.path.basename(__file__), args.min_year, args.max_year, args.geojson_files))
          

    elif args.command == "order":
        
        order(geometry_path = args.geojson_files,
              min_year = args.min_year,
              max_year = args.max_year,
              min_cloud = args.min_cloud,
              max_cloud = args.max_cloud,
              api_item_type = args.api_item_type,
              product_bundle = args.api_product_bundle,
              prefix = args.order_name_prefix
              )
        
        prefix_flag =  "-prefix "+ args.order_name_prefix  if args.order_name_prefix != None else ""
        
        print("To check on order, use the command below:\n")
        arg_min_year = "-min_y {} ".format(args.min_year) if args.min_year != None else ""
        arg_max_year = "-max_y {} ".format(args.max_year) if args.max_year != None else ""
        arg_gjson = "-gjson {} ".format(args.geojson_files) if args.geojson_files != None else ""
        arg_prefix = "-prefix {} ".format(args.order_name_prefix) if args.order_name_prefix != None else ""
        
        print("python {} check {}{}{}{}".format(os.path.basename(__file__),arg_prefix, arg_min_year, arg_max_year, arg_gjson))
        
        
        
        
    elif args.command == "check":
        
        if(args.geojson_files != None and (args.min_year == None or args.max_year == None)):
            raise Exception("When using -gjson, --geojson_files flag, you need to also specify -min_y, --min_year and -max_y, --max_year.")
            
            
        check(order_url=orders_url, 
               order_name_search=args.order_name, 
               order_date_search=args.order_date,
               min_year = args.min_year,
               max_year = args.max_year,
               geometry_path = args.geojson_files,
               prefix = args.order_name_prefix)
        
        
        print("\n\nUse the following download command to download the files for successful orders listed above:")
    
        arg_name = "-name {} ".format(args.order_name) if args.order_name != None else ""
        arg_date = "-date {} ".format(args.order_date) if args.order_date != None else ""
        arg_min_year = "-min_y {} ".format(args.min_year) if args.min_year != None else ""
        arg_max_year = "-max_y {} ".format(args.max_year) if args.max_year != None else ""
        arg_gjson = "-gjson {} ".format(args.geojson_files) if args.geojson_files != None else ""
        arg_prefix = "-prefix {} ".format(args.order_name_prefix) if args.order_name_prefix != None else ""
        
        print("python {} download {}{}{}{}{}{} <YOUR OUTPUT PATH>".format(os.path.basename(__file__), arg_name, arg_date, arg_min_year, arg_max_year, arg_prefix, arg_gjson))
        
    elif args.command == "download":
        
        if(args.geojson_files != None and (args.min_year == None or args.max_year == None)):
            raise Exception("When using -gjson, --geojson_files flag, you need to also specify -min_y, --min_year and -max_y, --max_year.")
            
            
        download(order_url=orders_url, 
               order_name_search=args.order_name, 
               order_date_search=args.order_date,
               min_year = args.min_year,
               max_year = args.max_year,
               geometry_path = args.geojson_files,
               output_dir = args.output_dir,
               prefix = args.order_name_prefix)
        
        
        arg_name = "-name {} ".format(args.order_name) if args.order_name != None else ""
        arg_date = "-date {} ".format(args.order_date) if args.order_date != None else ""
        arg_min_year = "-min_y {} ".format(args.min_year) if args.min_year != None else ""
        arg_max_year = "-max_y {} ".format(args.max_year) if args.max_year != None else ""
        arg_gjson = "-gjson {} ".format(args.geojson_files) if args.geojson_files != None else ""
        arg_prefix = "-prefix {} ".format(args.order_name_prefix) if args.order_name_prefix != None else ""
        arg_output = "{} ".format(args.output_dir) if args.output_dir != None else ""
        
        print("\nNOTE: To try downloading again, run the command below:")
        print("python {} download {}{}{}{}{}{} {}".format(os.path.basename(__file__), arg_name, arg_date, arg_min_year, arg_max_year, arg_prefix, arg_gjson, arg_output))
        
        
    else:
        raise NotImplementedError(
            f"Command {args.command} does not exist.",
        )
        

    

    
    

   
