import math
import os
import warnings
import time

import polars as pl
import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None

warnings.filterwarnings("ignore", message="Columns .* have mixed types.", category=UserWarning)

global offensive_epa_dict, defensive_epa_dict


def getTeamAbv(team):
    team_abvs = {'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
                 'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
                 'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
                 'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB', 'Houston Texans': 'HOU',
                 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX', 'Kansas City Chiefs': 'KC',
                 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC', 'Los Angeles Rams': 'LA',
                 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN', 'New England Patriots': 'NE',
                 'New Orleans Saints': 'NO', 'New York Giants': 'NYG', 'New York Jets': 'NYJ', 'Oakland Raiders': 'LV',
                 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT', 'San Francisco 49ers': 'SF',
                 'San Diego Chargers': 'LAC', 'St. Louis Rams': 'LA',
                 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB', 'Tennessee Titans': 'TEN',
                 'Washington Commanders': 'WAS', 'Washington Football Team': "WAS", 'Washington Redskins': 'WAS'}
    if team in team_abvs:
        return team_abvs[team]
    else:
        return None

def getTeamAbvShortName(team):
    short_name_abbreviations = {
        'Cardinals': 'ARI',
        'Falcons': 'ATL',
        'Ravens': 'BAL',
        'Bills': 'BUF',
        'Panthers': 'CAR',
        'Bears': 'CHI',
        'Bengals': 'CIN',
        'Browns': 'CLE',
        'Cowboys': 'DAL',
        'Broncos': 'DEN',
        'Lions': 'DET',
        'Packers': 'GB',
        'Texans': 'HOU',
        'Colts': 'IND',
        'Jaguars': 'JAX',
        'Chiefs': 'KC',
        'Raiders': 'LV',
        'Chargers': 'LAC',
        'Rams': 'LA',
        'Dolphins': 'MIA',
        'Vikings': 'MIN',
        'Patriots': 'NE',
        'Saints': 'NO',
        'Giants': 'NYG',
        'Jets': 'NYJ',
        'Eagles': 'PHI',
        'Steelers': 'PIT',
        '49ers': 'SF',
        'Seahawks': 'SEA',
        'Buccaneers': 'TB',
        'Titans': 'TEN',
        'Commanders': 'WAS'
    }
    if team in short_name_abbreviations:
        return short_name_abbreviations[team]
    else:
        return None


def abvToName(team_abv, season):
    team_names = {'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
                  'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
                  'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
                  'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
                  'HOU': 'Houston Texans',
                  'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars', 'KC': 'Kansas City Chiefs',
                  'LV': ['Las Vegas Raiders', 'Oakland Raiders'], 'LAC': ['Los Angeles Chargers', 'San Diego Chargers'],
                  'LA': ['Los Angeles Rams', 'St. Louis Rams'],
                  'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings', 'NE': 'New England Patriots',
                  'NO': 'New Orleans Saints', 'NYG': 'New York Giants', 'NYJ': 'New York Jets',
                  'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers', 'SF': 'San Francisco 49ers',
                  'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers', 'TEN': 'Tennessee Titans',
                  'WAS': ['Washington Commanders', "Washington Football Team", 'Washington Redskins']}

    if team_abv in team_names:
        if team_abv == "LAC":
            if season < 2017:
                return team_names[team_abv][1]
            return team_names[team_abv][0]
        elif team_abv == "LA":
            if season < 2016:
                return team_names[team_abv][1]
            return team_names[team_abv][0]
        elif team_abv == "LV":
            if season < 2020:
                return team_names[team_abv][1]
            return team_names[team_abv][0]
        elif team_abv == 'WAS':
            if season < 2020:
                return team_names[team_abv][2]
            elif season < 2022:
                return team_names[team_abv][1]
            return team_names[team_abv][0]
        else:
            return team_names[team_abv]

    else:
        return None


def getTeamOffEpa(team):
    global offensive_epa_dict
    return offensive_epa_dict[team]


def getTeamDefEpa(team):
    global defensive_epa_dict
    return defensive_epa_dict[team]


def getTeamSchedule(team, weeks_played, season):
    sched_data = pd.read_csv(f"Data/NFL_SCHEDULE_{season}.csv")
    sched_data = sched_data[(sched_data["HomeTm"] == team) | (sched_data["VisTm"] == team)]

    opponents = []

    for i in range(len(sched_data)):
        if sched_data["Week"].iloc[i] >= weeks_played:
            continue
        if sched_data["HomeTm"].iloc[i] == team:
            opponents.append(getTeamAbv(sched_data["VisTm"].iloc[i]))
        else:
            opponents.append(getTeamAbv(sched_data["HomeTm"].iloc[i]))

    return opponents


