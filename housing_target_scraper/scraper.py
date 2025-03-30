from typing import List, Optional, Generator, Union, Literal
import asyncio
import httpx 
import re

import pandas as pd
from urllib.parse import urlencode, urlparse, urlunparse
import pgeocode

from housing_target_scraper.utils.config_utils import config
from housing_target_scraper.website import SearchWebsite, ListingWebsite
from housing_target_scraper.logger import logger


class TargetHousingScraper:
    """Entry APIs to search listings info on housingtarget.com"""
    ROOT_QUERY_URL = "https://www.housingtarget.com/netherlands/housing-rentals"

    HOUSING_TYPE_DICT = {
        "Apartment" : "2",
        "House" : "3",
        "Room" : "9",
        "Home" : "20",
    }

    EXTRA_SEARCH_CRITERIA = {
        "less 1 year" : "1",
        "more 1 year" : "2",
        "unlimited" : "3",
    }

    def __init__(self, search_link : Optional[str] = None):
        """
        :param search_link: the url link from search page
        """
        self.search_link = search_link
        self.css_selector = config.css_selector
    

    # ----------------------------------------------------------------- Business methods -----------------------------------------------------------------
    @staticmethod
    def clean_column(colname : str) -> str:
        """Clean to column name to snake_case.
        :example:
            >>> clean_column("La la    la")
            la_la_la
        """
        text = re.sub(r"[^a-zA-Z0-9\s]", "", colname)   # Remove special characters
        text = re.sub(r"\s+", "_", text)                # Replace spaces with "_"
        return text.lower()                             # Convert to lowercase
    
    
    @staticmethod
    def to_dataframe(
        scraped_data : Generator[dict, None, None], 
        raw_data : bool = False
    ) -> pd.DataFrame:
        """Parse the returned set to pd.DataFrame format."""
        df = pd.DataFrame(scraped_data)
        if not raw_data:
            cleaned_cols = [TargetHousingScraper.clean_column(col) for col in df.columns]
            df.columns = cleaned_cols

        return df 
    

    @staticmethod
    def clean_price_col(
        listing_dict : dict[str, str], 
        price_colname : str = "price_per_month",
        new_price_colname : str = "price_per_month",
        currency_colname : str = "price_currency", 
    ) -> dict[str, str]:
        """Clean and process str price data to price[float] and currency[e.g. EUR]."""
        if not price_colname in listing_dict.keys():
            return listing_dict
        price_per_month = listing_dict.get(price_colname)
        copy_dict = listing_dict.copy()
        if price_per_month == "Not specified":
            copy_dict[price_colname] = None
        else:
            price, currency = price_per_month.strip().split(" ")
            copy_dict[new_price_colname] = float(price)
            copy_dict[currency_colname] = currency

        return copy_dict 


    @staticmethod
    def clean_size_col(
        listing_dict : dict[str, str],
        size_colname : str = "size", 
        new_size_colname : str = "size", 
        measurement_colname : str = "size_measurement", 
    ) -> dict[str, str]:
        """Clean and process str size data to size[int] and measurement unit[e.g. m2]"""
        if not size_colname in listing_dict.keys():
            return listing_dict
        size = listing_dict.get(size_colname)
        copy_dict = listing_dict.copy()
        if size == "Not specified":
            copy_dict["size"] = None 
        else:
            size, unit = size.strip().split(" ")
            copy_dict[new_size_colname] = int(size)
            copy_dict[measurement_colname] = unit
        
        return copy_dict


    @staticmethod
    def query_zipcode(
        location_queries : Union[str, List[str]],
        country_code : str = "nl",
    ) -> None:
        """Get a list of zipcode and search locations name from a location_query search."""
        nomi = pgeocode.Nominatim(country_code)
        if isinstance(location_queries, str): location_queries = [location_queries]
        df = pd.concat([nomi.query_location(q) for q in location_queries])

        return (
            list(set(df["postal_code"].astype(int))), 
            list(set(df.place_name))
        )

    def set_search_url(
        self, 
        zipcodes : Optional[Union[str, List[int]]] = None,
        location_queries : Optional[Union[str, List[int]]] = None,
        housing_type : Literal["Apartment", "House", "Room", "Home"] = None,
        min_price : int = None,
        max_price : int = None, 
        min_size : int = None, 
        max_size : int = None, 
        extra_criteria : List[Literal["less 1 year", "more 1 year", "unlimited"]] = None,
        exchange_home : bool = None, 
    ) -> str:
        """Searches for listings listings based on given params.
        
        :param zipcodes: zipcodes of areas to search.
        :param location_query: location to query for zipcodes. Cannot be used along with `zipcodes`.
        :param housing_type: the type of estates to search.
        :param min_price: min rental in EUR of estate to search. The minimum search price is 0 EUR.
        :param max_price: max rental in EUR of estate to search. The default price is 20000+ EUR. 
        :param min_size: min size in m2 of estate to search. The search size is at least 0.
        :param max_size: max size in m2 of estate to search The default search size is 500+ m2.

        :return: url reprents the searchable link on housingtarget.com.
        """
        # Check if available location_queries or zipcodes
        if location_queries and zipcodes:
            raise ValueError("Can only use `location_queries` or `zipcodes` params for search")
        elif location_queries:
            zipcodes, names = self.query_zipcode(location_queries)
            logger.info(f"Query by location name found the following locations: {', '.join(names)}")
            
        # Build query params for search url
        query_params = {}
        if isinstance(zipcodes, int): zipcodes = [zipcodes]
        query_params.update({"zip_codes" : ";".join([str(zipcode) for zipcode in zipcodes])})
        
        if exchange_home:
            query_params.update({"excl_swap" : 1})
        
        if extra_criteria:
            if isinstance(extra_criteria, str):
                extra_criteria = [extra_criteria]
            
            included_criteria = [self.EXTRA_SEARCH_CRITERIA[option] for option in extra_criteria]
            excluded_criteria = [num for num in ["1", "2", "3"] if num not in included_criteria]
            query_params.update({"ex_rper" : ";".join(excluded_criteria)})

        if isinstance(max_price, int):
            if max_price > 20000: pass 
            elif max_price <= 0: raise ValueError("Input value for max_price must be int and at least 1 EUR")
            else: query_params.update({"max_rent" : max_price})
        elif max_price: raise ValueError(f"Input value for max_price must be int: {max_price}")
        
        if isinstance(min_price, int) and min_price > 0: query_params.update({"min_rent" : min_price})
        elif min_price: raise ValueError(f"Input value for min_price must be int and more than 0: {min_price}")

        if isinstance(min_size, int) and min_size > 0: query_params.update({"area_from" : min_size})
        elif min_size: raise ValueError(f"Input value for min_size must be int and more than 0: {min_size}")
        
        if isinstance(max_size, int) and max_size < 500: 
            if max_size > 500: pass 
            elif max_size <= 0: raise ValueError(f"Input value for max_size must be at least 1 m2: {max_size}")
            else: query_params.update({"area_to" : max_size})
        elif max_size: raise ValueError(f"Input value for max_price must be int: {max_size}")

        if housing_type:
            if isinstance(housing_type, str): housing_type = [housing_type]
            included_housing_type = [self.HOUSING_TYPE_DICT[option] for option in housing_type]
            query_params.update({"estate_types" : ";".join(included_housing_type)})
        
        # Construct search url
        query_string = urlencode(query_params)
        parsed_url = urlparse(self.ROOT_QUERY_URL)
        full_url = urlunparse(parsed_url._replace(query=query_string))

        self.search_link = full_url
        
        return full_url


    def scrape(self, max_connections=10) -> Generator[dict, None, None]:
        """Wrapper to run the async scrape method synchronously."""
        logger.info(f"Start scraping url {self.search_link:.150}...")
        return asyncio.run(self._async_scrape(max_connections))


    async def _async_scrape(self, max_connections=10) -> List[dict]:
        """Async scrape all listings based on the given search url."""
        logger.info("Phase 1: Scrape all individual listings url.")
        search_website = SearchWebsite(self.search_link)
        searchable_urls = search_website.get_listing_link()
        logger.info(f"Finished Phase 1: got {len(searchable_urls)} urls")

        logger.info("Phase 2: Scrape individual url")
        # Shared flag to track if an error happens
        error_occurred = False
        async with httpx.AsyncClient() as client:
            sem = asyncio.Semaphore(max_connections)  # Limit concurrency

            async def bound_fetch(url):
                nonlocal error_occurred
                async with sem:
                    try:
                        return await ListingWebsite(url, client, self.css_selector).parse_info()
                    except httpx.RequestError as e:
                        logger.error(f"Request error while fetching {url}: {e}")
                        error_occurred = True
                        return None  # or handle however you'd like
                    except Exception as e:
                        logger.error(f"Unexpected error while processing {url}: {e}")
                        raise e
                    
            if error_occurred:
                logger.error("Aborting due to previous error.")
                return [] 

            tasks = [bound_fetch(url) for url in searchable_urls]
            results = await asyncio.gather(*tasks)
            logger.info(f"Finished Phase 2: Success scraped {len(results)} listings")
            
            # Filter out None results in case of errors
            return (result for result in results if result is not None)
    