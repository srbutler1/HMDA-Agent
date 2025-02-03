import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from .data_processor import DataProcessor

class LoanAnalyzer:
    """Analyzes HMDA loan data for patterns and recommendations"""
    
    def __init__(self):
        self.data_processor = DataProcessor()
        self.census_data = self._load_census_data()
        self.msa_data = self._load_msa_data()
        self.loan_type_map = {
            1: "Conventional",
            2: "FHA",
            3: "VA",
            4: "USDA/FSA"
        }
        
        self.denial_reason_map = {
            1: "Debt-to-income ratio",
            2: "Employment history",
            3: "Credit history",
            4: "Collateral",
            5: "Insufficient cash",
            6: "Unverifiable information",
            7: "Credit application incomplete",
            8: "Mortgage insurance denied",
            9: "Other"
        }

    def _load_census_data(self) -> pd.DataFrame:
        """Load census data from flat file"""
        try:
            census_file = Path("data/CensusFlatFile2024.csv")
            return pd.read_csv(census_file)
        except Exception as e:
            print(f"Error loading census data: {e}")
            return pd.DataFrame()

    def _load_msa_data(self) -> Dict[str, str]:
        """Load MSA data from file and create city-state to MSA code mapping"""
        try:
            with open('msa07inc.htm', 'r') as f:
                content = f.read()
                
            # Extract MSA data from the HTML table
            msa_mapping = {}
            
            # Split into lines and process each line
            lines = content.split('\n')
            for line in lines:
                if '<td class=xl25>' in line and '</td>' in line:
                    # Extract city-state text
                    city_state = line.split('<td class=xl25>')[1].split('</td>')[0].strip()
                    
                    # Get the corresponding MSA code from previous line
                    prev_line = lines[lines.index(line) - 1]
                    if 'x:num>' in prev_line:
                        msa_code = prev_line.split('x:num>')[1].split('</td>')[0].strip()
                        
                        if city_state and msa_code and not city_state.startswith('nonmetro'):
                            # Split into city and state
                            if ',' in city_state:
                                city, state = city_state.rsplit(',', 1)
                                city = city.strip()
                                state = state.strip()
                                
                                # Create normalized key for lookup
                                key = f"{city.upper()}, {state}"
                                msa_mapping[key] = msa_code
            
            return msa_mapping
        except Exception as e:
            print(f"Error loading MSA data: {e}")
            return {}

    def _get_msa_code(self, city: str, state: str) -> Optional[str]:
        """Get MSA code for given city and state"""
        # Normalize the city name and create lookup key
        city = city.strip().upper()
        state = state.strip().upper()
        
        # Try exact match first
        key = f"{city}, {state}"
        if key in self.msa_data:
            return self.msa_data[key]
            
        # Try partial matches
        for msa_key, code in self.msa_data.items():
            if state in msa_key and any(
                city in part.strip() 
                for part in msa_key.split('-')
            ):
                return code
                
        return None

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

    def validate_and_clean_data(
        self,
        data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
        """
        Validate and clean HMDA data before analysis
        
        Args:
            data: Raw HMDA data
            
        Returns:
            Tuple containing:
            - Cleaned DataFrame
            - Dictionary with validation errors
        """
        return self.data_processor.validate_hmda_data(data)

    def analyze_approval_patterns(
        self,
        data: pd.DataFrame,
        msa_code: Optional[str] = None
    ) -> Dict:
        """
        Analyze approval patterns by various factors
        
        Args:
            data: HMDA loan application data
            msa_code: Optional MSA code to filter by
            
        Returns:
            Dictionary containing approval pattern analysis
        """
        if msa_code:
            data = data[data["derived_msa-md"] == msa_code]
            
        # Overall approval rate
        approval_rate = (data["action_taken"] == 1).mean()
        
        # Approval rates by loan type
        loan_type_approvals = data.groupby("loan_type").agg({
            "action_taken": lambda x: (x == 1).mean()
        }).to_dict()["action_taken"]
        
        loan_type_approvals = {
            self.loan_type_map[k]: v 
            for k, v in loan_type_approvals.items()
        }
        
        # Income level analysis
        income_bins = [0, 50000, 100000, 150000, float('inf')]
        income_labels = ['<50k', '50k-100k', '100k-150k', '>150k']
        
        data['income_bracket'] = pd.cut(
            data['income'].astype(float),
            bins=income_bins,
            labels=income_labels
        )
        
        income_approvals = data.groupby('income_bracket').agg({
            'action_taken': lambda x: (x == 1).mean()
        }).to_dict()['action_taken']
        
        return {
            "overall_approval_rate": approval_rate,
            "loan_type_approval_rates": loan_type_approvals,
            "income_bracket_approval_rates": income_approvals
        }

    def analyze_denial_patterns(
        self,
        data: pd.DataFrame,
        msa_code: Optional[str] = None
    ) -> Dict:
        """
        Analyze patterns in loan denials
        
        Args:
            data: HMDA loan application data
            msa_code: Optional MSA code to filter by
            
        Returns:
            Dictionary containing denial pattern analysis
        """
        if msa_code:
            data = data[data["derived_msa-md"] == msa_code]
            
        # Get denial reasons (columns denial_reason-1 through denial_reason-4)
        denial_cols = [col for col in data.columns if col.startswith("denial_reason")]
        denied_apps = data[data["action_taken"] == 3]
        
        # Aggregate denial reasons
        all_reasons = []
        for col in denial_cols:
            reasons = denied_apps[col].dropna()
            all_reasons.extend(reasons)
            
        reason_counts = pd.Series(all_reasons).value_counts()
        
        # Map reason codes to descriptions
        reason_dist = {
            self.denial_reason_map[k]: v 
            for k, v in reason_counts.items() 
            if k in self.denial_reason_map
        }
        
        return {
            "denial_rate": (data["action_taken"] == 3).mean(),
            "reason_distribution": reason_dist
        }

    def get_qualification_factors(
        self,
        data: pd.DataFrame,
        loan_amount: float,
        income: float,
        property_type: str,
        city: str,
        state: str
    ) -> Dict:
        """
        Analyze qualification factors based on similar applications
        
        Args:
            data: HMDA loan application data
            loan_amount: Requested loan amount
            income: Annual income
            property_type: Type of property
            city: City name
            state: State code
            
        Returns:
            Dictionary containing qualification analysis
        """
        # Get MSA code for the city/state
        msa_code = self._get_msa_code(city, state)
        if msa_code:
            data = data[data["derived_msa-md"] == msa_code]
            
        # Filter for similar loan amounts (±20%)
        amount_lower = loan_amount * 0.8
        amount_upper = loan_amount * 1.2
        similar_amounts = data[
            (data["loan_amount"] >= amount_lower) & 
            (data["loan_amount"] <= amount_upper)
        ]
        
        # Filter for similar income (±20%)
        income_lower = income * 0.8
        income_upper = income * 1.2
        similar_income = similar_amounts[
            (similar_amounts["income"] >= income_lower) &
            (similar_amounts["income"] <= income_upper)
        ]
        
        # Filter for property type
        similar_props = similar_income[
            similar_income["derived_dwelling_category"].str.contains(
                property_type,
                case=False,
                na=False
            )
        ]
        
        # Calculate approval likelihood
        approval_rate = (similar_props["action_taken"] == 1).mean()
        
        # Get typical DTI ratios for approved loans
        approved_loans = similar_props[similar_props["action_taken"] == 1]
        typical_dti = approved_loans["debt_to_income_ratio"].median()
        
        return {
            "similar_applications_count": len(similar_props),
            "approval_rate": approval_rate,
            "typical_dti_ratio": typical_dti,
            "median_loan_amount": similar_props["loan_amount"].median(),
            "median_income": similar_props["income"].median(),
            "msa_code": msa_code
        }

    def analyze_market_trends(
        self,
        data: pd.DataFrame,
        msa_code: Optional[str] = None
    ) -> Dict:
        """
        Analyze market trends in the area
        
        Args:
            data: HMDA loan application data
            msa_code: Optional MSA code to filter by
            
        Returns:
            Dictionary containing market trend analysis
        """
        if msa_code:
            data = data[data["derived_msa-md"] == msa_code]
            
        # Loan type distribution
        loan_type_dist = data["loan_type"].map(self.loan_type_map).value_counts()
        
        # Property type distribution
        property_dist = data["derived_dwelling_category"].value_counts()
        
        # Loan purpose distribution
        purpose_dist = data["loan_purpose"].value_counts()
        
        # Calculate median values
        medians = {
            "median_loan_amount": data["loan_amount"].median(),
            "median_income": data["income"].median(),
            "median_property_value": data["property_value"].median(),
            "median_ltv": data["combined_loan_to_value_ratio"].median()
        }
        
        return {
            "loan_type_distribution": loan_type_dist.to_dict(),
            "property_type_distribution": property_dist.to_dict(),
            "loan_purpose_distribution": purpose_dist.to_dict(),
            "median_values": medians
        }

    def get_demographic_analysis(
        self,
        data: pd.DataFrame,
        msa_code: Optional[str] = None
    ) -> Dict:
        """
        Analyze lending patterns by demographic factors
        
        Args:
            data: HMDA loan application data
            msa_code: Optional MSA code to filter by
            
        Returns:
            Dictionary containing demographic analysis
        """
        if msa_code:
            data = data[data["derived_msa-md"] == msa_code]
            
        demographics = {}
        
        # Analyze by race
        race_approvals = data.groupby("derived_race").agg({
            "action_taken": lambda x: (x == 1).mean(),
            "loan_amount": "median",
            "income": "median"
        }).to_dict(orient="index")
        
        # Analyze by ethnicity
        ethnicity_approvals = data.groupby("derived_ethnicity").agg({
            "action_taken": lambda x: (x == 1).mean(),
            "loan_amount": "median",
            "income": "median"
        }).to_dict(orient="index")
        
        # Analyze by sex
        sex_approvals = data.groupby("derived_sex").agg({
            "action_taken": lambda x: (x == 1).mean(),
            "loan_amount": "median",
            "income": "median"
        }).to_dict(orient="index")
        
        demographics["race"] = race_approvals
        demographics["ethnicity"] = ethnicity_approvals
        demographics["sex"] = sex_approvals
        
        return demographics