def getTeamScheduleSpecificWeeks(team, weeks, season):
    sched_data = pd.read_csv(f"Data/NFL_SCHEDULE_{season}.csv")
    sched_data = sched_data[(sched_data["HomeTm"] == team) | (sched_data["VisTm"] == team)]

    opponents = []

    for i in range(len(sched_data)):
        if sched_data["Week"].iloc[i] not in weeks:
            continue
        if sched_data["HomeTm"].iloc[i] == team:
            opponents.append(getTeamAbv(sched_data["VisTm"].iloc[i]))
        else:
            opponents.append(getTeamAbv(sched_data["HomeTm"].iloc[i]))

    return opponents


def createOppMatrix(week, season):
    sched_data = pd.read_csv(f"Data/NFL_SCHEDULE_{season}.csv")
    matrix = []
    for team in sorted(set((sched_data['HomeTm'].tolist() + sched_data["VisTm"].tolist()))):
        try:
            matrix.append(getTeamSchedule(team, week, season))
        except:
            continue
    return matrix


def createOppDefMatrix(full_opp_matrix):
    for row in range(len(full_opp_matrix)):
        for col in range(len(full_opp_matrix[row])):
            full_opp_matrix[row][col] = getTeamDefEpa(full_opp_matrix[row][col])
    return full_opp_matrix


def createOppOffMatrix(full_opp_matrix):
    for row in range(len(full_opp_matrix)):
        for col in range(len(full_opp_matrix[row])):
            full_opp_matrix[row][col] = getTeamOffEpa(full_opp_matrix[row][col])
    return full_opp_matrix


def percentage_over_league_average(value, league_average):
    return ((value - league_average) / abs(league_average))


def increase_negative_value(original_value, percentage_increase):
    abs_value = abs(original_value)
    increased_value = original_value + (abs_value * percentage_increase)
    return increased_value

def first_week_hfa(data):

    # Filter out rows where 'side_of_field' is NaN
    data = data[data['side_of_field'].notna()]

    data = data[data["week"] < 19]

    # Calculate total EPA for home and away teams
    total_home_epa = 0
    total_away_epa = 0

    for i in range(len(data)):
        epa = data["epa"].iloc[i]

        if data["home_team"].iloc[i] == data["posteam"].iloc[i]:
            total_home_epa += epa
        elif data["home_team"].iloc[i] == data["defteam"].iloc[i]:
            total_home_epa += (epa * -1)

        if data["away_team"].iloc[i] == data["posteam"].iloc[i]:
            total_away_epa += epa
        elif data["away_team"].iloc[i] == data["defteam"].iloc[i]:
            total_away_epa += (epa * -1)

    # Calculate home field advantage
    hfa = (total_home_epa / len(data)) - (total_away_epa / len(data))

    return hfa

    # Example usage:
    # data = pd.read_csv("path_to_your_data.csv")
    # home_field_advantage = hfa(season)
    # print(home_field_advantage)


def hfa(data,last_season_data,weeks_played=1):
    hfa = first_week_hfa(last_season_data)
    if weeks_played == 1:
        return hfa

    data = data[(data["week"] < weeks_played)]

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

    if weeks_played < 14:
        return (hfa * (1 - (weeks_played - 1) / 13)) + (
                    (total_home_epa / len(data)) - (total_away_epa / len(data))) * (
                (weeks_played - 1) / 13)
    else:
        return ((total_home_epa / len(data)) - (total_away_epa / len(data)))


def teamVarPP(data, last_season_data, team, weeks_played, season):
    if weeks_played == 1:
        last_var = (teamVarPP(last_season_data,None,team, 23, season - 1))
        return last_var

    net_data = pd.read_csv(f"Team Stats/{season}/{weeks_played - 1}/Net_Ratings.csv")

    data = data[(data["week"] < weeks_played)]

    team_data = data[((data['home_team'] == team) | (data['away_team'] == team))]

    team_data = team_data[team_data['side_of_field'].notna()]

    for i in range(len(team_data)):
        if team_data["defteam"].iloc[i] == team:
            team_data["epa"].iloc[i] = team_data["epa"].iloc[i] * -1

    opps = getTeamSchedule(abvToName(team, season), weeks_played, season)

    opps_strength = []

    for opp in opps:
        opps_strength.append(net_data[opp].iloc[0])

    opps_strength_above_avg = [(np.mean(net_data.iloc[0]) - x) * -1 for x in opps_strength]

    week_score = team_data.groupby("week")["epa"].mean().tolist()

    var = np.var([x + y for x, y in zip(week_score, opps_strength_above_avg)])

    if weeks_played < 14:
        last_var = (teamVarPP(last_season_data,None ,team, 23, season - 1))
        return last_var * (1 - (weeks_played - 1) / 13) + var * ((weeks_played - 1) / 13)

    return var


