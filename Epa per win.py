import pandas as pd
import main

def save_to_csv(file_name, results):
    df = pd.DataFrame(results)
    df.to_csv(file_name, index=False)
    print(f"Data saved to {file_name}")

output = []
for s in [2020,2021,2022,2023]:
    data = pd.read_csv(f"Data/play_by_play_{s}.csv")
    schedule_data = pd.read_csv(f"Data/NFL_SCHEDULE_{s}.csv")

    wins_data = pd.DataFrame(schedule_data["Winner/tie"].apply(main.getTeamAbv)).groupby(schedule_data["Winner/tie"]).count()

    teams = data["home_team"].unique()
    print(teams)
    for t in teams:
        output.append({"Team":t,"EPA":data[data['posteam'] == t]['epa'].sum() + data[data['defteam'] == t]['epa'].sum()*-1,
                       "Wins":wins_data.loc[main.abvToName(t,s)].iloc[0]
        })
        print(f"{t} : {data[data['posteam'] == t]['epa'].sum() + data[data['defteam'] == t]['epa'].sum()*-1} {wins_data.loc[main.abvToName(t,s)].iloc[0]}")

save_to_csv(f"EPA_Per_Win.csv", output)