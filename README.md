![Python](https://img.shields.io/badge/Python-3.x-blue)
![Concurrent](https://img.shields.io/badge/Concurrency-Supported-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Active-success)
![Build](https://img.shields.io/badge/Build-Passing-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Cross--Platform-lightgrey)
![Code Style](https://img.shields.io/badge/Code%20Style-PEP%208-blue)
![Tests](https://img.shields.io/badge/Tests-Covered-green)
![Issues](https://img.shields.io/github/issues/your-username/housing-target-scraper)
![Pull Requests](https://img.shields.io/github/issues-pr/your-username/housing-target-scraper)
![Last Commit](https://img.shields.io/github/last-commit/your-username/housing-target-scraper)
![Contributions](https://img.shields.io/badge/Contributions-Welcome-orange)
![Stars](https://img.shields.io/github/stars/your-username/housing-target-scraper?style=social)
![Forks](https://img.shields.io/github/forks/your-username/housing-target-scraper?style=social)

# Housing Target Scraper

This project is a web scraper designed to collect housing data from various online sources. The goal is to automate the process of gathering information about housing listings, such as prices, locations, and other relevant details.

## Features

- Scrapes housing data from multiple websites.
- Extracts key details like price, location, and property type.
- Saves data in a structured format (e.g., CSV, JSON).
- Configurable scraping parameters.

## Requirements

- Python 3.x
- Required libraries (see `requirements.txt`)

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/your-username/housing-target-scraper.git
    cd housing-target-scraper
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage
Here is a good example:
```python 
import pickle

from housing_target_scraper.scraper import TargetHousingScraper

# This will run the asynchronous main function and handle the event loop
if __name__ == "__main__":
    scraper = TargetHousingScraper()
    url = scraper.set_search_url(
        # zipcodes=[1099],
        location_queries="Amsterdam"
        housing_type=["Apartment", "Home"], 
        min_price=10,
        max_price=1200,
        min_size=1,
        max_size=100,
        extra_criteria=["more 1 year"]
    )
    results = scraper.scrape()
    results = TargetHousingScraper.to_dataframe(results)
    print(results)

    with open("data.pkl", "wb") as file:
        pickle.dump(results, file)

```
Please find more details example in `main.py`.
## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix:
    ```bash
    git checkout -b feature-name
    ```
3. Commit your changes:
    ```bash
    git commit -m "Add feature-name"
    ```
4. Push to your branch:
    ```bash
    git push origin feature-name
    ```
5. Open a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contact

For questions or feedback, please open an issue or reach out via GitHub.