def Adj_Pass_Run_Net(data, pass_run_net="net", season=2023, week=2):
    global defensive_epa_dict, offensive_epa_dict

    offensive_epa_dict = {}
    defensive_epa_dict = {}
    num_of_off_plays = {}

    data = data[(data["week"] < week)]

    if season == 2001:
        data.loc[
            (data["play_id"].isin(
                [1538, 2861, 483, 1104, 2757, 390, 3819, 2518, 2261, 3111, 1942, 3117, 1282, 2402, 1460, 3192, 1528,
                 2129, 970])) &
            (data["posteam"] == "JAX"),
            "epa"
        ] += 14

    if season == 2002:
        data.loc[
            (data["play_id"].isin(
                [2901, 164, 1271, 1280, 1592, 3163, 1970, 3106, 3327, 654, 3324, 1054, 661, 2425, 2366, 2147, 929, 3680,
                 2829])) &
            (data["posteam"] == "JAX"),
            "epa"
        ] += 14

    if pass_run_net == "pass":
        if season > 2001:
            play_types_excluded = ["RUSH"]
            data = data[~data["play_type_nfl"].isin(play_types_excluded)]
        else:
            data = data[~data["play_type"].isin(['run'])]

    elif pass_run_net == "run":
        if season > 2001:
            play_types_included = ["RUSH", "FUMBLE"]
            data = data[data["play_type_nfl"].isin(play_types_included)]
        else:
            data = data[data["play_type"].isin(['run'])]

    for team in sorted(set((data['home_team'].tolist() + data["away_team"].tolist()))):
        team_data = data[((data['home_team'] == team) | (data['away_team'] == team))]

        team_data = team_data[team_data['side_of_field'].notna()]

        off_team_data = team_data[team_data["posteam"] == team]
        def_team_data = team_data[team_data["defteam"] == team]

        off_mean = np.mean(off_team_data["epa"])
        def_mean = np.mean(def_team_data['epa'] * -1)

        offensive_epa_dict[team] = off_mean
        defensive_epa_dict[team] = def_mean
        num_of_off_plays[team] = len(off_team_data)

    if week == 2:
        if pass_run_net == "net":
            net = {}

            for key in defensive_epa_dict.keys():
                net[key] = defensive_epa_dict[key] + offensive_epa_dict[key]

            net = sorted(net.items(), key=lambda x: x[1], reverse=True)
            net = dict(net)

            off_dict = dict(sorted(offensive_epa_dict.items(), key=lambda x: x[1], reverse=True))
            def_dict = dict(sorted(defensive_epa_dict.items(), key=lambda x: x[1], reverse=True))

            return net, def_dict, off_dict, num_of_off_plays

        else:
            off_dict = dict(sorted(offensive_epa_dict.items(), key=lambda x: x[1], reverse=True))
            def_dict = dict(sorted(defensive_epa_dict.items(), key=lambda x: x[1], reverse=True))
            return def_dict, off_dict

    for round in range(25):

        if round == 0:
            o_la = np.mean(list(offensive_epa_dict.values()))
            d_la = np.mean(list(defensive_epa_dict.values()))

        else:
            o_la = np.mean(list(adj_off_dict.values()))
            d_la = np.mean(list(adj_def_dict.values()))

        def_strength_matrix = createOppDefMatrix(createOppMatrix(week, season))
        offensive_epa = list(offensive_epa_dict.values())

        adj_off_dict = {}

        for i in range(len(offensive_epa)):
            weights = np.arange(1, len(def_strength_matrix[i]) + 1) ** (.75)
            weights_normalized = weights / weights.sum()
            weighted_avg = np.average(def_strength_matrix[i], weights=weights_normalized)

            adj_off_dict[list(offensive_epa_dict.keys())[i]] = offensive_epa[i] + (o_la - weighted_avg) * -1

        off_strength_matrix = createOppOffMatrix(createOppMatrix(week, season))
        defensive_epa = list(defensive_epa_dict.values())

        adj_def_dict = {}

        for i in range(len(defensive_epa)):
            weights = np.arange(1, len(off_strength_matrix[i]) + 1)
            weights_normalized = weights / weights.sum()
            weighted_avg = np.average(off_strength_matrix[i], weights=weights_normalized)

            adj_def_dict[list(defensive_epa_dict.keys())[i]] = defensive_epa[i] + (d_la - weighted_avg) * -1

    if pass_run_net == "net":
        adj_net = {}

        for key in adj_def_dict.keys():
            adj_net[key] = adj_def_dict[key] + adj_off_dict[key]

        adj_net = sorted(adj_net.items(), key=lambda x: x[1], reverse=True)
        adj_net = dict(adj_net)

        adj_off_dict = dict(sorted(adj_off_dict.items(), key=lambda x: x[1], reverse=True))
        adj_def_dict = dict(sorted(adj_def_dict.items(), key=lambda x: x[1], reverse=True))

        return adj_net, adj_def_dict, adj_off_dict, num_of_off_plays

    else:
        adj_off_dict = dict(sorted(adj_off_dict.items(), key=lambda x: x[1], reverse=True))
        adj_def_dict = dict(sorted(adj_def_dict.items(), key=lambda x: x[1], reverse=True))
        return adj_def_dict, adj_off_dict


