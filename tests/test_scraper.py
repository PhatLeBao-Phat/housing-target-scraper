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
                {"price_per_month": "   682.96\xa0EUR ", "housing_type": "House"},
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


    @pytest.mark.parametrize(
        "listing_dict, size_colname, new_size_colname, measurement_colname, expected",
        [
            # Case 1: if size is not specified then return None 
            (
                {"size" : "Not specified", "housing_type" : "House"},
                "size",
                "size",
                "size_measurement", 
                {"size" : None, "housing_type" : "House"}
            ),
            # Case 2: size col is not presented
            (
                {"size_lala" : "30 m2", "housing_type" : "House"},
                "size",
                "size",
                "size_measurement", 
                {"size_lala" : "30 m2", "housing_type" : "House"}
            ),
            # Case 3: Rename size col to something else 
            (
                {"size" : "30 m2", "housing_type" : "House"},
                "size",
                "new_size",
                "size_measurement", 
                {"size" : "30 m2", "new_size" : 30.0, "size_measurement" : "m2", "housing_type" : "House"}
            )
        ]
    )
    def test_clean_size_col(
        self, listing_dict, size_colname, new_size_colname, measurement_colname, expected
    ):
        """
        Test the `clean_size_col` function.
        """
        cleaned_dict = TargetHousingScraper.clean_size_col(
            listing_dict, size_colname, new_size_colname, measurement_colname
        )

        assert cleaned_dict == expected