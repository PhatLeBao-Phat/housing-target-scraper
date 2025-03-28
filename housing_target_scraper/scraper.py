from typing import Literal, List 
from housing_target_scraper.website import HousingTargetWebsite


class Scraper: 
    """Responsible for scraping and store scraped data"""

    def __init__(
        self, 
        mode : Literal["parallel", "linear"] = "parallel", 
        websites : List = []
    ):
        self.mode = mode 
        self.websites = websites    

    def run(self):
        """Run the scraper on websites"""
        r = [] 
        for w in self.websites:
            listings = w.scrape_listings()
            r.append(listings)
        
        return r