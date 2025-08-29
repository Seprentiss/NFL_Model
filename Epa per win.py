import pandas as pd
import main

def save_to_csv(file_name, results):
    df = pd.DataFrame(results)
    df.to_csv(file_name, index=False)
    print(f"Data saved to {file_name}")

def EPA_per_win():
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

def HFA_reg_vs_post():

    for s in [2020,2021,2022,2023]:
        data = pd.read_csv(f"Data/play_by_play_{s}.csv")
        data = data[(data["week"] < 18)]

        data = data[data['side_of_field'].notna()]

        total_home_epa = 0
        total_away_epa = 0

        for week in data["week"].unique():
            week_data = data[(data["week"] == week)]
            for i in range(len(week_data)):
                epa = week_data["epa"].iloc[i]
                if week_data["home_team"].iloc[i] == week_data["posteam"].iloc[i]:
                    total_home_epa += epa
                elif data["home_team"].iloc[i] == data["defteam"].iloc[i]:
                    total_home_epa += (epa * -1)

            for i in range(len(week_data)):
                epa = week_data["epa"].iloc[i]
                if week_data["away_team"].iloc[i] == week_data["posteam"].iloc[i]:
                    total_away_epa += epa
                elif data["away_team"].iloc[i] == data["defteam"].iloc[i]:
                    total_away_epa += epa * -1

        print((total_home_epa-total_away_epa)/len(data))

HFA_reg_vs_post()


