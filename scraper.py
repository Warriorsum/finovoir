import requests
import pandas as pd
import socket
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Set a default timeout for API requests
socket.setdefaulttimeout(10)

# Function to fetch NAV from the API with retries
def get_nav(scheme_code, date):
    """Fetch NAV for a specific scheme code and date, checking up to 10 previous days if unavailable."""
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    try:
        response = requests.get(url, timeout=5)  # Reduced timeout to 5 sec
        if response.status_code == 200:
            data = response.json()
            nav_data = data.get("data", [])

            for i in range(10):  # Try fetching NAV up to 10 previous days
                check_date = (date - timedelta(days=i)).strftime("%d-%m-%Y")
                for entry in nav_data:
                    if entry["date"] == check_date:
                        return float(entry["nav"])  # Stop retrying once valid NAV is found
    except Exception as e:
        print(f"⚠ API error: {e} for scheme code {scheme_code}")
    return None  # Return None if no NAV found

# Load the filtered funds Excel file
excel_file = "filtered_funds.xlsx"
df_funds = pd.read_excel(excel_file, engine="openpyxl")

# Standardize column names and convert NAV_Date to datetime
df_funds.rename(columns=lambda x: x.strip(), inplace=True)
df_funds.rename(columns={"Latest NAV": "NAV", "NAV Date": "NAV_Date"}, inplace=True)
df_funds["NAV_Date"] = pd.to_datetime(df_funds["NAV_Date"], format="%d-%b-%Y")

# Determine the most common NAV date (mode)
most_common_nav_date = df_funds["NAV_Date"].mode()[0]
print(f"Most Common NAV Date: {most_common_nav_date.strftime('%d-%b-%Y')}")

# Save the mode NAV date to a file for later use
with open("latest_nav_date.txt", "w") as file:
    file.write(most_common_nav_date.strftime("%d-%b-%Y"))

# Remove funds with NAV older than 10 days
cutoff_date = most_common_nav_date - timedelta(days=10)
df_funds = df_funds[df_funds["NAV_Date"] >= cutoff_date]

# Create "Direct / Regular" column
def classify_plan(scheme_name):
    name = scheme_name.lower()
    if "direct" in name:
        return "Direct"
    elif "regular" in name:
        return "Regular"
    else:
        return "Others"

df_funds["Direct / Regular"] = df_funds["Scheme Name"].apply(classify_plan)

# Define NAV periods based on the most common NAV date
nav_periods = {
    "1M": most_common_nav_date - relativedelta(months=1),
    "3M": most_common_nav_date - relativedelta(months=3),
    "6M": most_common_nav_date - relativedelta(months=6),
    "1Y": most_common_nav_date - relativedelta(years=1),
    "3Y": most_common_nav_date - relativedelta(years=3),
    "5Y": most_common_nav_date - relativedelta(years=5),
    "10Y": most_common_nav_date - relativedelta(years=10),
}

# --- Fetch NAVs in Batches ---
BATCH_SIZE = 100  # Process 100 funds at a time

def fetch_navs_for_period(df, period, date, max_workers=20):
    print(f"\nFetching NAVs for {period} as of {date.strftime('%d-%b-%Y')}...")
    start_time = time.time()
    
    results = {}
    codes = df["Scheme Code"].tolist()

    # Process funds in smaller batches
    for i in range(0, len(codes), BATCH_SIZE):
        batch = codes[i:i + BATCH_SIZE]

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {executor.submit(get_nav, code, date): code for code in batch}
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    nav_value = future.result()
                    results[code] = nav_value
                except Exception as exc:
                    print(f"⚠ Code {code} generated an exception: {exc}")
                    results[code] = None
    
    df[period] = df["Scheme Code"].map(results)
    duration = time.time() - start_time
    print(f"✅ Finished fetching NAVs for {period}. Took {duration:.2f} seconds.")

# Process all funds
df_all_funds = df_funds.copy()

# Fetch NAVs for each period
for period, date in nav_periods.items():
    fetch_navs_for_period(df_all_funds, period, date)

# Fetch NAVs for Most Common NAV Date
fetch_navs_for_period(df_all_funds, "Most Common NAV", most_common_nav_date)

# Calculate returns in percentage
for period in nav_periods.keys():
    df_all_funds[f"{period} Return (%)"] = ((df_all_funds["NAV"] / df_all_funds[period] - 1) * 100).round(2)

# Save the final data to an Excel file
output_file = "all_funds_with_returns.xlsx"
df_all_funds.to_excel(output_file, index=False, engine="openpyxl")
print(f"\n✅ Final data saved to {output_file}")
