import pandas as pd
import numpy as np
from datetime import datetime

def preprocess_ev_stations(input_file, output_file):
    #preprocessing EV charging station data from AFDC dataset.
    # reading the dataset with all columns as string initially
    df = pd.read_csv(input_file, low_memory=False)
    
    # selectimg only EV-relevant columns
    columns_to_keep = [
        'Station Name', 'Street Address', 'City', 'State', 'ZIP',
        'Status Code', 'Access Days Time', 'EV Level2 EVSE Num',
        'EV DC Fast Count', 'EV Network', 'EV Connector Types',
        'Latitude', 'Longitude', 'Open Date', 'EV Pricing',
        'EV On-Site Renewable Source', 'Restricted Access',
        'EV Workplace Charging'
    ]
    
    # columns and handle missing values
    df = df[columns_to_keep].copy()
    
    # cleaning names
    df.columns = df.columns.str.lower().str.replace(' ', '_')
    
    # converting neumeric columns 
    df['ev_level2_evse_num'] = pd.to_numeric(df['ev_level2_evse_num'], errors='coerce').fillna(0)
    df['ev_dc_fast_count'] = pd.to_numeric(df['ev_dc_fast_count'], errors='coerce').fillna(0)
    
    # total_chargers
    df['total_chargers'] = df['ev_level2_evse_num'] + df['ev_dc_fast_count']
    
    # dates
    df['open_date'] = pd.to_datetime(df['open_date'], errors='coerce')
    df['station_age_days'] = (pd.Timestamp.now() - df['open_date']).dt.days
    
    # creating accessibility features - fixing the data type issues
    df['is_24_7'] = df['access_days_time'].fillna('').astype(str).str.contains('24 hours', case=False).astype(int)
    df['is_public'] = (~df['restricted_access'].fillna('').astype(str).str.contains('private', case=False)).astype(int)
    df['is_workplace'] = df['ev_workplace_charging'].fillna('').astype(str).str.contains('YES', case=False).astype(int)
    
    # network information
    df['ev_network'] = df['ev_network'].fillna('Independent')
    
    # connector type features
    df['has_ccs'] = df['ev_connector_types'].fillna('').astype(str).str.contains('J1772COMBO', case=False).astype(int)
    df['has_chademo'] = df['ev_connector_types'].fillna('').astype(str).str.contains('CHADEMO', case=False).astype(int)
    df['has_tesla'] = df['ev_connector_types'].fillna('').astype(str).str.contains('TESLA', case=False).astype(int)
    
    # preprocessiing pricing information
    df['is_free'] = df['ev_pricing'].fillna('').astype(str).str.contains('free', case=False).astype(int)
    
    # station metrics
    df['charging_capacity'] = df['ev_level2_evse_num'] * 7.2 + df['ev_dc_fast_count'] * 50  # kW
    
    # state-level metrics
    state_stats = df.groupby('state').agg({
        'station_name': 'count',
        'total_chargers': 'sum',
        'charging_capacity': 'sum'
    }).reset_index()
    
    state_stats.columns = ['state', 'stations_in_state', 'chargers_in_state', 'capacity_in_state']
    df = df.merge(state_stats, on='state', how='left')
    
    # station density score(0-1 scale)
    df['station_density_score'] = (df['stations_in_state'] / df['stations_in_state'].max()).round(3)
    
    # converting composite accessibility score (0-1 scale)
    df['accessibility_score'] = (
        (df['is_24_7'] * 0.4) +
        (df['is_public'] * 0.4) +
        (df['is_workplace'] * 0.2)
    ).round(3)
    
    # utilization metrics (for analysis purposes)
    np.random.seed(42)  # for reproducibility
    
    # base utilization affected by multiple factors
    base_utilization = (
        0.5 +  # base rate
        df['is_public'] * 0.2 +  # public stations bonus
        df['is_24_7'] * 0.1 +    # 24/7 stations bonus
        (df['charging_capacity'] / df['charging_capacity'].max()) * 0.2  # capacity bonus
    )
    
    # add random variation
    df['utilization_rate'] = (
        base_utilization + 
        np.random.normal(0, 0.1, len(df))  # add noise
    ).clip(0, 1).round(3)  # ensure between 0 and 1
    
    # calculate estimated daily revenue
    avg_kwh_cost = 0.30  # average cost per kWh
    hours_per_day = 24
    
    df['daily_revenue_potential'] = (
        df['charging_capacity'] *  # total kW capacity
        hours_per_day *           # hours of operation
        0.5 *                     # average capacity factor
        df['utilization_rate'] *  # station-specific utilization
        avg_kwh_cost             # price per kWh
    ).round(2)
    
    # Print data quality check
    print("\nData Quality Check:")
    print("\nMissing values:")
    print(df.isnull().sum())
    
    print("\nValue counts for key indicators:")
    print("\nNetwork distribution:")
    print(df['ev_network'].value_counts().head())
    
    print("\nCharger type distribution:")
    print(f"Total Level 2 chargers: {df['ev_level2_evse_num'].sum()}")
    print(f"Total DC Fast chargers: {df['ev_dc_fast_count'].sum()}")
    
    # saving datsaet
    df.to_csv(output_file, index=False)
    
    print(f"\nProcessed data saved to: {output_file}")
    print(f"Total stations processed: {len(df)}")
    print(f"Total states covered: {df['state'].nunique()}")
    
    return df

if __name__ == "__main__":
    input_file = "data/raw/alt_fuel_stations.csv"
    output_file = "data/processed/ev_analysis_final.csv"
    try:
        processed_df = preprocess_ev_stations(input_file, output_file)
        print("\nPreprocessing completed successfully!")
    except Exception as e:
        print(f"\nError during preprocessing: {str(e)}")
        print("\nPlease check if:")
        print("1. The input file exists in the correct location")
        print("2. You have write permissions for the output directory")
        print("3. The input file contains the expected columns")
