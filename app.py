from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Load mutual fund data
df = pd.read_excel("ranked_funds.xlsx", engine="openpyxl")

# Keep only required columns
columns_to_keep = ["Scheme Name", "Category", "Sub-Category", "Direct / Regular",
                   "1M Return (%)", "3M Return (%)", "6M Return (%)", "1Y Return (%)",
                   "3Y Return (%)", "5Y Return (%)", "10Y Return (%)"]
df = df[columns_to_keep]

# Convert return columns to numeric
df[["1M Return (%)", "3M Return (%)", "6M Return (%)", "1Y Return (%)",
    "3Y Return (%)", "5Y Return (%)", "10Y Return (%)"]] = df[[
    "1M Return (%)", "3M Return (%)", "6M Return (%)", "1Y Return (%)",
    "3Y Return (%)", "5Y Return (%)", "10Y Return (%)"]].apply(pd.to_numeric, errors="coerce")

# Extract unique categories and sub-categories (ensure no None values)
categories = sorted(df["Category"].dropna().unique())
sub_categories_dict = df.groupby("Category")["Sub-Category"].unique().apply(list).to_dict()

# Ensure no undefined values in sub_categories_dict
for key in sub_categories_dict:
    sub_categories_dict[key] = [sub_cat for sub_cat in sub_categories_dict[key] if pd.notna(sub_cat)]

direct_regular_options = ["All", "Direct", "Regular"]

# Read the most common NAV date from the file
try:
    with open("latest_nav_date.txt", "r") as file:
        most_common_nav_date = file.read().strip()
except FileNotFoundError:
    most_common_nav_date = "Unknown"

@app.route("/", methods=["GET", "POST"])
def index():
    filtered_funds = df.copy()

    # Default values for dropdowns
    category = request.form.get("category", "All")
    sub_category = request.form.get("sub_category", "All")
    direct_regular = request.form.get("direct_regular", "All")
    short_term_weight = float(request.form.get("short_term_weight", 50))

    # Calculate long-term weight dynamically
    long_term_weight = 100 - short_term_weight

    # Apply filters
    if category != "All":
        filtered_funds = filtered_funds[filtered_funds["Category"] == category]

    if sub_category != "All":
        filtered_funds = filtered_funds[filtered_funds["Sub-Category"].str.strip().str.lower() == sub_category.strip().lower()]

    if direct_regular != "All":
        filtered_funds = filtered_funds[filtered_funds["Direct / Regular"] == direct_regular]

    # Compute ranks only if DataFrame is not empty
    if not filtered_funds.empty:
        filtered_funds["Short-Term Average Rank"] = filtered_funds[[
            "1M Return (%)", "3M Return (%)", "6M Return (%)", "1Y Return (%)"
        ]].rank(ascending=False, method="min").mean(axis=1)

        filtered_funds["Long-Term Average Rank"] = filtered_funds[[
            "3Y Return (%)", "5Y Return (%)", "10Y Return (%)"
        ]].rank(ascending=False, method="min").mean(axis=1)

        filtered_funds["Weighted Average Rank"] = (
            (filtered_funds["Short-Term Average Rank"] * short_term_weight / 100) +
            (filtered_funds["Long-Term Average Rank"] * long_term_weight / 100)
        )

        filtered_funds[["Short-Term Average Rank", "Long-Term Average Rank", "Weighted Average Rank"]] = \
            filtered_funds[["Short-Term Average Rank", "Long-Term Average Rank", "Weighted Average Rank"]].round(1)

    # Sort by Weighted Average Rank
    filtered_funds["Weighted Average Rank"] = pd.to_numeric(filtered_funds["Weighted Average Rank"], errors="coerce")
    filtered_funds = filtered_funds.sort_values(by="Weighted Average Rank", ascending=True, na_position="last")

    # Replace NaNs with "–"
    filtered_funds.fillna("–", inplace=True)

    return render_template("index.html", categories=categories, sub_categories_dict=sub_categories_dict,
                           direct_regular_options=direct_regular_options, funds=filtered_funds,
                           short_term_weight=short_term_weight, long_term_weight=long_term_weight,
                           selected_category=category, selected_sub_category=sub_category,
                           selected_direct_regular=direct_regular, most_common_nav_date=most_common_nav_date)

if __name__ == "__main__":
    app.run(debug=True)
