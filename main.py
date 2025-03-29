import pickle

from housing_target_scraper.scraper import TargetHousingScraper

# This will run the asynchronous main function and handle the event loop
if __name__ == "__main__":
    scraper = TargetHousingScraper()
    url = scraper.set_search_url(
        # zipcodes=[1099],
        location_queries="Amsterdam"
        # housing_type=["Apartment", "Home"], 
        # min_price=10,
        # max_price=1200,
        # min_size=1,
        # max_size=100,
        # extra_criteria=["more 1 year"]
    )
    results = scraper.scrape()
    results = TargetHousingScraper.to_dataframe(results)
    print(results)

    with open("data.pkl", "wb") as file:
        pickle.dump(results, file)


