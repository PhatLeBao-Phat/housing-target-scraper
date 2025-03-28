import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Tuple, List, Optional, Deque
import re
from collections import deque

from housing_target_scraper.housing import Listing
from housing_target_scraper.logger import logger as logging
from housing_target_scraper.helper import ParallelOfficer


# class Website:
#     """Base class for website interactions, providing interface for searching listings."""

#     def __init__(self, url: str):
#         self.url = url

#     def get_listing(self):
#         raise NotImplementedError("Method is not implemented")


class HousingTargetWebsite():
    """Class for HousingTarget website interaction."""
    ROOT_URL = "https://www.housingtarget.com"


    def __init__(self, url: str, headless: bool = True):
        """Initialize HousingTargetWebsite with URL and headless browser option."""
        super().__init__(url)
        if self.ROOT_URL not in self.url:
            raise ValueError(f"Supplemented URL {self.url} is not supported by {self.__class__.__name__}")
        self.driver = self._initialize_chrome_driver(headless)
        self.headless = headless
        self.session = requests.Session()


    def __del__(self):
        """Ensure the browser driver quits on object deletion."""
        self.driver.quit()
    

    @staticmethod
    def _initialize_chrome_driver(headless: bool = True) -> webdriver.Chrome:
        """Configure and return a Chrome WebDriver instance."""
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if headless:
            chrome_options.add_argument("--headless=new")

        return webdriver.Chrome(options=chrome_options)


    @staticmethod
    def fetch_listing_details(url: str, session : requests.Session) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Extract title, street, description, and SEO text from a listing page url."""
        try:
            page = session.get(url, timeout=10)
            page.raise_for_status()
        except requests.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
            return None, None, None, None

        # Parse HTML content
        soup = BeautifulSoup(page.content, "html.parser")
        html = soup.find("div", class_="top-info-mobile")
        title = html.findChild("h1").get_text(strip=True) if html and html.findChild("h1") else None
        street = html.findChild("strong").get_text(strip=True) if html and html.findChild("strong") else None
        description = soup.find("div", class_="desc").get_text(strip=True) if soup.find("div", class_="desc") else None
        seo = soup.find("div", class_="seo").get_text(strip=True) if soup.find("div", class_="seo") else None

        return title, street, description, seo


    @staticmethod
    def extract_property_details_from_string(listing: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract size, property type, and location from listing string."""
        size = re.search(r"(\d+\s*(?:m²|m2))", listing, re.IGNORECASE)
        property_type = re.search(r"\b(apartment|house|room|studio|flat)\b", listing, re.IGNORECASE)
        location = re.search(r"(?<=\bin\s)(.*)", listing)

        return (
            size.group(1) if size else None, 
            property_type.group(1) if property_type else None, 
            location.group(1).strip() if location else None
        )
    

    def parse_listing_element(self, listing_element: str) -> Listing:
        """Parse HTML list element into a Listing object.
        
        :param listing_element: <li> tag bs4.HTML element representing an item in a list
        :return: Listing object
        """
        bs4_html = BeautifulSoup(listing_element.get_attribute("outerHTML"), "html.parser")
        link = bs4_html.find("a")["href"] # TODO: add following link
        title, street, description, seo = self.fetch_listing_details(self.ROOT_URL + link, self.session)
        rent = bs4_html.find("label").parent.find("span").get_text(strip=True)
        size, property_type, location = self.extract_property_details_from_string(bs4_html.find("a").get_text(strip=True))

        return Listing(
            link=link,
            rent=rent,
            size=size,
            property_type=property_type,
            location=location,
            title=title,
            street=street,
            description=description,
            seo=seo,
        )


    def scrape_listings(self, visited_urls: set, return_listings: List[Listing], max_pages: int = 20) -> List[Listing]:
        """
        Recursively fetch listings from paginated website URLs with detailed logging.
        
        :param url:
        :param visited_urls:
        :param all_listings:
        :param max_pages:

        :return: List of listing object. Each object contains properties details. 
        
        """
        if not isinstance(visited_urls, set):
            raise TypeError(f"Expecting visited_urls of type set not {type(visited_urls)}")
        if not isinstance(return_listings, list):
            raise TypeError(f"Expecting return_listings of type list not type {type(return_listings)}")
        
        # FIFO loop
        q = deque([self.url])
        while q and len(visited_urls) < max_pages:
            url = q.popleft() 

            self._visit_url(url, visited_urls)
            
            listings = self._parse_listings_from_page()
            if listings:
                return_listings.extend(listings)

            pagination_links = self._get_pagination_links()
            
            for link in pagination_links:
                if not self._should_skip(link, visited_urls, max_pages, q):
                    q.append(link)

        return return_listings


    def _should_skip(self, url: str, visited_urls: set, max_pages: int, q : Deque) -> bool:
        """Checks if a URL should be skipped."""
        if url in visited_urls or len(visited_urls) >= max_pages or url in q:
            return True
        return False


    def _visit_url(self, url: str, visited_urls: set):
        """Visits the URL and adds it to visited URLs."""
        logging.info(f"Visiting {url}")
        visited_urls.add(url)
        self.driver.get(url)


    def _parse_listings_from_page(self) -> List[Listing]:
        """Parses listings from the current page."""
        try:
            WebDriverWait(self.driver, 1).until(EC.presence_of_element_located((By.CLASS_NAME, "table-ads")))

            ul_element = self.driver.find_element(By.CLASS_NAME, "table-ads")
            li_elements = ul_element.find_elements(By.TAG_NAME, "li")
            listings = [li for li in li_elements if li.get_attribute("class") == "" and li.find_elements(By.TAG_NAME, "div")]

            logging.info(f"Found {len(listings)} listings on the page")

            # Parallel threadings 
            po = ParallelOfficer()
            return po.process_parallel_list(listings, self.parse_listing_element)    

        except Exception as e:
            logging.warning(f"Error parsing listings: {e}")
            return []


    def _get_pagination_links(self) -> List[str]:
        """Extracts pagination links from the current page that has not been visited."""
        try:
            pagination_html = BeautifulSoup(self.driver.find_element(By.CLASS_NAME, "pager").get_attribute("outerHTML"), "html.parser")
            pagination_links = [self.ROOT_URL + e["href"] for e in pagination_html.find_all("a")]
            logging.info(f"Found {len(pagination_links)} pagination links")
            return pagination_links
        except Exception as e:
            logging.warning(f"Error retrieving pagination links: {e}")
            return []