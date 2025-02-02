import pandas as pd
import requests
from typing import Dict, List, Optional
from pathlib import Path

class HMDAApi:
    """Interface for HMDA Data Browser API that handles data retrieval and caching"""
    
    BASE_URL = "https://ffiec.cfpb.gov/v2/data-browser-api"
    
    def __init__(self):
        self.cache_dir = Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get_loan_data(
        self,
        year: int,
        states: Optional[List[str]] = None,
        msamds: Optional[List[str]] = None,
        filters: Optional[Dict] = None,
        cache: bool = True
    ) -> pd.DataFrame:
        """
        Get HMDA loan application data through Data Browser API
        
        Args:
            year: Year to get data for (2018 onwards)
            states: Optional list of state codes
            msamds: Optional list of MSA/MD codes
            filters: Optional filters like loan_purposes, actions_taken etc.
            cache: Whether to use cached data if available
            
        Returns:
            DataFrame containing filtered HMDA data
        """
        # Generate cache key from parameters
        cache_key = f"hmda_{year}"
        if states:
            cache_key += f"_{'_'.join(states)}"
        if msamds:
            cache_key += f"_{'_'.join(msamds)}"
        cache_file = self.cache_dir / f"{cache_key}.csv"
        
        # Check cache first
        if cache and cache_file.exists():
            return pd.read_csv(cache_file)
        
        # Build query parameters
        params = {"years": str(year)}
        
        if states:
            params["states"] = ",".join(states)
        if msamds:
            params["msamds"] = ",".join(msamds)
        if filters:
            params.update(filters)
            
        # Get CSV data from API
        response = requests.get(
            f"{self.BASE_URL}/view/csv",
            params=params,
            stream=True
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.text}")
            
        # Stream response to temporary file then read into DataFrame
        tmp_file = Path("tmp_hmda_data.csv")
        with open(tmp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        df = pd.read_csv(tmp_file)
        tmp_file.unlink()  # Delete temporary file
        
        # Cache the data if requested
        if cache:
            df.to_csv(cache_file, index=False)
            
        return df

    def get_filers(
        self,
        year: int,
        states: Optional[List[str]] = None,
        msamds: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Get list of HMDA filers for given year and geography
        
        Args:
            year: Filing year
            states: Optional list of state codes
            msamds: Optional list of MSA/MD codes
            
        Returns:
            DataFrame containing filer information
        """
        params = {"years": str(year)}
        
        if states:
            params["states"] = ",".join(states)
        if msamds:
            params["msamds"] = ",".join(msamds)
            
        response = requests.get(
            f"{self.BASE_URL}/view/filers",
            params=params
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.text}")
            
        return pd.DataFrame(response.json()["institutions"])