def Qb_epa(qb, data, pass_stats, run_stats):
    qb_data = data[(data['passer_player_name'] == qb) | (data['rusher_player_name'] == qb)]

    team_name = qb_data["posteam"].unique()

    weeks_played = []

    for t in team_name:
        weeks_played.append(list(qb_data[qb_data['posteam'] == t]["week"].unique()))

    all_weeks = set().union(*weeks_played)

    data = data[data["week"].isin(all_weeks)]

    off_plays = 0
    for t in team_name:
        off_plays += len((data[data["posteam"] == t]))

    pass_data = qb_data[qb_data["play_type"].isin(["pass"])]
    run_data = qb_data[qb_data["play_type"].isin(["run"])]

    if (len(run_data["qb_epa"])) > 0:
        qb_epa_pp_pass = pass_data["qb_epa"].mean()
        pass_plays = len(pass_data["epa"])
    else:
        qb_epa_pp_pass = 0
        pass_plays = 0

    if (len(run_data["qb_epa"])) > 0:
        qb_epa_pp_run = run_data["qb_epa"].mean()
        run_plays = len(run_data["qb_epa"])
    else:
        qb_epa_pp_run = 0
        run_plays = 0

    pass_opps = []
    run_opps = []

    total = 0

    for i in range(len(team_name)):
        for opp in getTeamScheduleSpecificWeeks(abvToName(team_name[i], season), weeks=weeks_played[i], season=season):
            pass_opps.append(pass_stats[opp])
            run_opps.append(run_stats[opp])

    adjusted_epa = qb_epa_pp_pass + (np.mean(list(pass_stats.values())) + np.mean(pass_opps)) * -1
    total += (adjusted_epa * pass_plays)

    adjusted_epa = qb_epa_pp_run + (np.mean(list(run_stats.values())) - np.mean(run_opps)) * -1

    total += (adjusted_epa * run_plays)
    if run_plays == 0:
        return total, (total / (run_plays + pass_plays)), (total / off_plays), len(all_weeks)
    else:
        return total, (total / pass_plays), (total / off_plays), len(all_weeks)


