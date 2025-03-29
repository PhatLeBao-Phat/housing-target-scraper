"""Parsing configuration used for scraping."""

from pathlib import Path 
from yaml import SafeLoader, load 

from diot import Diot

import housing_target_scraper


PACKAGE_ROOT = Path(housing_target_scraper.__file__).resolve().parent
CONFIG_PATH = PACKAGE_ROOT / "config\\config.yaml"

with open(CONFIG_PATH) as f:
    config_data = load(f, Loader=SafeLoader)

config = Diot(config_data)
