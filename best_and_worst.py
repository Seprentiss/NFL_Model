import os
import pandas
import pandas as pd

teams_dict = {}
for season in range(1999,2020):
    directory_path = f"Team Stats/{season}/{21}/Net_Ratings.csv"
    data = pd.read_csv(directory_path)
    for team in data.columns.values:
        teams_dict[f"{team} ( {season} )"] = round(data[team].iloc[0],3)

for season in range(2020,2023):
    directory_path = f"Team Stats/{season}/{22}/Net_Ratings.csv"
    data = pd.read_csv(directory_path)
    for team in data.columns.values:
        teams_dict[f"{team} ( {season} )"] = round(data[team].iloc[0],3)

directory_path = f"Team Stats/{2023}/{22}/Net_Ratings.csv"
data = pd.read_csv(directory_path)
for team in data.columns.values:
    teams_dict[f"{team} ( {2023} )"] = round(data[team].iloc[0], 3)


sorted_teams_dict = dict(sorted(teams_dict.items(), key=lambda x: x[1], reverse=True))


print(sorted_teams_dict)

final_data = pd.DataFrame(columns=["Team","ADJ EPA Per Play"])
final_data["Team"] = sorted_teams_dict.keys()
final_data["ADJ EPA Per Play"] = sorted_teams_dict.values()
final_data.index +=1
final_data.to_csv("Teams Ranked.csv",index_label="Rank")

teams_dict = {}
for season in range(1999,2020):
    directory_path = f"Team Stats/{season}/{21}/Net_Off_Ratings.csv"
    data = pd.read_csv(directory_path)
    for team in data.columns.values:
        teams_dict[f"{team} ( {season} )"] = round(data[team].iloc[0],3)

for season in range(2020,2023):
    directory_path = f"Team Stats/{season}/{22}/Net_Ratings.csv"
    data = pd.read_csv(directory_path)
    for team in data.columns.values:
        teams_dict[f"{team} ( {season} )"] = round(data[team].iloc[0],3)

directory_path = f"Team Stats/{2023}/{22}/Net_Off_Ratings.csv"
data = pd.read_csv(directory_path)
for team in data.columns.values:
    teams_dict[f"{team} ( {2023} )"] = round(data[team].iloc[0], 3)


sorted_teams_dict = dict(sorted(teams_dict.items(), key=lambda x: x[1], reverse=True))


print(sorted_teams_dict)

final_data = pd.DataFrame(columns=["Team","ADJ EPA Per Play"])
final_data["Team"] = sorted_teams_dict.keys()
final_data["ADJ EPA Per Play"] = sorted_teams_dict.values()
final_data.index +=1
final_data.to_csv("Teams Ranked Off.csv",index_label="Rank")

teams_dict = {}
for season in range(1999,2020):
    directory_path = f"Team Stats/{season}/{21}/Net_Def_Ratings.csv"
    data = pd.read_csv(directory_path)
    for team in data.columns.values:
        teams_dict[f"{team} ( {season} )"] = round(data[team].iloc[0],3)

for season in range(2020,2023):
    directory_path = f"Team Stats/{season}/{22}/Net_Ratings.csv"
    data = pd.read_csv(directory_path)
    for team in data.columns.values:
        teams_dict[f"{team} ( {season} )"] = round(data[team].iloc[0],3)

directory_path = f"Team Stats/{2023}/{22}/Net_Def_Ratings.csv"
data = pd.read_csv(directory_path)
for team in data.columns.values:
    teams_dict[f"{team} ( {2023} )"] = round(data[team].iloc[0], 3)


sorted_teams_dict = dict(sorted(teams_dict.items(), key=lambda x: x[1], reverse=True))


print(sorted_teams_dict)

final_data = pd.DataFrame(columns=["Team","ADJ EPA Per Play"])
final_data["Team"] = sorted_teams_dict.keys()
final_data["ADJ EPA Per Play"] = sorted_teams_dict.values()
final_data.index +=1
final_data.to_csv("Teams Ranked Def.csv",index_label="Rank")


