import pandas as pd
import numpy as np
import re

import main

df = pd.read_html("https://www.vegasinsider.com/nfl/odds/win-totals/")[0]

# Function to extract description
def extract_description(text):
  if isinstance(text, str):  # Ensure the value is a string
        match = re.search(r'"description":"(.*?)"', text)
        return match.group(1) if match else None
  return None  # Return None for non-string values

# Apply the function to the DataFrame column
df['Description'] = df['Time'].apply(extract_description)
# Regex pattern to extract numbers following 'o'
pattern = r'o(\d{1,2}(\.\d)?)'
# Apply the pattern to the column
columns_to_extract = ['BetMGM', 'DraftKings', 'BallyBet', 'RiversCasino']
# Apply regex to each specified column
for column in columns_to_extract:
    df[column] = df[column].apply(lambda x: re.search(pattern, str(x)).group(1) if isinstance(x, str) and re.search(pattern, x) else None)
    # Convert the extracted values to numeric, handling errors by setting them to NaN
    df[column] = pd.to_numeric(df[column], errors='coerce')

df['Average'] = df[columns_to_extract].mean(axis=1)
df['Average'] = df['Average'].dropna().apply(lambda x: round(x * 2) / 2)
final = df[['Description','Average']].dropna().sort_values(by='Description')
final = final.rename(columns={'Description': 'Team', 'Average': 'Vegas Wins'})
final["Team"] = final["Team"].apply(main.getTeamAbv)
final.to_csv("NFL Vegas Win Totals 2025.csv",index=False)