def Wr_epa(wr, data, pass_stats):
    wr_data = data[(data['receiver_player_name'] == wr) | (data['rusher_player_name'] == wr)]

    team_name = wr_data["posteam"].unique()
    weeks_played = []

    for t in team_name:
        weeks_played.append(list(wr_data[wr_data['posteam'] == t]["week"].unique()))

    all_weeks = set().union(*weeks_played)

    data = data[data["week"].isin(all_weeks)]

    off_plays = 0
    for t in team_name:
        off_plays += len((data[data["posteam"] == t]))

    pass_data = wr_data[wr_data["play_type"].isin(["pass"])]

    if pass_data["epa"].sum() == 0 or pd.isna(pass_data["epa"].sum()):
        return 0, 0, 0, 0, all_weeks

    wr_epa_pp_pass = 0
    wr_epa_pr_pass = 0

    qualified_plays = 0

    receptions = 0

    # EPA PER PLAY
    for i in range(len(pass_data)):
        if pd.isna(pass_data["yac_epa"].iloc[i]):
            continue
        wr_epa_pp_pass += (pass_data["epa"].iloc[i])

        qualified_plays += 1

    # EPA PER RECEPTION
    for i in range(len(pass_data)):
        if pass_data["comp_air_epa"].iloc[i] == 0 and pass_data["comp_yac_epa"].iloc[i] == 0:
            continue
        if pd.isna(pass_data["epa"].iloc[i]):
            continue
        if pass_data["comp_air_epa"].iloc[i] < 0:
            wr_epa_pr_pass += pass_data["epa"].iloc[i]
        else:
            wr_epa_pr_pass += (pass_data["epa"].iloc[i])

        receptions += 1

    if qualified_plays == 0:
        wr_epa_pp_pass = 0
    else:
        wr_epa_pp_pass = wr_epa_pp_pass / qualified_plays

    if receptions == 0:
        wr_epa_pr_pass = 0
    else:
        wr_epa_pr_pass = wr_epa_pr_pass / receptions

    pass_opps = []

    total = 0
    recep_total = 0

    for i in range(len(team_name)):
        for opp in getTeamScheduleSpecificWeeks(abvToName(team_name[i], season), weeks=weeks_played[i], season=season):
            pass_opps.append(pass_stats[opp])

    adjusted_epa = wr_epa_pr_pass + (np.mean(list(pass_stats.values())) - np.mean(pass_opps)) * -1

    recep_total += (adjusted_epa * receptions)

    adjusted_epa = wr_epa_pp_pass + (np.mean(list(pass_stats.values())) - np.mean(pass_opps)) * -1

    total += (adjusted_epa * qualified_plays)

    if receptions == 0:
        if len(all_weeks) == 0:
            return 0, 0, total / off_plays, off_plays, []
        return 0, 0, total / off_plays, off_plays, all_weeks

    else:
        epa_per_rep = recep_total / receptions
        epa_per_play = total / off_plays

        return (epa_per_rep, receptions, epa_per_play, off_plays, all_weeks)


def Rb_epa(rb, data, pass_stats, run_stats):
    rb_data = data[(data['receiver_player_name'] == rb) | (data['rusher_player_name'] == rb)]

    team_name = rb_data["posteam"].unique()
    weeks_played = []

    for t in team_name:
        weeks_played.append(list(rb_data[rb_data['posteam'] == t]["week"].unique()))

    all_weeks = set().union(*weeks_played)

    data = data[data["week"].isin(all_weeks)]

    off_plays = 0
    for t in team_name:
        off_plays += len((data[data["posteam"] == t]))

    run_data = rb_data[rb_data["play_type"].isin(["run"])]

    rb_epa_pr = run_data["epa"].mean()

    run_plays = len(run_data["epa"])

    run_opps = []

    rush_total = 0

    for i in range(len(team_name)):
        for opp in getTeamScheduleSpecificWeeks(abvToName(team_name[i], season), weeks=weeks_played[i], season=season):
            run_opps.append(run_stats[opp])

    adjusted_epa = rb_epa_pr + (np.mean(list(run_stats.values())) - np.mean(run_opps)) * -1

    rush_total += (adjusted_epa * run_plays)

    results = Wr_epa(rb, data, pass_stats)
    if len(results) < 5:
        epa_per_rep, receptions, epa_per_play, off_rec_plays, wr_weeks_played = results[0], results[1], results[2], \
        results[3], []
    else:
        epa_per_rep, receptions, epa_per_play, off_rec_plays, wr_weeks_played = results[0], results[1], results[2], \
            results[3], results[4]
    total_games = len(set(all_weeks.union(wr_weeks_played)))

    if run_data["epa"].sum() == 0.0 or pd.isna(run_data["epa"].sum()):
        if receptions == 0:
            return (0, 0, 0, 0,
                    0, total_games)
        return ((0 + epa_per_play * off_rec_plays), 0, epa_per_rep,
                ((0 + epa_per_rep * receptions) / (0 + receptions)),
                ((0 + epa_per_play * off_rec_plays) / off_plays), total_games)

    else:
        return ((rush_total + epa_per_play * off_rec_plays), (rush_total / run_plays), epa_per_rep,
                ((rush_total + epa_per_rep * receptions) / (run_plays + receptions)),
                ((rush_total + epa_per_play * off_rec_plays) / off_plays), total_games)


