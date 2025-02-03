import streamlit as st
import pandas as pd
from pathlib import Path
from utils.hmda_api import HMDAApi
from utils.loan_analyzer import LoanAnalyzer
from utils.census_analyzer import CensusAnalyzer

# Initialize our components
hmda_api = HMDAApi()
loan_analyzer = LoanAnalyzer()
census_analyzer = CensusAnalyzer()

# Configure the Streamlit page
st.set_page_config(
    page_title="HMDA Multi-Agent System",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("HMDA Multi-Agent System")
    st.sidebar.title("Navigation")

    # Navigation
    page = st.sidebar.radio(
        "Select Interface",
        ["Customer Loan Qualification", "Research Analysis"]
    )

    if page == "Customer Loan Qualification":
        customer_interface()
    else:
        researcher_interface()

def customer_interface():
    # Initialize session state for form inputs
    if 'form_submitted' not in st.session_state:
        st.session_state.form_submitted = False
    
    st.header("Loan Qualification Assistant")
    st.write("""
    This tool helps you understand what types of loans you may qualify for based on:
    - Your location and regional data
    - Income and financial information
    - Property details
    - Local lending patterns
    """)

    col1, col2 = st.columns(2)

    with col1:
        # Location Information
        st.subheader("Location Information")
        # All US states
        states = [
            "Select State", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            "DC"  # Including District of Columbia
        ]
        
        # Use session state to store form values
        if 'state' not in st.session_state:
            st.session_state.state = "Select State"
        if 'city' not in st.session_state:
            st.session_state.city = ""
        if 'annual_income' not in st.session_state:
            st.session_state.annual_income = 0
        if 'credit_score' not in st.session_state:
            st.session_state.credit_score = 650
        if 'monthly_debt' not in st.session_state:
            st.session_state.monthly_debt = 0
        if 'property_type' not in st.session_state:
            st.session_state.property_type = "Single Family"
        if 'property_value' not in st.session_state:
            st.session_state.property_value = 0
        if 'down_payment' not in st.session_state:
            st.session_state.down_payment = 0
        if 'loan_purpose' not in st.session_state:
            st.session_state.loan_purpose = "Home Purchase"
            
        def update_state(key, value):
            st.session_state[key] = value
            st.session_state.form_submitted = False
            
        state = st.selectbox("State", states, key="state_select", 
                           on_change=update_state, args=("state",))
        if state != "Select State":
            city = st.text_input("City", key="city_input",
                               on_change=update_state, args=("city",))
            
        # Financial Information
        st.subheader("Financial Information")
        annual_income = st.number_input("Annual Income ($)", min_value=0, value=st.session_state.annual_income, 
                                      step=1000, on_change=update_state, args=("annual_income",))
        credit_score = st.slider("Credit Score", 300, 850, st.session_state.credit_score,
                               on_change=update_state, args=("credit_score",))
        monthly_debt = st.number_input("Monthly Debt Payments ($)", min_value=0, 
                                     value=st.session_state.monthly_debt, step=100,
                                     on_change=update_state, args=("monthly_debt",))

    with col2:
        # Property Information
        st.subheader("Property Information")
        property_type = st.selectbox(
            "Property Type",
            ["Single Family", "Multi-Family", "Manufactured Home"],
            key="property_type_select",
            on_change=update_state, args=("property_type",)
        )
        property_value = st.number_input("Estimated Property Value ($)", min_value=0, 
                                       value=st.session_state.property_value, step=1000,
                                       on_change=update_state, args=("property_value",))
        down_payment = st.number_input("Down Payment ($)", min_value=0, 
                                     value=st.session_state.down_payment, step=1000,
                                     on_change=update_state, args=("down_payment",))
        
        # Loan Information
        st.subheader("Loan Information")
        loan_purpose = st.selectbox(
            "Loan Purpose",
            ["Home Purchase", "Refinancing", "Home Improvement"],
            key="loan_purpose_select",
            on_change=update_state, args=("loan_purpose",)
        )
    
    if st.button("Analyze Qualification"):
        st.session_state.form_submitted = True
        
    if st.session_state.form_submitted:
        if state != "Select State" and city and annual_income > 0 and property_value > 0:
            analyze_qualification(
                state, city, annual_income, credit_score, monthly_debt,
                property_type, property_value, down_payment, loan_purpose
            )
        else:
            st.warning("Please fill in all required fields")

def researcher_interface():
    st.header("HMDA Data Analysis")
    st.write("""
    Research tools for analyzing HMDA data:
    - Regional lending patterns
    - Demographic analysis
    - Time series trends
    - Fair lending analysis
    - Data quality control
    """)

    # Analysis Configuration
    col1, col2 = st.columns(2)
    
    with col1:
        # Data Selection
        st.subheader("Data Selection")
        year = st.selectbox("Select Year", range(2023, 2017, -1))
        # All US states for research interface
        states = [
            "All States", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
            "DC"  # Including District of Columbia
        ]
        state = st.selectbox("Select State", states)
        
    with col2:
        # Analysis Type
        st.subheader("Analysis Type")
        analysis_type = st.selectbox(
            "Analysis Type",
            ["Lending Patterns", "Demographic Analysis", "Fair Lending", "Market Trends", "Data Quality"]
        )
    
    # Load Data
    if state != "All States":
        data = hmda_api.get_loan_data(year, state)
    else:
        data = pd.DataFrame()  # Handle multi-state analysis
        
    if not data.empty:
        # Validate and clean data
        cleaned_data, validation_errors = loan_analyzer.data_processor.validate_hmda_data(data)
        
        if validation_errors['missing_required_fields'] or validation_errors['invalid_data_types']:
            st.error("Data validation errors found:")
            for error in validation_errors['missing_required_fields'] + validation_errors['invalid_data_types']:
                st.warning(error)
        
        if analysis_type == "Data Quality":
            show_data_quality_analysis(cleaned_data)
        elif analysis_type == "Lending Patterns":
            show_lending_patterns(cleaned_data)
        elif analysis_type == "Demographic Analysis":
            show_demographic_analysis(cleaned_data)
        elif analysis_type == "Fair Lending":
            show_fair_lending_analysis(cleaned_data)
        else:
            show_market_trends(cleaned_data)
    else:
        st.error("Unable to load HMDA data. Please try again.")

def show_data_quality_analysis(data: pd.DataFrame):
    """Display data quality analysis"""
    st.subheader("Data Quality Analysis")
    
    # Perform quality control
    qc_results = loan_analyzer.data_processor.perform_quality_control(data)
    
    # Display summary statistics
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Data Quality Metrics")
        st.metric("Total Records", qc_results['total_records'])
        st.metric("Denial Rate", f"{qc_results['statistics']['denial_rate']:.1%}")
        st.metric("Withdrawal Rate", f"{qc_results['statistics']['withdrawal_rate']:.1%}")
    
    with col2:
        st.write("Quality Control Flags")
        if qc_results['flags']:
            for flag in qc_results['flags']:
                with st.expander(f"⚠️ {flag['type'].replace('_', ' ').title()}"):
                    if 'count' in flag:
                        st.write(f"Records affected: {flag['count']}")
                    if 'value' in flag:
                        st.write(f"Value: {flag['value']:.2%}")
                    if 'threshold' in flag:
                        st.write(f"Threshold: {flag['threshold']:.2f}")
        else:
            st.success("No quality control flags found")
    
    # Show recommendations
    if qc_results['recommendations']:
        st.subheader("Recommendations")
        for rec in qc_results['recommendations']:
            st.info(rec)
    
    # Prepare LAR summary
    st.subheader("LAR Preparation Summary")
    lar_data, lar_summary = loan_analyzer.data_processor.prepare_hmda_lar(data)
    
    if lar_summary['errors']:
        st.error("LAR Preparation Errors:")
        for error in lar_summary['errors']:
            st.warning(error)
    else:
        st.success("LAR preparation completed successfully")
        
        # Show LAR statistics
        stats_cols = st.columns(3)
        stats = lar_summary['statistics']
        
        stats_cols[0].metric("Total Originated", stats['total_originated'])
        stats_cols[1].metric("Total Denied", stats['total_denied'])
        stats_cols[2].metric("Total Withdrawn", stats['total_withdrawn'])
        
        if stats['median_loan_amount']:
            st.metric("Median Loan Amount", f"${stats['median_loan_amount']:,.0f}")
        if stats['median_income']:
            st.metric("Median Income", f"${stats['median_income']:,.0f}")

def analyze_qualification(
    state: str,
    city: str,
    income: float,
    credit_score: int,
    monthly_debt: float,
    property_type: str,
    property_value: float,
    down_payment: float,
    loan_purpose: str
):
    """Analyze loan qualification and provide recommendations"""
    st.info("Analyzing loan qualification...")
    
    # Use most recent available year (2023) for loan qualification analysis
    try:
        loan_data = hmda_api.get_loan_data(2023, state)
    except Exception as e:
        st.error(f"Error fetching loan data: {str(e)}")
        return
        
    if loan_data.empty:
        st.error("Unable to fetch loan data for analysis")
        return
    
    # Calculate key metrics
    loan_amount = property_value - down_payment
    ltv_ratio = loan_amount / property_value
    dti_ratio = (monthly_debt * 12) / income
    
    # Get qualification factors
    factors = loan_analyzer.get_qualification_factors(
        loan_data,
        loan_amount,
        income,
        property_type
    )
    
    # Get market assessment
    market = census_analyzer.get_market_assessment(
        "census_tract",  # Would need actual tract ID
        loan_amount
    )
    
    # Display Results
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Qualification Analysis")
        st.metric("Loan-to-Value Ratio", f"{ltv_ratio:.1%}")
        st.metric("Debt-to-Income Ratio", f"{dti_ratio:.1%}")
        st.metric("Local Approval Rate", f"{factors['approval_rate']:.1%}")
        
    with col2:
        st.subheader("Market Conditions")
        st.metric("Area Median Income", f"${market['median_family_income']:,.0f}")
        st.metric("Affordability Ratio", f"{market['affordability_ratio']:.2f}")
    
    # Show recommendations
    st.subheader("Loan Recommendations")
    recommendations = loan_analyzer._get_loan_recommendations(
        dti_ratio,
        ltv_ratio,
        credit_score,
        income,
        property_value,
        factors
    )
    
    for rec in recommendations:
        with st.expander(f"{rec['type']} Loan - {rec['likelihood']} Likelihood"):
            st.write("Requirements:")
            for req in rec['requirements']:
                st.write(f"- {req}")

def show_lending_patterns(data: pd.DataFrame):
    """Display lending pattern analysis"""
    st.subheader("Lending Patterns Analysis")
    
    # Get market trends
    trends = loan_analyzer.analyze_market_trends(data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Loan Type Distribution")
        st.bar_chart(pd.Series(trends["loan_type_distribution"]))
        
    with col2:
        st.write("Property Type Distribution")
        st.bar_chart(pd.Series(trends["property_type_distribution"]))
    
    st.write("Market Medians")
    cols = st.columns(4)
    for i, (key, value) in enumerate(trends["median_values"].items()):
        cols[i].metric(key.replace("_", " ").title(), f"${value:,.0f}")

def show_demographic_analysis(data: pd.DataFrame):
    """Display demographic analysis"""
    st.subheader("Demographic Analysis")
    
    # Get demographic analysis
    demographics = loan_analyzer.get_demographic_analysis(data)
    
    for category in ["race", "ethnicity", "sex"]:
        st.write(f"\n{category.title()} Analysis")
        df = pd.DataFrame.from_dict(demographics[category], orient='index')
        st.dataframe(df)

def show_fair_lending_analysis(data: pd.DataFrame):
    """Display fair lending analysis"""
    st.subheader("Fair Lending Analysis")
    
    # Analyze approval patterns
    patterns = loan_analyzer.analyze_approval_patterns(data)
    
    st.metric("Overall Approval Rate", f"{patterns['overall_approval_rate']:.1%}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Approval Rates by Loan Type")
        st.bar_chart(pd.Series(patterns["loan_type_approval_rates"]))
        
    with col2:
        st.write("Approval Rates by Income Bracket")
        st.bar_chart(pd.Series(patterns["income_bracket_approval_rates"]))
    
    # Show denial reasons
    denial_patterns = loan_analyzer.analyze_denial_patterns(data)
    st.write("\nDenial Reasons")
    st.bar_chart(pd.Series(denial_patterns["reason_distribution"]))

def show_market_trends(data: pd.DataFrame):
    """Display market trend analysis"""
    st.subheader("Market Trends")
    
    # Get neighborhood characteristics
    neighborhood = census_analyzer.analyze_neighborhood_characteristics(data)
    
    st.write("Lending by Minority Population Percentage")
    minority_df = pd.DataFrame.from_dict(
        neighborhood["minority_population_analysis"],
        orient='index'
    )
    st.line_chart(minority_df["action_taken"])
    
    st.write("Lending by Tract Income Level")
    income_df = pd.DataFrame.from_dict(
        neighborhood["tract_income_analysis"],
        orient='index'
    )
    st.line_chart(income_df["action_taken"])

if __name__ == "__main__":
    main()
