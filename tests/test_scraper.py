import pytest
from housing_target_scraper.scraper import TargetHousingScraper


class TestClean:
    @pytest.mark.parametrize(
        "listing_dict, price_colname, new_price_colname, currency_colname, expected",
        [
            # Case 1: Price is "Not specified" -> Should be converted to None
            (
                {"price_per_month": "Not specified", "housing_type": "House"},
                "price_per_month",
                "price_per_month",
                "price_currency",
                {"price_per_month": None, "housing_type": "House"},
            ),
            # Case 2: Price with currency -> Should extract price as float and currency separately
            (
                {"price_per_month": "682.96 EUR", "housing_type": "House"},
                "price_per_month",
                "price_per_month",
                "price_currency",
                {
                    "price_per_month": 682.96,
                    "housing_type": "House",
                    "price_currency": "EUR",
                },
            ),
            # Case 3: Incorrect column name -> Should return the original dictionary unchanged
            (
                {"price_per_month": "682.96 EUR", "housing_type": "House"},
                "price_per_mola",  # Incorrect column name
                "price_per_month",
                "price_currency",
                {"price_per_month": "682.96 EUR", "housing_type": "House"},
            ),
            # Case 4: Rename column while extracting price and currency
            (
                {"price_per_month": "682.96 EUR", "housing_type": "House"},
                "price_per_month",
                "new_price_per_month",
                "price_currency",
                {
                    "price_per_month": "682.96 EUR",
                    "new_price_per_month": 682.96,
                    "housing_type": "House",
                    "price_currency": "EUR",
                },
            ),
        ],
    )
    def test_clean_price_col(self, listing_dict, price_colname, new_price_colname, currency_colname, expected):
        """
        Test the clean_price_col function to ensure it correctly parses and cleans price-related fields.
        """
        cleaned_dict = TargetHousingScraper.clean_price_col(
            listing_dict, price_colname, new_price_colname, currency_colname
        )
        assert cleaned_dict == expected