def Player_Stats(num_of_off_plays, pass_stats, run_stats, week=2, season=2023):

    url = f'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv'
    #
    data = pd.read_csv(url, low_memory=True)

    # data = pd.read_csv("player_stats_2025.csv")

    pos_data = pd.DataFrame(
        columns=["Player", "POS", "TM", "GP", "Total EPA", "EPA per Game", "EPA per Play ( all plays contributed )",
                 "EPA per Play ( all offense )", "Total Passing EPA", "EPA per Completion",
                 "EPA per Attempt", "Rushing EPA", "EPA per Carry", "Receiving EPA",
                 "EPA per Reception", "EPA per Target"])

    data = data[data['week'] < week]

    for player in data['player_display_name'].unique():

        new_data = data[data["player_display_name"] == player]
        if len(new_data) == 0:
            continue
        if new_data["position_group"].unique()[0] not in ["QB", "WR", "RB", "TE"]:
            continue
        if (week - 1) > 1:
            pass_opp, run_opp = [], []
            for team in new_data['opponent_team']:
                pass_opp.append(pass_stats[team])
                run_opp.append(run_stats[team])

            for i in range(len(new_data)):
                p_epa = new_data["passing_epa"].iloc[i]
                p_att = new_data["attempts"].iloc[i]

                if p_att > 0:
                    new_data["passing_epa"].iloc[i] = p_att * (
                            (p_epa / p_att) + (np.mean(list(pass_stats.values())) - pass_opp[i]) * -1)

                ru_epa = new_data["rushing_epa"].iloc[i]
                ru_att = new_data["carries"].iloc[i]

                if ru_att > 0:
                    new_data["rushing_epa"].iloc[i] = ru_att * (
                            (ru_epa / ru_att) + (np.mean(list(run_stats.values())) - run_opp[i]) * -1)

                re_epa = new_data["receiving_epa"].iloc[i]
                re_att = new_data["targets"].iloc[i]

                if re_att > 0:
                    new_data["receiving_epa"].iloc[i] = re_att * (
                            (re_epa / re_att) + (np.mean(list(pass_stats.values())) - pass_opp[i]) * -1)
        gp = len(new_data)

        pos = new_data["position"].value_counts().keys()[0]

        passing_epa = sum(new_data["passing_epa"].dropna())

        rushing_epa = sum(new_data["rushing_epa"].dropna())

        receiving_epa = sum(new_data["receiving_epa"].dropna())

        total_epa = passing_epa + rushing_epa + receiving_epa

        receptions = sum(new_data["receptions"].dropna())

        targets = sum(new_data["targets"].dropna())

        carries = sum(new_data["carries"].dropna())

        passing_attempts = sum(new_data["attempts"].dropna())

        completions = sum(new_data["completions"].dropna())

        if (passing_attempts + targets + carries) < 5:
            continue

        # get num of team
        num_off_plays = 0
        teams_played_for = new_data["team"].unique()
        # teams_played_for = new_data["team"].unique()
        for team in teams_played_for:
            num_off_plays += num_of_off_plays[team]

        pos_data.loc[len(pos_data.index)] = [player, pos, teams_played_for, gp, total_epa, total_epa / gp,
                                             total_epa / (passing_attempts + targets + carries),
                                             total_epa / num_off_plays, passing_epa,
                                             passing_epa / completions if completions > 0 else 0,
                                             passing_epa / passing_attempts if passing_attempts > 0 else 0, rushing_epa,
                                             rushing_epa / carries if carries > 0 else 0, receiving_epa,
                                             receiving_epa / receptions if receptions > 0 else 0,
                                             receiving_epa / targets if targets > 0 else 0]

    #     print(f'Player: {player} POS: {pos} GP: {gp} ( per game {total_epa/gp} ) Total EPA: {total_epa} (per play {total_epa / (passing_attempts + targets + carries)}) passing_epa: {passing_epa} ( per completion {passing_epa / completions if completions > 0 else 0} ) ( per attempt {passing_epa/ passing_attempts if passing_attempts > 0 else 0} )  rushing_epa: {rushing_epa} ( per carry {rushing_epa / carries if carries > 0 else 0} ) receiving_epa: {receiving_epa} ( per recep {receiving_epa / receptions if receptions > 0 else 0} ) ( per target {receiving_epa / targets if targets > 0 else 0} )')

    qb_data = pos_data[pos_data["POS"] == "QB"].sort_values("Total EPA", ascending=False).round(4)
    rb_data = pos_data[pos_data["POS"] == "RB"].sort_values("Total EPA", ascending=False)
    wr_data = pos_data[pos_data["POS"] == "WR"].sort_values("Total EPA", ascending=False)
    te_data = pos_data[pos_data["POS"] == "TE"].sort_values("Total EPA", ascending=False)

    qb_data.to_csv(f"Player Stats/{season}/{week-1}/qb_data.csv", index=False)
    rb_data.to_csv(f"Player Stats/{season}/{week-1}/rb_data.csv", index=False)
    wr_data.to_csv(f"Player Stats/{season}/{week-1}/wr_data.csv", index=False)
    te_data.to_csv(f"Player Stats/{season}/{week-1}/te_data.csv", index=False)


