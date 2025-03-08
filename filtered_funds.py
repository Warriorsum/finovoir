import requests
import pandas as pd
from datetime import datetime, timedelta

# AMFI URL for mutual fund data
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

# Step 1: Download and Read AMFI Data
print("📥 Downloading latest mutual fund data from AMFI...")
response = requests.get(AMFI_URL)
if response.status_code != 200:
    raise Exception(f"❌ Failed to fetch data from AMFI. Status Code: {response.status_code}")

# Step 2: Process Data
data = response.text.splitlines()
cleaned_data = []
category, sub_category = None, None  # Placeholder for category extraction

print("🔍 Processing fund data...")

for line in data:
    line = line.strip()
    
    # Identify category & sub-category (e.g., "Open Ended Schemes (Debt Scheme - Banking and PSU Fund)")
    if line.startswith("Open Ended Schemes"):
        category_info = line.split("(", 1)[-1].split(")")[0]  # Extracts "Debt Scheme - Banking and PSU Fund"
        if " - " in category_info:
            category, sub_category = category_info.split(" - ", 1)
        else:
            category, sub_category = category_info, None
        continue  # Skip processing this line further

    # Skip headers and empty lines
    if not line or any(keyword in line for keyword in ["Scheme Code", "ISIN", "Net Asset Value", "Date"]):
        continue

    # Parse Fund Data (Scheme Code; ISIN Div Payout/ ISIN Growth; ISIN Div Reinvestment; Scheme Name; NAV; Date)
    fields = line.split(";")
    if len(fields) < 5:
        continue  # Skip invalid rows

    scheme_code = fields[0]
    isin = fields[1] if fields[1] else None
    scheme_name = fields[3]
    nav = fields[4]
    nav_date = fields[5]

    # Apply filters: Keep only Growth funds, remove IDCW funds
    scheme_name_lower = scheme_name.lower()
    if (
        ("growth" in scheme_name_lower and "idcw" not in scheme_name_lower)
        or scheme_name_lower.endswith("growth plan")
        or scheme_name_lower.endswith("growth option")
    ):
        cleaned_data.append([scheme_code, isin, scheme_name, category, sub_category, nav, nav_date])

# Step 3: Convert Data to DataFrame
columns = ["Scheme Code", "ISIN", "Scheme Name", "Category", "Sub-Category", "NAV", "NAV_Date"]
df_funds = pd.DataFrame(cleaned_data, columns=columns)

# Step 4: Convert NAV_Date to datetime format
df_funds["NAV_Date"] = pd.to_datetime(df_funds["NAV_Date"], format="%d-%b-%Y")

# Step 5: Remove funds with NAV older than 10 days from latest NAV date
latest_nav_date = df_funds["NAV_Date"].max()
cutoff_date = latest_nav_date - timedelta(days=10)
df_funds = df_funds[df_funds["NAV_Date"] >= cutoff_date]
print(f"✅ Removed funds older than 10 days. Keeping funds with NAV from {cutoff_date.strftime('%d-%b-%Y')} onwards.")

# Step 6: Create "Direct / Regular" column
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

# Step 7: Save Processed Data to Excel
output_file = "filtered_funds.xlsx"
df_funds.to_excel(output_file, index=False, engine="openpyxl")
print(f"✅ Updated fund data saved to {output_file}")

# Step 8: Show Sample Output
print(df_funds.head())
