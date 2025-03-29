from housing_target_scraper.listing import Listing
from housing_target_scraper.logger import logger
from housing_target_scraper.utils.config_utils import config

from typing import Optional, List
import requests
from urllib.parse import urlparse, parse_qs, urlunparse
from concurrent.futures import ThreadPoolExecutor
import itertools
import asyncio
import httpx
import pickle 

from bs4 import BeautifulSoup, element
from diot import Diot


class Website:
    """Responsible for website-related data and web content parsing."""
    def __init__(self):
        pass 

    def parse_content(self):
        pass

    def get_link(self):
        """This is optional, let me think about it."""
        pass 


class SearchWebsite:
    """Responsible for search website and parse url to listing cites."""
    ROOT_URL = "https://www.housingtarget.com"

    def __init__(
        self, 
        search_url : str, 
        requests_session: Optional[requests.Session] = None

    ):
        if requests_session is not None and not isinstance(requests_session, requests.Session):
            raise ValueError(f"Invalid requests.Session object passed: {requests_session}")

        self.requests_session = requests_session or requests.Session()  # Or for fallback value
        self.search_url = search_url if self.is_search_url_valid(search_url) else None


    @staticmethod
    def get_html(requests_session : requests.Session, search_url : str) -> BeautifulSoup:
        """Send GET to server with corresponding search url. Return bs4 object."""
        try:
            page = requests_session.get(search_url, timeout=10)
            page.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Error fetching {search_url}: {e}")

        return BeautifulSoup(page.text, features="lxml")


    @staticmethod
    def set_paginated_url(url : str, page_num : str) -> str:
        """Add the page_num to the search_url."""
        parsed_url = urlparse(url)

        return urlunparse(parsed_url._replace(path=parsed_url.path + "/pageindex" + str(page_num)))

    def parse_individual_paginated_url(self, paginated_url) -> List[str]:
        """Parse individual paginated url and return a list of url to individual listing."""
        soup = self.get_html(self.requests_session, paginated_url)

        result = [
            self.ROOT_URL + e.find_next().get("href") 
            for e in soup.find_all("div", {"class" : "text-data"})
        ]
        logger.info(f"Parsed {len(result)} links from {paginated_url}")

        return result


    def get_listing_link(self) -> List[str]:
        """Fetch all urls to individual listing site."""
        soup = self.get_html(self.requests_session, self.search_url)

        max_page = max([
            int(e.text)
            for e in soup.find("div", {"class": "pager"}).children
            if e != "\n" and e.text.isdigit()
        ])
        pagination_urls = (
            self.set_paginated_url(self.search_url, page_num)
            for page_num in range(max_page + 1)
        )

        with ThreadPoolExecutor() as executor:
            result = list(
                executor.map(self.parse_individual_paginated_url, pagination_urls)
            )

        # Flatten list and get unique set 
        result = set(itertools.chain(*result))

        return result 


    def is_search_url_valid(
        self, 
        search_url,
        valid_query_keys : List[str] = ['estate_types', 'area_to', 'max_rent', 'ex_rper'],
    ) -> bool:

        parsed_url = urlparse(search_url)
        query_params = parse_qs(parsed_url.query)

        root_url = parsed_url.scheme + "://" + parsed_url.netloc
        if root_url != self.ROOT_URL: 
            logger.error(f"Invalid root url: {root_url}")
            return False

        invalid_query_keys = [key for key in query_params if key not in valid_query_keys]
        if invalid_query_keys: 
            logger.error(f"Invalid query keys in the url: {', '.join(invalid_query_keys)}")
            return False

        return True
    

class ListingWebsite:
    def __init__(
        self, 
        url : str, 
        client : httpx.AsyncClient,
        css_selector : Diot, 
    ) -> None:
        self.url = url
        self.css_selector = css_selector
        self.client = client 
    

    @staticmethod
    def clean_text(text : str) -> str:
        """Clean Unicode text parsed from individual websites."""
        return text.strip().replace("\xa0", " ")
    

    @staticmethod
    def parse_desc_element(desc_element : element.Tag) -> dict:
        """Parse the desc, zipcode, and area info from description text."""
        desc_list = [e for e in desc_element.contents if e.name != "br" and e != "\n"]
        try: 
            zipcode = desc_list[-1].strip().split(":")[1]
            area = desc_list[-2].strip().split(":")[1]
        except (ValueError, IndexError) as e:
            zipcode, area = None, None
            
        desc = "".join(desc_list)

        return (
            {"zipcode" : zipcode},
            {"area" : area},
            {"desc" : desc},
        )
        

    async def parse_info(self) -> List[Listing]:
        logger.info(f"Fetching info from listing url: {self.url}")
        try:
            response = await self.client.get(self.url, timeout=10)
        except httpx.RequestError as e:
            return self.url, f"Error: {e}"
        
        soup = BeautifulSoup(response.text, features="lxml")
        fact_list = soup.select(self.css_selector.fact_list)
        results = {
            li_element.contents[1].text.strip(): li_element.contents[3].text.strip()
            for li_element in fact_list
            if not li_element.get("class").__contains__("no-value")
        }

        # Get description, zipcode, and area
        desc_element = soup.select(self.css_selector.desc)[0]
        zipcode_dict, area_dict, desc_dict = self.parse_desc_element(desc_element)
        results = {**results, **zipcode_dict, **area_dict, **desc_dict}

        return results
            
            
class TargetHousingScraper:
    """Entry APIs to search listings info on housingtarget.com"""
    def __init__(self, search_link : Optional[str] = None):
        """
        :param search_link: the url link from search page
        """
        self.search_link = search_link
        self.css_selector = config.css_selector
    

    # ----------------------------------------------------------------- Business methods -----------------------------------------------------------------
    def search(**kwargs) -> List[Listing]:
        """Searches for listings listings based on given params."""
        pass 


    async def scrape(self, max_connections=10) -> List[dict]:
        """Scrape all listings based on the given search url."""
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
                        error_occurred = True
                        raise e
                    
            if error_occurred:
                logger.error("Aborting due to previous error.")
                return [] 

            tasks = [bound_fetch(url) for url in searchable_urls]
            results = await asyncio.gather(*tasks)
            logger.info(f"Finished Phase 2: Success scraped {len(results)} listings")
            
            # Filter out None results in case of errors
            return [result for result in results if result is not None]
        


async def main():
    # Your search URL here
    search_url = "https://www.housingtarget.com/netherlands/housing-rentals/amsterdam?estate_types=2;3;9"

    # Create the scraper object
    scraper = TargetHousingScraper(search_url)
    
    # Run the scrape method to get the results
    results = await scraper.scrape(max_connections=10)

    return results 

# This will run the asynchronous main function and handle the event loop
if __name__ == "__main__":
    results = asyncio.run(main())
    with open("data.pkl", "wb") as file:
        pickle.dump(results, file)


