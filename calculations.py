import pandas as pd
import numpy as np

# Load the Excel file
input_file = "all_funds_with_returns.xlsx"
df = pd.read_excel(input_file, engine="openpyxl")

# Drop rows with missing returns
return_columns = ["1M Return (%)", "3M Return (%)", "6M Return (%)", "1Y Return (%)", "3Y Return (%)", "5Y Return (%)", "10Y Return (%)"]
df = df.dropna(subset=return_columns, how="all")

# ✅ **Annualize 3Y, 5Y, and 10Y returns using CAGR formula & round to 2 decimals**
def annualize_return(returns, years):
    return round(((1 + returns / 100) ** (1 / years) - 1) * 100, 2) if pd.notna(returns) else np.nan

df["3Y Return (%)"] = df["3Y Return (%)"].apply(lambda x: annualize_return(x, 3))
df["5Y Return (%)"] = df["5Y Return (%)"].apply(lambda x: annualize_return(x, 5))
df["10Y Return (%)"] = df["10Y Return (%)"].apply(lambda x: annualize_return(x, 10))

# ✅ **Ranking function (higher return gets Rank 1, lowest gets last rank)**
def calculate_ranks(column):
    return column.rank(method="min", ascending=False).astype("Int64")  # Ensure integer ranks

# ✅ **Apply ranking to each return period**
for col in return_columns:
    rank_col = f"{col} Rank"
    df[rank_col] = calculate_ranks(df[col])

# ✅ **Compute Short-Term and Long-Term Average Ranks**
df["Short-Term Avg Rank"] = df[["1M Return (%) Rank", "3M Return (%) Rank", "6M Return (%) Rank", "1Y Return (%) Rank"]].mean(axis=1).round(2)
df["Long-Term Avg Rank"] = df[["3Y Return (%) Rank", "5Y Return (%) Rank", "10Y Return (%) Rank"]].mean(axis=1).round(2)

# ✅ **Default weights (user-adjustable via website)**
short_term_weight = 0.5
long_term_weight = 0.5

# ✅ **Calculate Weighted Average Rank & round to 2 decimals**
df["Weighted Average Rank"] = ((df["Short-Term Avg Rank"] * short_term_weight) + 
                               (df["Long-Term Avg Rank"] * long_term_weight)).round(2)

# ✅ **Sort funds based on Weighted Average Rank**
df = df.sort_values(by="Weighted Average Rank")

# ✅ **Save processed data to Excel**
output_file = "ranked_funds.xlsx"
df.to_excel(output_file, index=False, engine="openpyxl")

print(f"✅ Processed data saved to {output_file}")