def createNflScheduleData(season):
    data = pd.read_html(f"https://www.pro-football-reference.com/years/{season}/games.htm")[0]

    if "HomeTm" in data.columns and "VisTm" in data.columns:
        data.to_csv(f"Data/NFL_SCHEDULE_{season}.csv", index=False)
    else:
        data["HomeTm"] = ""
        data["VisTm"] = ""
        for i in range(len(data)):
            if data['Unnamed: 5'].iloc[i] == "@":
                data['HomeTm'].iloc[i] = data['Loser/tie'].iloc[i]
                data['VisTm'].iloc[i] = data['Winner/tie'].iloc[i]
            else:
                data['HomeTm'].iloc[i] = data['Winner/tie'].iloc[i]
                data['VisTm'].iloc[i] = data['Loser/tie'].iloc[i]

            if data["Week"].iloc[i] == "WildCard":
                data["Week"].iloc[i] = 19
            if data["Week"].iloc[i] == "Division":
                data["Week"].iloc[i] = 20
            if data["Week"].iloc[i] == "ConfChamp":
                data["Week"].iloc[i] = 21
            if data["Week"].iloc[i] == "SuperBowl":
                data["Week"].iloc[i] = 22

        data = data[(data['Date'] != "Playoffs") & (data['Week'] != "Week")]
        data.to_csv(f"Data/NFL_SCHEDULE_{season}.csv", index=False)

if __name__ == '__main__':

    print("Start Processing Every Week")

    full_start = time.time()

    for season in [2025]:
        createNflScheduleData(season)

        url = f'https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.csv'

        data = pd.read_csv(url, low_memory=True)

        for week in range(9,10):

            print("Adjusting Team Stats...")

            start = time.time()

            directory_path = f"Team Stats/{season}/{week-1}"

            # Check if the directory already exists
            if not os.path.exists(directory_path):
                # Create the directory if it doesn't exist
                os.makedirs(directory_path)
                print(f"Directory '{directory_path}' created successfully.")
            else:
                print(f"Directory '{directory_path}' already exists.")


            directory_path = f"Player Stats/{season}/{week-1}"

            # Check if the directory already exists
            if not os.path.exists(directory_path):
                # Create the directory if it doesn't exist
                os.makedirs(directory_path)
                print(f"Directory '{directory_path}' created successfully.")
            else:
                print(f"Directory '{directory_path}' already exists.")

            data = data[data['side_of_field'].notna()]

            net_stats, net_def_stats, net_off_stats,num_of_off_plays = Adj_Pass_Run_Net(data, "net", season=season, week=week)
            print("Net Done")
            pass_def_stats, pass_off_stats = Adj_Pass_Run_Net(data, "pass", season=season, week=week)
            print("Pass Done")
            run_def_stats, run_off_stats = Adj_Pass_Run_Net(data, "run", season=season, week=week)
            print("Run Done")

            pd.DataFrame([net_stats]).to_csv(f"Team Stats/{season}/{week-1}/Net_Ratings.csv", index=False)
            pd.DataFrame([net_def_stats]).to_csv(f"Team Stats/{season}/{week-1}/Net_Def_Ratings.csv", index=False)
            pd.DataFrame([net_off_stats]).to_csv(f"Team Stats/{season}/{week-1}/Net_Off_Ratings.csv", index=False)

            pd.DataFrame([pass_def_stats]).to_csv(f"Team Stats/{season}/{week-1}/Pass_Def_Ratings.csv", index=False)
            pd.DataFrame([pass_off_stats]).to_csv(f"Team Stats/{season}/{week-1}/Pass_Off_Ratings.csv", index=False)

            pd.DataFrame([run_def_stats]).to_csv(f"Team Stats/{season}/{week-1}/Run_Def_Ratings.csv", index=False)
            pd.DataFrame([run_off_stats]).to_csv(f"Team Stats/{season}/{week-1}/Run_Off_Ratings.csv", index=False)

            end = time.time()

            print("Adjusting Team Stats Complete!")

            print("Start Adjusting Player Stats")

            s = time.time()

            Player_Stats(num_of_off_plays,pass_def_stats,run_def_stats,week=week,season=season)

            print("Adjusting Player Stats Complete!")

            print(f"Player Adj Time: {time.time()-s}")


