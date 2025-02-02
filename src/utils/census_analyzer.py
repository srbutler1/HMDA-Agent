import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path

class CensusAnalyzer:
    """Analyzes census data in relation to HMDA lending patterns"""
    
    def __init__(self):
        self.current_census_data = self._load_census_data()
        self.historical_census_data = pd.DataFrame()  # Will be populated as needed
        
    def _load_census_data(self) -> pd.DataFrame:
        """Load current census data from flat file"""
        try:
            census_file = Path("data/CensusFlatFile2024.csv")
            return pd.read_csv(census_file)
        except Exception as e:
            print(f"Error loading census data: {e}")
            return pd.DataFrame()
            
    def load_historical_census_data(
        self,
        year: int,
        api_client  # FFIEC API client instance
    ) -> None:
        """
        Load historical census data from FFIEC API for time series analysis
        Only available from 2018 onwards
        
        Args:
            year: Year to load data for (2018 or later)
            api_client: FFIEC API client instance
        """
        if year < 2018:
            raise ValueError("Historical census data only available from 2018 onwards")
            
        try:
            # Load historical data through API client
            historical_data = api_client.get_census_data(year)
            self.historical_census_data = pd.concat([
                self.historical_census_data,
                historical_data
            ])
        except Exception as e:
            print(f"Error loading historical census data for {year}: {e}")

    def get_tract_demographics(
        self,
        tract_id: str,
        year: Optional[int] = None
    ) -> Dict:
        """
        Get demographic information for a census tract based on FFIEC data
        
        Args:
            tract_id: Census tract identifier
            
        Returns:
            Dictionary containing tract demographic information
        """
        # Use historical data if year is specified and data exists
        if year and not self.historical_census_data.empty:
            census_data = self.historical_census_data[
                (self.historical_census_data["census_tract"] == tract_id) &
                (self.historical_census_data["year"] == year)
            ]
            if census_data.empty:
                return {}
            tract_data = census_data.iloc[0]
        # Otherwise use current flat file data
        else:
            if self.current_census_data.empty:
                return {}
            tract_data = self.current_census_data[
                self.current_census_data["census_tract"] == tract_id
            ].iloc[0]
        
        # Calculate FFIEC tract income level
        tract_mfi_percent = tract_data["tract_to_msa_income_percentage"]
        income_level = self._get_ffiec_income_level(tract_mfi_percent)
        
        return {
            "population": tract_data["tract_population"],
            "minority_population_percent": tract_data["tract_minority_population_percent"],
            "median_family_income": tract_data["ffiec_msa_md_median_family_income"],
            "tract_to_msa_income_percent": tract_mfi_percent,
            "tract_income_level": income_level,
            "below_poverty_line_percent": tract_data["tract_below_poverty_line_percent"],
            "owner_occupied_units": tract_data["tract_owner_occupied_units"],
            "one_to_four_family_homes": tract_data["tract_one_to_four_family_homes"],
            "median_home_age": tract_data["tract_median_age_of_housing_units"],
            "total_housing_units": tract_data["tract_total_housing_units"],
            "vacant_units": tract_data["tract_vacant_units"],
            "renter_occupied_units": tract_data["tract_renter_occupied_units"],
            "inside_principal_city": tract_data["tract_inside_principal_city"]
        }

    def _get_ffiec_income_level(self, tract_mfi_percent: float) -> str:
        """
        Determine FFIEC income level classification based on tract to MSA/MD income percentage
        
        Args:
            tract_mfi_percent: Tract to MSA/MD median family income percentage
            
        Returns:
            FFIEC income level classification
        """
        if tract_mfi_percent == 0:
            return "Not Known"
        elif tract_mfi_percent < 50:
            return "Low"
        elif tract_mfi_percent < 80:
            return "Moderate"
        elif tract_mfi_percent < 120:
            return "Middle"
        else:
            return "Upper"

    def analyze_income_levels(
        self,
        hmda_data: pd.DataFrame,
        msa_code: Optional[str] = None
    ) -> Dict:
        """
        Analyze income levels in relation to area median income
        
        Args:
            hmda_data: HMDA loan application data
            msa_code: Optional MSA code to filter by
            
        Returns:
            Dictionary containing income level analysis
        """
        if self.census_data.empty:
            return {}
            
        if msa_code:
            hmda_data = hmda_data[hmda_data["derived_msa-md"] == msa_code]
            census_subset = self.census_data[
                self.census_data["derived_msa-md"] == msa_code
            ]
        else:
            census_subset = self.census_data
            
        # Calculate area median income
        area_median_income = census_subset["ffiec_msa_md_median_family_income"].median()
        
        # Categorize applications by income level
        hmda_data["income_level"] = hmda_data["income"].apply(
            lambda x: self._categorize_income(x, area_median_income)
        )
        
        # Calculate approval rates by income level
        approval_by_income = hmda_data.groupby("income_level").agg({
            "action_taken": lambda x: (x == 1).mean()
        }).to_dict()["action_taken"]
        
        return {
            "area_median_income": area_median_income,
            "approval_rates_by_income_level": approval_by_income
        }

    def _categorize_income(
        self,
        income: float,
        area_median_income: float
    ) -> str:
        """Categorize income relative to area median income"""
        if income <= area_median_income * 0.5:
            return "Very Low"
        elif income <= area_median_income * 0.8:
            return "Low"
        elif income <= area_median_income * 1.2:
            return "Moderate"
        else:
            return "High"

    def analyze_neighborhood_characteristics(
        self,
        hmda_data: pd.DataFrame,
        msa_code: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict:
        """
        Analyze lending patterns by FFIEC neighborhood characteristics
        
        Args:
            hmda_data: HMDA loan application data
            msa_code: Optional MSA code to filter by
            
        Returns:
            Dictionary containing neighborhood analysis
        """
        # Determine which census dataset to use
        if year and not self.historical_census_data.empty:
            census_data = self.historical_census_data[
                self.historical_census_data["year"] == year
            ]
            if census_data.empty:
                return {}
        else:
            if self.current_census_data.empty:
                return {}
            census_data = self.current_census_data
            
        if msa_code:
            hmda_data = hmda_data[hmda_data["derived_msa-md"] == msa_code]
            census_subset = census_data[
                census_data["derived_msa-md"] == msa_code
            ]
        else:
            census_subset = census_data
            
        # Merge HMDA and census data
        merged_data = pd.merge(
            hmda_data,
            census_subset,
            on="census_tract",
            how="left"
        )
        
        # Calculate FFIEC income levels
        merged_data['tract_income_level'] = merged_data['tract_to_msa_income_percentage'].apply(
            self._get_ffiec_income_level
        )
        
        # Analyze by minority population percentage
        minority_bins = [0, 20, 40, 60, 80, 100]
        minority_labels = ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']
        
        merged_data['minority_bracket'] = pd.cut(
            merged_data['tract_minority_population_percent'],
            bins=minority_bins,
            labels=minority_labels
        )
        
        minority_analysis = merged_data.groupby('minority_bracket').agg({
            'action_taken': lambda x: (x == 1).mean(),
            'loan_amount': 'median',
            'property_value': 'median',
            'income': 'median'
        }).to_dict(orient='index')
        
        # Analyze by FFIEC tract income level
        income_analysis = merged_data.groupby('tract_income_level').agg({
            'action_taken': lambda x: (x == 1).mean(),
            'loan_amount': 'median',
            'property_value': 'median',
            'income': 'median',
            'debt_to_income_ratio': 'median'
        }).to_dict(orient='index')
        
        # Analyze by housing characteristics
        housing_analysis = {
            'owner_occupied_rate': (
                merged_data['tract_owner_occupied_units'] / 
                merged_data['tract_total_housing_units']
            ).mean(),
            'vacancy_rate': (
                merged_data['tract_vacant_units'] / 
                merged_data['tract_total_housing_units']
            ).mean(),
            'median_home_age': merged_data['tract_median_age_of_housing_units'].median(),
            'single_family_home_pct': (
                merged_data['tract_one_to_four_family_homes'] / 
                merged_data['tract_total_housing_units']
            ).mean()
        }
        
        return {
            "minority_population_analysis": minority_analysis,
            "tract_income_analysis": income_analysis,
            "housing_market_indicators": housing_analysis
        }

    def get_market_assessment(
        self,
        tract_id: str,
        loan_amount: float
    ) -> Dict:
        """
        Assess market conditions for a specific census tract
        
        Args:
            tract_id: Census tract identifier
            loan_amount: Proposed loan amount
            
        Returns:
            Dictionary containing market assessment
        """
        if self.census_data.empty:
            return {}
            
        tract_data = self.census_data[
            self.census_data["census_tract"] == tract_id
        ].iloc[0]
        
        # Calculate affordability metrics
        median_income = tract_data["ffiec_msa_md_median_family_income"]
        monthly_payment = self._calculate_monthly_payment(loan_amount)
        affordability_ratio = (monthly_payment * 12) / median_income
        
        return {
            "median_family_income": median_income,
            "affordability_ratio": affordability_ratio,
            "owner_occupied_percent": (
                tract_data["tract_owner_occupied_units"] /
                tract_data["tract_one_to_four_family_homes"]
            ),
            "median_home_age": tract_data["tract_median_age_of_housing_units"]
        }

    def _calculate_monthly_payment(
        self,
        loan_amount: float,
        interest_rate: float = 0.07,
        term_years: int = 30
    ) -> float:
        """Calculate estimated monthly mortgage payment"""
        r = interest_rate / 12
        n = term_years * 12
        return loan_amount * (r * (1 + r)**n) / ((1 + r)**n - 1)
