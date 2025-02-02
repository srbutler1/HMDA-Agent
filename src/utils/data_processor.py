import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from .hmda_api import HMDAApi

# Configure logging
logging.basicConfig(
    filename='hmda_processing.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DataProcessor:
    """Handler for HMDA data processing, validation, and analysis"""
    
    # HMDA data field requirements
    REQUIRED_FIELDS = {
        'application_date': str,
        'loan_type': int,
        'loan_purpose': int,
        'loan_amount': float,
        'action_taken': int,
        'state': str,
        'county': str,
        'census_tract': str,
        'ethnicity': str,
        'race': str,
        'sex': str,
        'income': float,
        'purchaser_type': int,
        'hoepa_status': int,
        'lien_status': int,
        'number_of_units': int
    }
    
    def __init__(self):
        self.hmda_api = HMDAApi()
        self.census_data = self._load_census_data()
        self.error_counts = {
            'missing_fields': 0,
            'invalid_types': 0,
            'validation_errors': 0
        }
        
    def _load_census_data(self) -> pd.DataFrame:
        """Load census data from flat file"""
        try:
            census_file = Path("data/CensusFlatFile2024.csv")
            data = pd.read_csv(census_file)
            logging.info(f"Successfully loaded census data with {len(data)} records")
            return data
        except Exception as e:
            logging.error(f"Error loading census data: {e}")
            return pd.DataFrame()

    def validate_hmda_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
        """
        Validate HMDA data fields and return cleaned data with error report
        
        Args:
            data: DataFrame containing HMDA data
            
        Returns:
            Tuple containing:
            - Cleaned DataFrame
            - Dictionary with validation errors
        """
        errors = {
            'missing_required_fields': [],
            'invalid_data_types': [],
            'validation_errors': []
        }
        
        # Reset error counts
        self.error_counts = {k: 0 for k in self.error_counts}
        
        # Check for required fields
        missing_fields = set(self.REQUIRED_FIELDS.keys()) - set(data.columns)
        if missing_fields:
            error_msg = f"Missing required fields: {missing_fields}"
            logging.error(error_msg)
            errors['missing_required_fields'].append(error_msg)
            self.error_counts['missing_fields'] += len(missing_fields)
        
        # Create a copy for cleaning
        cleaned_data = data.copy()
        
        # Validate data types and values
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field in cleaned_data.columns:
                try:
                    # Convert to expected type
                    cleaned_data[field] = cleaned_data[field].astype(expected_type)
                    
                    # Validate specific fields
                    if field == 'loan_amount':
                        invalid_amounts = cleaned_data[field] <= 0
                        if invalid_amounts.any():
                            error_msg = f"Invalid loan amounts found: {sum(invalid_amounts)} records"
                            errors['validation_errors'].append(error_msg)
                            self.error_counts['validation_errors'] += sum(invalid_amounts)
                    
                    elif field == 'action_taken':
                        invalid_actions = ~cleaned_data[field].isin(range(1, 9))
                        if invalid_actions.any():
                            error_msg = f"Invalid action taken codes found: {sum(invalid_actions)} records"
                            errors['validation_errors'].append(error_msg)
                            self.error_counts['validation_errors'] += sum(invalid_actions)
                    
                except Exception as e:
                    error_msg = f"Error converting {field} to {expected_type}: {str(e)}"
                    logging.error(error_msg)
                    errors['invalid_data_types'].append(error_msg)
                    self.error_counts['invalid_types'] += 1
        
        # Log validation results
        logging.info(f"Data validation completed with {sum(self.error_counts.values())} total errors")
        for error_type, count in self.error_counts.items():
            if count > 0:
                logging.warning(f"{error_type}: {count} errors")
        
        return cleaned_data, errors

    def is_hmda_reportable(self, loan_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if a loan is HMDA reportable
        
        Args:
            loan_data: Dictionary containing loan information
            
        Returns:
            Tuple containing:
            - Boolean indicating if loan is reportable
            - String explaining the determination
        """
        # Check if loan is secured by a dwelling
        if not loan_data.get('secured_by_dwelling', False):
            return False, "Loan not secured by a dwelling"
            
        # Check if loan amount meets minimum threshold
        if loan_data.get('loan_amount', 0) < 500:
            return False, "Loan amount below $500 threshold"
            
        # Check for excluded transactions
        if loan_data.get('temporary_financing', False):
            return False, "Temporary financing excluded"
            
        if loan_data.get('agricultural_purpose', False):
            return False, "Agricultural purpose excluded"
            
        # Check business purpose loans
        if loan_data.get('business_purpose', False):
            if loan_data.get('loan_purpose') not in ['home_purchase', 'home_improvement', 'refinancing']:
                return False, "Business purpose loan not for home purchase, improvement, or refinancing"
        
        return True, "Loan is HMDA reportable"

    def analyze_loan_qualification(
        self,
        state: str,
        city: str,
        income: float,
        credit_score: int,
        property_type: str,
        property_value: float
    ) -> Dict:
        """
        Analyze loan qualification based on user inputs and historical data.
        
        Args:
            state: Two-letter state code
            city: City name
            income: Annual income
            credit_score: Credit score
            property_type: Type of property
            property_value: Estimated property value
            
        Returns:
            Dictionary containing qualification analysis
        """
        # Get recent loan data for the state
        loan_data = self.hmda_api.get_loan_data(2024, state)
        
        if loan_data.empty:
            return {
                "error": "Unable to fetch loan data for analysis"
            }
            
        # Calculate key metrics
        dti_ratio = self._calculate_dti_ratio(income, property_value)
        ltv_ratio = self._calculate_ltv_ratio(property_value, property_value * 0.8)  # Assuming 20% down
        
        # Get local market statistics
        local_stats = self._get_local_statistics(loan_data, city)
        
        # Determine loan type recommendations
        recommendations = self._get_loan_recommendations(
            dti_ratio,
            ltv_ratio,
            credit_score,
            income,
            property_value,
            local_stats
        )
        
        return {
            "metrics": {
                "dti_ratio": dti_ratio,
                "ltv_ratio": ltv_ratio,
                "local_median_loan": local_stats["median_loan_amount"],
                "local_median_income": local_stats["median_income"]
            },
            "recommendations": recommendations
        }

    def _calculate_dti_ratio(
        self,
        income: float,
        property_value: float,
        interest_rate: float = 0.07,
        term_years: int = 30
    ) -> float:
        """Calculate debt-to-income ratio"""
        # Simplified monthly payment calculation
        loan_amount = property_value * 0.8  # Assuming 20% down
        r = interest_rate / 12
        n = term_years * 12
        monthly_payment = loan_amount * (r * (1 + r)**n) / ((1 + r)**n - 1)
        
        # Add estimated taxes and insurance (1.5% of property value annually)
        monthly_payment += (property_value * 0.015) / 12
        
        return (monthly_payment * 12) / income

    def _calculate_ltv_ratio(
        self,
        property_value: float,
        loan_amount: float
    ) -> float:
        """Calculate loan-to-value ratio"""
        return loan_amount / property_value

    def _get_local_statistics(
        self,
        loan_data: pd.DataFrame,
        city: str
    ) -> Dict:
        """Get statistics for the local market"""
        # Filter for the city if possible
        city_data = loan_data[loan_data["derived_msa-md"].notna()]
        
        return {
            "median_loan_amount": city_data["loan_amount"].median(),
            "median_income": city_data["income"].median(),
            "approval_rate": (city_data["action_taken"] == 1).mean()
        }

    def _get_loan_recommendations(
        self,
        dti_ratio: float,
        ltv_ratio: float,
        credit_score: int,
        income: float,
        property_value: float,
        local_stats: Dict
    ) -> List[Dict]:
        """Generate loan type recommendations"""
        recommendations = []
        
        # Conventional loan
        if credit_score >= 620 and dti_ratio <= 0.43 and ltv_ratio <= 0.95:
            recommendations.append({
                "type": "Conventional",
                "likelihood": "High",
                "requirements": [
                    "Credit score 620+",
                    "DTI ratio <= 43%",
                    "Down payment 5-20%"
                ]
            })
            
        # FHA loan
        if credit_score >= 580 and dti_ratio <= 0.50:
            recommendations.append({
                "type": "FHA",
                "likelihood": "Medium" if credit_score < 620 else "High",
                "requirements": [
                    "Credit score 580+",
                    "DTI ratio <= 50%",
                    "Down payment 3.5%"
                ]
            })
            
        # VA loan (would need to verify eligibility)
        recommendations.append({
            "type": "VA",
            "likelihood": "Unknown",
            "requirements": [
                "Military service requirement",
                "No down payment required",
                "No minimum credit score"
            ]
        })
        
        return recommendations

    def analyze_demographic_trends(
        self,
        state: str,
        year_range: List[int]
    ) -> pd.DataFrame:
        """Analyze demographic trends in lending"""
        trends = []
        
        for year in year_range:
            data = self.hmda_api.get_loan_data(year, state)
            if not data.empty:
                summary = {
                    "year": year,
                    "total_applications": len(data),
                    "approval_rate": (data["action_taken"] == 1).mean(),
                    "median_loan": data["loan_amount"].median(),
                    "median_income": data["income"].median()
                }
                
                # Add demographic breakdowns
                for demo in ["race", "ethnicity", "sex"]:
                    col = f"derived_{demo}"
                    if col in data.columns:
                        grouped = data.groupby(col)["action_taken"].agg(
                            ["count", lambda x: (x == 1).mean()]
                        )
                        for group, stats in grouped.iterrows():
                            summary[f"{demo}_{group}_share"] = stats["count"] / len(data)
                            summary[f"{demo}_{group}_approval"] = stats["<lambda>"]
                
                trends.append(summary)
        
        return pd.DataFrame(trends)

    def perform_quality_control(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform quality control checks on HMDA data
        
        Args:
            data: DataFrame containing HMDA data
            
        Returns:
            Dictionary containing QC results and flags
        """
        qc_results = {
            'total_records': len(data),
            'flags': [],
            'statistics': {},
            'recommendations': []
        }
        
        # Check for outliers in key numeric fields
        numeric_fields = ['loan_amount', 'income', 'rate_spread']
        for field in numeric_fields:
            if field in data.columns:
                stats = data[field].describe()
                outliers = data[data[field] > stats['75%'] + 1.5 * (stats['75%'] - stats['25%'])]
                if len(outliers) > 0:
                    qc_results['flags'].append({
                        'type': 'outlier',
                        'field': field,
                        'count': len(outliers),
                        'threshold': stats['75%'] + 1.5 * (stats['75%'] - stats['25%'])
                    })
        
        # Check for unusual patterns
        qc_results['statistics'] = {
            'denial_rate': (data['action_taken'] == 3).mean(),
            'withdrawal_rate': (data['action_taken'] == 4).mean(),
            'incomplete_rate': (data['action_taken'] == 5).mean()
        }
        
        # Flag high denial/withdrawal rates
        if qc_results['statistics']['denial_rate'] > 0.4:
            qc_results['flags'].append({
                'type': 'high_denial_rate',
                'value': qc_results['statistics']['denial_rate']
            })
        
        if qc_results['statistics']['withdrawal_rate'] > 0.2:
            qc_results['flags'].append({
                'type': 'high_withdrawal_rate',
                'value': qc_results['statistics']['withdrawal_rate']
            })
        
        # Check for missing rate spread on higher-priced loans
        if 'rate_spread' in data.columns and 'loan_amount' in data.columns:
            high_amount_missing_rate = data[
                (data['loan_amount'] > data['loan_amount'].quantile(0.9)) & 
                (data['rate_spread'].isna())
            ]
            if len(high_amount_missing_rate) > 0:
                qc_results['flags'].append({
                    'type': 'missing_rate_spread',
                    'count': len(high_amount_missing_rate)
                })
        
        # Generate recommendations based on findings
        if qc_results['flags']:
            qc_results['recommendations'].append(
                "Review flagged records for data accuracy and completeness"
            )
            if any(f['type'] == 'outlier' for f in qc_results['flags']):
                qc_results['recommendations'].append(
                    "Implement additional validation rules for outlier values"
                )
        
        # Log QC results
        logging.info(f"Quality control completed with {len(qc_results['flags'])} flags")
        for flag in qc_results['flags']:
            logging.warning(f"QC Flag: {flag}")
        
        return qc_results

    def prepare_hmda_lar(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Prepare HMDA Loan Application Register (LAR) for submission
        
        Args:
            data: DataFrame containing HMDA data
            
        Returns:
            Tuple containing:
            - Formatted LAR DataFrame
            - Dictionary with preparation summary
        """
        summary = {
            'total_records': len(data),
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            # Validate data first
            cleaned_data, validation_errors = self.validate_hmda_data(data)
            if validation_errors['missing_required_fields'] or validation_errors['invalid_data_types']:
                summary['errors'].extend(validation_errors['missing_required_fields'])
                summary['errors'].extend(validation_errors['invalid_data_types'])
                logging.error("Critical errors found during LAR preparation")
                return data, summary
            
            # Format fields according to HMDA requirements
            lar_data = cleaned_data.copy()
            
            # Format numeric fields
            if 'loan_amount' in lar_data.columns:
                lar_data['loan_amount'] = lar_data['loan_amount'].round().astype(int)
            
            if 'income' in lar_data.columns:
                lar_data['income'] = lar_data['income'].round().astype(int)
            
            # Format date fields
            if 'application_date' in lar_data.columns:
                lar_data['application_date'] = pd.to_datetime(lar_data['application_date']).dt.strftime('%Y%m%d')
            
            # Calculate statistics
            summary['statistics'] = {
                'total_originated': len(lar_data[lar_data['action_taken'] == 1]),
                'total_denied': len(lar_data[lar_data['action_taken'] == 3]),
                'total_withdrawn': len(lar_data[lar_data['action_taken'] == 4]),
                'median_loan_amount': lar_data['loan_amount'].median() if 'loan_amount' in lar_data.columns else None,
                'median_income': lar_data['income'].median() if 'income' in lar_data.columns else None
            }
            
            # Perform quality control
            qc_results = self.perform_quality_control(lar_data)
            if qc_results['flags']:
                summary['warnings'].extend([f"QC Flag: {flag}" for flag in qc_results['flags']])
            
            logging.info(f"LAR preparation completed for {len(lar_data)} records")
            return lar_data, summary
            
        except Exception as e:
            error_msg = f"Error preparing LAR: {str(e)}"
            logging.error(error_msg)
            summary['errors'].append(error_msg)
            return data, summary
