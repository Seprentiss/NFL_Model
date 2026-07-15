import pandas as pd
import numpy as np
import requests


week = 1

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
}

url = "https://www.vegasinsider.com/nfl/odds/las-vegas/"

# Fetch the webpage content with the custom headers
response = requests.get(url, headers=headers)

df = pd.read_html("https://www.vegasinsider.com/nfl/odds/las-vegas/")[0]

df.rename(columns={'Time': 'Team'}, inplace=True)

df.dropna(subset = ['Team'], inplace=True)



df = df[df["Team"].str.contains("Matchup") == False]
df = df[df["Team"].str.contains("Final") == False]

df["Team"] = df["Team"].astype(str)

df["Team"] = df["Team"].str.split(' ').str[1]

print(df["Team"])

df["Consensus"] = df["Consensus"].str.split(" ")

# Create two new columns based on the first and second indices
df['Spread'] = df['Consensus'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
df['Odds'] = df['Consensus'].apply(lambda x: x[1] if isinstance(x, list) and len(x) > 1 else None)

# Print the resulting DataFrame
df = df[df["Odds"].notna()]

df = df[~df['Spread'].str.startswith(('u', 'o'))]

print(df)

df[["Team","Spread"]].to_csv(f"2026 Vegas Lines/Vegas_Lines_Week_{week}.csv",index=False)