#
    #     print(f"Total Time: {end - start}")
    #
    #     qbs = pd.DataFrame(columns=["QB Name","GP","Total Adj EPA", "Adj EPA Per Touch", "Adj EPA Per Play"])
    #
    #     print("start QB's:")
    #
    #     weekly_data = data[(data["week"] < week)]
    #
    # start = time.time()
    #
    #
    # for qb in weekly_data["passer_player_name"].unique():
    #     if pd.isna(qb):
    #         continue
    #     if weekly_data["passer_player_name"].value_counts()[qb] < 5 * week:
    #         continue
    #     else:
    #         total, ppp, pp, gp = Qb_epa(qb, weekly_data, pass_def_stats, run_def_stats)
    #
    #         qbs.loc[len(qbs.index)] = [qb,gp, total, ppp, pp]
    #
    # qbs = qbs.sort_values("Adj EPA Per Play", ascending=False)
    # qbs.to_csv(f"Player Stats/{season}/{week-1}/qbs.csv", index=False)
    #
    # end = time.time()
    #
    # print(f"Total Time: {end - start}")
    #
    # pos_players = pd.DataFrame(
    #     columns=["Name","GP","Total Adj EPA", "Adj EPA Per Rush", "Adj EPA Per Reception", "Adj EPA Per Touch",
    #              "Adj EPA Per Play"])
    #
    # print("start position players:")
    # start = time.time()
    #
    # all_players = (list(weekly_data["receiver_player_name"].unique()) + list(weekly_data["rusher_player_name"].unique()))
    #
    # all_players_to_rush_rec = []
    #
    # qb_names = pd.read_csv(f"Player Stats/{season}/{week-1}/qbs.csv")["QB Name"].tolist()
    #
    # for p in all_players:
    #     if p not in qb_names and not pd.isna(p) and p not in all_players_to_rush_rec:
    #         all_players_to_rush_rec.append(p)
    #
    # for player in all_players_to_rush_rec:
    #
    #     total_touches = 0
    #     if pd.isna(player):
    #         continue
    #
    #     try:
    #         total_touches += weekly_data["receiver_player_name"].value_counts()[player]
    #     except:
    #         total_touches += 0
    #
    #     try:
    #         total_touches += weekly_data["rusher_player_name"].value_counts()[player]
    #     except:
    #         total_touches += 0
    #
    #     if total_touches < 3 * week:
    #         continue
    #
    #     else:
    #         total, prush,prep, pt, pp, gp = Rb_epa(player, data, pass_def_stats, run_def_stats)
    #         pos_players.loc[len(pos_players.index)] = [player,gp,total, prush, prep, pt, pp]
    #
    # pos_players = pos_players.sort_values("Adj EPA Per Play", ascending=False)
    #
    # pos_players.to_csv(f"Player Stats/{season}/pos_players.csv", index=False)
    # end = time.time()
    #
    # print(f"Total Time: {end - start}")

# full_end = time.time()
#
# print(f"Total Time To Update Every Week: {full_end - full_start}")

# hfa = hfa(season=2023,weeks_played=5)
# print(hfa)
#
#
# def CalcWinner(home, away, home_net, away_net, hfa):
#     if home_net + hfa > away_net:
#         print(home)
#     else:
#         print(away)
#
#
# home_team = "TB"
# away_team = "KC"
#
# home_net = pd.read_csv(f"Team Stats/{season}/Net_Ratings.csv")[home_team].iloc[0]
# away_net = pd.read_csv(f"Team Stats/{season}/Net_Ratings.csv")[away_team].iloc[0]
#
# CalcWinner(home_team, away_team, home_net, away_net, hfa)
#
# print(f"{home_team}: {home_net}  {away_team}: {away_net}")
#
# import scipy.stats as st
# import math
#
# home = home_net
# away = away_net
# homev = teamVarPP(pd.read_csv(f"Data/play_by_play_{season}.csv", low_memory=False), home_team,
#                   weeks_played=week,season=season)
# awayv = teamVarPP(pd.read_csv(f"Data/play_by_play_{season}.csv", low_memory=False), away_team,
#                   weeks_played=week,season=season)
# mean = home - away
# sd = math.sqrt((homev + awayv))
# z = (0 - mean) / sd
# htwp = (1 - st.norm.cdf(z))
# atwp = 1 - htwp
#
# print(f"{home_team}: {round(htwp, 2) * 100}  {away_team}: {round(atwp, 2) * 100}")
