from pathlib import Path

import pandas as pd

COLUMNS = [
    "Player",
    "POS",
    "Total EPA",
    "EPA per Play ( all plays contributed )"
]

dfs = []

base_dir = Path("Player Stats")

latest_qb_data_by_year = {}

for year_dir in base_dir.iterdir():
    if not year_dir.is_dir():
        continue

    # Find numeric week directories
    week_dirs = [
        d for d in year_dir.iterdir()
        if d.is_dir() and d.name.isdigit()
    ]

    if not week_dirs:
        continue

    # Get largest week number
    latest_week_dir = max(week_dirs, key=lambda d: int(d.name))


    qb_file = latest_week_dir / "qb_data.csv"

    if qb_file.exists():
        latest_qb_data_by_year[year_dir.name] = qb_file

# Example: print results
for year, path in latest_qb_data_by_year.items():
    df = pd.read_csv(path)

    # Keep only needed columns
    df = df[COLUMNS].copy()

    # Add season
    df["season"] = int(year)

    dfs.append(df)

all_qb_epa = pd.concat(dfs, ignore_index=True)


df = all_qb_epa.rename(columns={
    "Total EPA": "total_epa",
    "EPA per Play ( all plays contributed )": "epa_per_play"
})

# Sort properly
df = df.sort_values(["Player", "season"])

# Running total EPA per QB
df["cumulative_epa"] = df.groupby("Player")["total_epa"].cumsum()

import plotly.express as px

fig = px.line(
    df,
    x="season",
    y="cumulative_epa",
    color="Player",
    markers=True,
    title="Running Total EPA by QB Over Time",
    labels={
        "season": "Season",
        "cumulative_epa": "Cumulative Total EPA"
    }
)

fig.update_layout(
    hovermode="x unified",
    legend_title_text="Quarterback"
)

fig.show()



