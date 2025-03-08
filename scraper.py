import requests
import pandas as pd
import time
import socket
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set a default timeout (optional)
socket.setdefaulttimeout(10)

# Function to fetch NAV from the API with retries and exponential backoff
def get_nav(scheme_code, date):
    """Fetch NAV for a specific scheme code and date, checking up to 10 previous days if unavailable."""
    for i in range(10):  # Try fetching NAV up to 10 previous days
        check_date = (date - timedelta(days=i)).strftime("%d-%m-%Y")
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                nav_data = data.get("data", [])
                for entry in nav_data:
                    if entry["date"] == check_date:
                        return float(entry["nav"])
        except Exception as e:
            print(f"⚠ API error: {e} for scheme code {scheme_code}")
    return None  # Return None if no NAV found

# Load the filtered funds Excel file
excel_file = "filtered_funds.xlsx"
df_funds = pd.read_excel(excel_file, engine="openpyxl")

# Standardize column names (strip spaces and rename NAV-related columns)
df_funds.rename(columns=lambda x: x.strip(), inplace=True)
df_funds.rename(columns={"Latest NAV": "NAV", "NAV Date": "NAV_Date"}, inplace=True)
print("Columns after renaming:", df_funds.columns.tolist())

# Ensure NAV column exists before proceeding
if "NAV" not in df_funds.columns:
    raise ValueError("❌ Column 'NAV' not found after renaming! Check the Excel file.")

# Convert NAV_Date to datetime and remove funds with NAV older than 10 days from the latest NAV date
df_funds["NAV_Date"] = pd.to_datetime(df_funds["NAV_Date"], format="%d-%b-%Y")
latest_nav_date = df_funds["NAV_Date"].max()
print(f"Latest NAV Date in dataset: {latest_nav_date.strftime('%d-%b-%Y')}")
ten_days_prior = latest_nav_date - timedelta(days=10)
df_funds = df_funds[df_funds["NAV_Date"] >= ten_days_prior]

# Create "Direct / Regular" column
def classify_plan(scheme_name):
    name = scheme_name.lower()
    if "direct" in name and "regular" in name:
        return "Direct"
    elif "direct" in name:
        return "Direct"
    elif "regular" in name:
        return "Regular"
    else:
        return "Others"

df_funds["Direct / Regular"] = df_funds["Scheme Name"].apply(classify_plan)

# Define NAV periods based on the latest NAV date (not today)
nav_periods = {
    "1M": latest_nav_date - relativedelta(months=1),
    "3M": latest_nav_date - relativedelta(months=3),
    "6M": latest_nav_date - relativedelta(months=6),
    "1Y": latest_nav_date - relativedelta(years=1),
    "3Y": latest_nav_date - relativedelta(years=3),
    "5Y": latest_nav_date - relativedelta(years=5),
    "10Y": latest_nav_date - relativedelta(years=10),
}

# --- Use ThreadPoolExecutor to fetch NAVs concurrently ---
def fetch_navs_for_period(df, period, date, max_workers=20):
    print(f"\nFetching NAVs for {period} as of {date.strftime('%d-%b-%Y')}...")
    results = {}
    codes = df["Scheme Code"].tolist()
    
    # Use ThreadPoolExecutor to run get_nav concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_code = {executor.submit(get_nav, code, date): code for code in codes}
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                nav_value = future.result()
                results[code] = nav_value
            except Exception as exc:
                print(f"⚠ Code {code} generated an exception: {exc}")
                results[code] = None
    # Create a new column in df with the results, matching by Scheme Code
    df[period] = df["Scheme Code"].map(results)
    print(f"✅ Finished fetching NAVs for {period}.")
    # Save intermediate result for this period
    temp_file = f"nav_data_{period}.xlsx"
    df.to_excel(temp_file, index=False, engine="openpyxl")
    print(f"✅ Intermediate data for {period} saved to {temp_file}.")

# Process all funds (all categories/sub-categories)
df_all_funds = df_funds.copy()

# For each NAV period, fetch NAVs concurrently and save intermediate Excel file
for period, date in nav_periods.items():
    fetch_navs_for_period(df_all_funds, period, date)

# Calculate returns in percentage for all funds
for period in nav_periods.keys():
    df_all_funds[f"{period} Return (%)"] = ((df_all_funds["NAV"] / df_all_funds[period] - 1) * 100).round(2)

# Save the final data to an Excel file
output_file = "all_funds_with_returns.xlsx"
df_all_funds.to_excel(output_file, index=False, engine="openpyxl")
print(f"\n✅ Final data saved to {output_file}")

# Show a sample output
print(df_all_funds.head())
