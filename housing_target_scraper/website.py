import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, urlunparse
from concurrent.futures import ThreadPoolExecutor
import itertools
import httpx

from bs4 import BeautifulSoup, element
from diot import Diot

from housing_target_scraper.listing import Listing
from housing_target_scraper.logger import logger


SEARCH_PARAMS = ['estate_types', 'area_to', 'max_rent', 'ex_rper', "area_from", "min_rent", "zip_codes"]
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
            return BeautifulSoup(page.text, features="lxml")
        except requests.RequestException as e:
            logger.error(f"Error fetching {search_url}: {e}")




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
        logger.info(f"Parsed {len(result)} links from {paginated_url:.150}...")

        return result


    def get_listing_link(self) -> List[str]:
        """Fetch all urls to individual listing site."""
        soup = self.get_html(self.requests_session, self.search_url)
        # Find the last page available
        try:
            page_elements = soup.find("div", {"class": "pager"}).children
            max_page = max([
                int(e.text)
                for e in page_elements
                if e != "\n" and e.text.isdigit()
            ])
        except AttributeError as e:
            logger.error(f"Find pagination element error: {e}")
            max_page = 1

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
        valid_query_keys : List[str] = SEARCH_PARAMS,
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
        desc_list = [e for e in desc_element.contents if e.name != "br" and e != "\n" and type(e) == str]
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
        """Parse information from the given url."""
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
        results = {**results, **zipcode_dict, **area_dict, **desc_dict, "url" : self.url}

        return results
            