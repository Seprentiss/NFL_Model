import os
import pandas as pd
import numpy as np
import dash
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import numpy as np
from dash import html, dcc
import os
import glob

player_season = '2025'
player_week = '20'
ratings_season = '2025'
ratings_week = '20'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_master_predictions(folder_path, file_type="csv"):
    """
    Reads all weekly prediction files in a folder and combines them into a single master file.

    Parameters:
        folder_path (str): Path to the folder containing the weekly prediction files.
        file_type (str): "csv" (default) or "excel" depending on your file type.

    Returns:
        pd.DataFrame: The combined master DataFrame.
    """
    # Pattern to match all your weekly prediction files
    file_pattern = os.path.join(folder_path, f"Week_*_Predictions_Full_Season.{file_type}")

    # List all files matching the pattern
    all_files = glob.glob(file_pattern)

    # Sort files by week number
    all_files.sort(key=lambda x: int(x.split('Week_')[1].split('_')[0]))

    # Read and concatenate all files
    if file_type == "csv":
        df_list = [pd.read_csv(f) for f in all_files]
        master_df = pd.concat(df_list, ignore_index=True)
        master_df.to_csv(os.path.join(folder_path, "Master_Predictions_Full_Season.csv"), index=False)
    elif file_type in ["xls", "xlsx", "excel"]:
        df_list = [pd.read_excel(f) for f in all_files]
        master_df = pd.concat(df_list, ignore_index=True)
        master_df.to_excel(os.path.join(folder_path, "Master_Predictions_Full_Season.xlsx"), index=False)
    else:
        raise ValueError("file_type must be 'csv' or 'excel'")

    print(f"Master file created with {len(master_df)} rows.")
    return master_df

create_master_predictions("2025_Weekly_Predictions", file_type="csv")
# ---------------------------
# Config
# ---------------------------
CSV_PATH = os.environ.get(
    "PREDICTIONS_CSV",
    os.path.join(BASE_DIR, f"{ratings_season}_Weekly_Predictions", f"Master_Predictions_Full_Season.csv")
)
TITLE = "Game Predictions Dashboard"
THEME = dbc.themes.DARKLY


# ---------------------------
# Data Load + Prep
# ---------------------------
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"CSV not found at '{CSV_PATH}'. Place the file next to app.py or set PREDICTIONS_CSV env var."
    )

df = pd.read_csv(CSV_PATH)
df.columns = [c.strip() for c in df.columns]

# Ensure EV is numeric
if df["Expected Value (%)"].dtype == object:
    df["Expected Value (%)"] = (
        df["Expected Value (%)"].astype(str).str.replace('%', '', regex=False)
    )
    df["Expected Value (%)"] = pd.to_numeric(df["Expected Value (%)"], errors='coerce')

df["EV_Positive"] = df["Expected Value (%)"].fillna(0) > 0
df["Spread Edge"] = abs(df["Home Team Projected Spread"]) - abs(df["Home Team Vegas Spread"])

df["Win% Differential"] = (df["Home Win %"] - df["Away Win %"]).abs()

qb_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats",f"{player_season}",f"{player_week}","qb_data.csv"))
rb_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats",f"{player_season}",f"{player_week}","rb_data.csv"))
wr_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats",f"{player_season}",f"{player_week}","wr_data.csv"))
te_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats",f"{player_season}",f"{player_week}","te_data.csv"))

# def add_WAR(df):
#     # Calculate WAR based on top 32 players at this position
#     top32_avg_epa = df['EPA per Play ( all offense )'].nsmallest(len(df) // 2).mean()
#     df['WAR'] = (df['EPA per Play ( all offense )'] * 33.146 + 8.3641) - (top32_avg_epa * 33.146 + 8.3641)
#     return df
#
# qb_df = add_WAR(qb_df)
# rb_df = add_WAR(rb_df)
# wr_df = add_WAR(wr_df)
# te_df = add_WAR(te_df)

def add_WAR_global(df, all_players, total_wins, cap_share=0.35, position_col="POS"):
    """
    Calculate Wins Above Replacement (WAR), scaled by position.

    - Players are only compared to others at their position
    - WAR shares by position are based on abs(EPA) + avg EPA per player
    - QB+RB+WR+TE combined capped at `cap_share` (default 40%)
    - Unused share is left unused
    """

    df = df.copy()
    all_players = all_players.copy()

    # --- Estimate plays ---
    df['est_plays'] = df['Total EPA'] / df['EPA per Play ( all offense )']
    df['est_plays'] = df['est_plays'].replace([np.inf, -np.inf], np.nan).fillna(0)

    all_players['est_plays'] = all_players['Total EPA'] / all_players['EPA per Play ( all offense )']
    all_players['est_plays'] = all_players['est_plays'].replace([np.inf, -np.inf], np.nan).fillna(0)

    # --- Wins per full-time starter ---
    df['wins_per_fulltime'] = df['EPA per Play ( all offense )'] * 33.146 + 8.3641
    baseline_plays = df['est_plays'].mean()
    df['wins_scaled'] = df['wins_per_fulltime'] * (df['est_plays'] / baseline_plays)

    # --- Replacement level within this position (bottom 20%) ---
    pos = df[position_col].iloc[0]
    pos_players = all_players[all_players[position_col] == pos]

    repl_thr = pos_players['EPA per Play ( all offense )'].quantile(0.20)
    repl_wins = (repl_thr * 33.146 + 8.3641)

    df['replacement_level'] = repl_wins * (df['est_plays'] / baseline_plays)
    df['WAR_raw'] = df['wins_scaled'] - df['replacement_level']

    # --- Compute positional weights ---
    pos_abs_epa = all_players.groupby(position_col)['Total EPA'].apply(lambda x: x.abs().sum())
    pos_avg_epa = all_players.groupby(position_col)['Total EPA'].apply(lambda x: x.abs().mean())
    pos_weights = pos_abs_epa * pos_avg_epa
    pos_share = pos_weights / pos_weights.sum()


    # --- Cap skill positions at `cap_share` ---
    skill_positions = ["QB", "RB", "WR", "TE"]
    skill_total_share = pos_share.loc[pos_share.index.intersection(skill_positions)].sum()

    if skill_total_share > cap_share:
        scale_factor = cap_share / skill_total_share
        pos_share.loc[skill_positions] *= scale_factor


    # print("\nPositional Weights (share of WAR allocation):")
    # for p, w in pos_share.items():
    #     print(f"{p}: {w:.3f}  ({w * 100:.1f}%)")

    # --- Allocate WAR budget to this position ---
    pos_share_value = pos_share.get(pos, 0)
    target_wins_pos = total_wins * pos_share_value

    raw_sum = df['WAR_raw'].sum()
    scaling_factor = target_wins_pos / raw_sum if raw_sum > 0 else 0


    df['WAR'] = df['WAR_raw'] * scaling_factor

    return df
# --- Usage ---
all_players = pd.concat([qb_df, rb_df, wr_df, te_df], ignore_index=True)

schedule_data = pd.read_csv(f"Data/NFL_SCHEDULE_{player_season}.csv")
total_wins = len(schedule_data[schedule_data["Week"] <= int(player_week)])
qb_df = add_WAR_global(qb_df, all_players,total_wins)
rb_df = add_WAR_global(rb_df, all_players,total_wins)
wr_df = add_WAR_global(wr_df, all_players,total_wins)
te_df = add_WAR_global(te_df, all_players,total_wins)



# Combine all positions
all_players = pd.concat([qb_df, rb_df, wr_df, te_df], ignore_index=True)


def add_PAAS(df, all_players, position_col="POS", starters_per_pos=None):
    """
    Calculate Points Above Average Starter (PAAS) using total EPA and EPA per offensive play,
    relative to a positional starter baseline.

    df: DataFrame for a single position
    all_players: DataFrame of all players across positions
    position_col: column name with position labels
    starters_per_pos: dict, e.g. {"QB": 32, "RB": 64, "WR": 64, "TE": 32}
    """
    df = df.copy()
    all_players = all_players.copy()

    # --- Estimate plays ---
    all_players['est_plays'] = all_players['Total EPA'] / all_players['EPA per Play ( all offense )']
    df['est_plays'] = df['Total EPA'] / df['EPA per Play ( all offense )']

    # Clean up infinities / missing
    all_players['est_plays'] = all_players['est_plays'].replace([float('inf'), -float('inf')], 0).fillna(0)
    df['est_plays'] = df['est_plays'].replace([float('inf'), -float('inf')], 0).fillna(0)

    # --- Positional baseline ---
    pos = df[position_col].iloc[0]  # assume one position per df
    pos_players = all_players[all_players[position_col] == pos]

    if starters_per_pos is not None and pos in starters_per_pos:
        n_starters = starters_per_pos[pos]
    else:
        n_starters = 32  # default if not provided

    # Baseline EPA per play of starter-level player at this position
    baseline_epa_per_play = pos_players['EPA per Play ( all offense )'].nlargest(n_starters).mean()

    # Baseline total contribution = baseline EPA per play × estimated plays
    baseline_total_epa = baseline_epa_per_play * df['est_plays'].mean()

    # Player total contribution = EPA per play × estimated plays
    df['player_total_epa'] = df['EPA per Play ( all offense )'] * df['est_plays']

    # PAAS = value above positional starter
    df['PAAS'] = df['player_total_epa'] - baseline_total_epa

    return df

# Define starter counts per position
starters = {"QB": 32, "RB": 64, "WR": 64, "TE": 32}

qb_df = add_PAAS(qb_df, all_players, starters_per_pos=starters)
rb_df = add_PAAS(rb_df, all_players, starters_per_pos=starters)
wr_df = add_PAAS(wr_df, all_players, starters_per_pos=starters)
te_df = add_PAAS(te_df, all_players, starters_per_pos=starters)

# Example mock player data
players = {
    "QB": [
        {"name": "Patrick Mahomes", "team": "KC", "rank": 1, "points": 350},
        {"name": "Josh Allen", "team": "BUF", "rank": 2, "points": 340},
    ],
    "RB": [
        {"name": "Christian McCaffrey", "team": "SF", "rank": 1, "points": 300},
        {"name": "Bijan Robinson", "team": "ATL", "rank": 2, "points": 270},
    ],
    "WR": [
        {"name": "Justin Jefferson", "team": "MIN", "rank": 1, "points": 320},
        {"name": "Ja'Marr Chase", "team": "CIN", "rank": 2, "points": 310},
    ],
    "TE": [
        {"name": "Travis Kelce", "team": "KC", "rank": 1, "points": 260},
        {"name": "Mark Andrews", "team": "BAL", "rank": 2, "points": 220},
    ]
}


def player_card(player):
    """Create a styled player card"""
    return dbc.Card(
        dbc.CardBody([
            html.H4(f"{player['name']} ({player['team']})", className="text-lg font-bold"),
            html.P(f"Rank: {player['rank']}"),
            html.P(f"Projected Points: {player['points']}"),
        ]),
        className="m-2 shadow-sm rounded-2xl border"
    )

# Function to create a player card/pill
def create_player_card(player):
    return dbc.Card(
        dbc.Row(
            [
                dbc.Col(
                    html.Div([
                        html.H5(player['Player'], className="mb-1"),
                        html.P(player['TM'], className="mb-0"),
                        html.P(f"GP: {player['GP']}", className="mb-0")
                    ]),
                    width=6
                ),
                dbc.Col(
                    html.Div([
                        html.P(f"Total EPA: {round(player['Total EPA'],2)}", className="mb-1"),
                        html.P(f"EPA per Play: {round(player['EPA per Play ( all plays contributed )'],2)}", className="mb-1"),
                        html.P(f"WAR: {player['WAR']:.2f}", className="mb-1"),
                        html.P(f"PAAS: {player['PAAS']:.2f}", className="mb-1")
                    ]),
                    width=6,
                    style={"textAlign": "right"}
                ),

            ],
            className="g-0 align-items-center"
        ),
        className="mb-2 p-2",
        style={"borderRadius": "15px", "border": "1px solid #ccc"}
    )

# Create cards for each position
qb_cards = [create_player_card(row) for _, row in qb_df.iterrows()]
rb_cards = [create_player_card(row) for _, row in rb_df.iterrows()]
wr_cards = [create_player_card(row) for _, row in wr_df.iterrows()]
te_cards = [create_player_card(row) for _, row in te_df.iterrows()]


# Create Tabs
from dash import html, dcc

player_tabs = html.Div([

    dcc.Tabs(
        id="position-tabs",
        value="QB",  # default selected tab
        children=[
            dcc.Tab(
                label="QB",
                value="QB",
                style={
                    "flex": "1",
                    "textAlign": "center",
                    "backgroundColor": "#222",
                    "color": "#ddd",
                    "padding": "10px 0",
                    "fontSize": "16px",
                    "fontWeight": "bold",
                    "border": "none"
                },
                selected_style={
                    "backgroundColor": "#444",
                    "color": "#fff"
                }
            ),
            dcc.Tab(
                label="RB",
                value="RB",
                style={
                    "flex": "1",
                    "textAlign": "center",
                    "backgroundColor": "#222",
                    "color": "#ddd",
                    "padding": "10px 0",
                    "fontSize": "16px",
                    "fontWeight": "bold",
                    "border": "none"
                },
                selected_style={
                    "backgroundColor": "#444",
                    "color": "#fff"
                }
            ),
            dcc.Tab(
                label="WR",
                value="WR",
                style={
                    "flex": "1",
                    "textAlign": "center",
                    "backgroundColor": "#222",
                    "color": "#ddd",
                    "padding": "10px 0",
                    "fontSize": "16px",
                    "fontWeight": "bold",
                    "border": "none"
                },
                selected_style={
                    "backgroundColor": "#444",
                    "color": "#fff"
                }
            ),
            dcc.Tab(
                label="TE",
                value="TE",
                style={
                    "flex": "1",
                    "textAlign": "center",
                    "backgroundColor": "#222",
                    "color": "#ddd",
                    "padding": "10px 0",
                    "fontSize": "16px",
                    "fontWeight": "bold",
                    "border": "none"
                },
                selected_style={
                    "backgroundColor": "#444",
                    "color": "#fff"
                }
            ),
        ],
        style={
            "display": "flex",
            "borderRadius": "12px",
            "overflow": "hidden",
            "border": "1px solid #444",
            "marginBottom": "1rem",
            "backgroundColor": "#222"
        }
    ),

    html.Div(id="tab-content")
])






layout = html.Div(
    [
        html.H2("Player Rankings", className="text-2xl font-bold mb-4"),
        dcc.Tabs(
            id="position-tabs",
            value="QB",
            children=[
                dcc.Tab(label=pos, value=pos) for pos in players.keys()
            ],
        ),
        html.Div(id="player-cards-container", className="grid grid-cols-2 gap-4 mt-4"),
    ]
)

# Example NFL team colors (primary colors)
team_colors = {
    "ARI": "#97233F",  # Cardinals
    "ATL": "#A71930",  # Falcons
    "BAL": "#241773",  # Ravens
    "BUF": "#00338D",  # Bills
    "CAR": "#0085CA",  # Panthers
    "CHI": "#0B162A",  # Bears
    "CIN": "#FB4F14",  # Bengals
    "CLE": "#311D00",  # Browns
    "DAL": "#041E42",  # Cowboys
    "DEN": "#FB4F14",  # Broncos
    "DET": "#0076B6",  # Lions
    "GB":  "#203731",  # Packers
    "HOU": "#03202F",  # Texans
    "IND": "#002C5F",  # Colts
    "JAX": "#006778",  # Jaguars
    "KC":  "#E31837",  # Chiefs
    "LV":  "#000000",  # Raiders
    "LAC": "#0080C6",  # Chargers
    "LA": "#866D4B",  # Rams
    "MIA": "#008E97",  # Dolphins
    "MIN": "#4F2683",  # Vikings
    "NE":  "#002244",  # Patriots
    "NO":  "#D3BC8D",  # Saints
    "NYG": "#0B2265",  # Giants
    "NYJ": "#125740",  # Jets
    "PHI": "#004C54",  # Eagles
    "PIT": "#FFB612",  # Steelers
    "SF":  "#AA0000",  # 49ers
    "SEA": "#002244",  # Seahawks
    "TB":  "#D50A0A",  # Buccaneers
    "TEN": "#4B92DB",  # Titans
    "WAS": "#773141",  # Commanders
}


def rank_to_color(rank, max_rank=32):
    """Convert rank 1..max_rank to a color from bright green to dark red."""
    # RGB for bright green (#2ECC40) to dark red (#8B0000)
    green_rgb = (46, 204, 64)
    red_rgb = (139, 0, 0)

    ratio = (rank - 1) / (max_rank - 1)  # 0 = rank 1, 1 = rank 32
    r = int(green_rgb[0] + (red_rgb[0] - green_rgb[0]) * ratio)
    g = int(green_rgb[1] + (red_rgb[1] - green_rgb[1]) * ratio)
    b = int(green_rgb[2] + (red_rgb[2] - green_rgb[2]) * ratio)

    return f"rgba({r},{g},{b},0.7)"  # semi-transparent
def hex_to_rgba(hex_color, alpha=0.2):
    """Convert hex color to rgba string with given alpha."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def make_strength_chart(home_mean, home_var, away_mean, away_var, hfa, home_team, away_team):
    x = np.linspace(min(home_mean, away_mean) - .3, max(home_mean, away_mean) + .3, 200)

    # Home with HFA
    home_y = (1 / np.sqrt(2 * np.pi * home_var)) * np.exp(-((x - (home_mean + hfa)) ** 2) / (2 * home_var))
    away_y = (1 / np.sqrt(2 * np.pi * away_var)) * np.exp(-((x - away_mean) ** 2) / (2 * away_var))

    # Team colors from dictionary
    home_color = team_colors.get(home_team, "#AAAAAA")
    away_color = team_colors.get(away_team, "#888888")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x, y=home_y,
        mode="lines",
        name=home_team,
        line=dict(color=home_color, width=3),
        fill="tozeroy",
        fillcolor=hex_to_rgba(home_color, alpha=0.2)
    ))
    fig.add_trace(go.Scatter(
        x=x, y=away_y,
        mode="lines",
        name=away_team,
        line=dict(color=away_color, width=3),
        fill="tozeroy",
        fillcolor=hex_to_rgba(away_color, alpha=0.2)
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=160,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="h",
            y=-0.25,
            x=0.5,
            xanchor="center",
            font=dict(color="#AAAAAA", size=10)
        ),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )

    return dcc.Graph(
        figure=fig,
        config={"displayModeBar": False},
        style={"width": "100%", "height": '120px'}
    )




def matchup_row(r):
    wk = int(r["Week"]) if not pd.isna(r["Week"]) else "?"
    return f"{r['Away Team']} @ {r['Home Team']} (Wk {wk})"
df["Matchup"] = df.apply(matchup_row, axis=1)

weeks = sorted(df["Week"].dropna().unique().tolist())

all_teams = sorted(pd.unique(df[["Home Team", "Away Team"]].values.ravel('K')))

# ---------------------------
# App + Layout
# ---------------------------
app = Dash(__name__, external_stylesheets=[THEME], suppress_callback_exceptions=True)
server = app.server
app.title = TITLE

# Filters card (only used on first page)
controls_card = dbc.Card(
    [
        dbc.CardHeader(
            html.H5("Filters", className="mb-0"),
            style={"backgroundColor": "#001F3F", "color": "white"}
        ),
        dbc.CardBody([
            # Top row: Week, Team, Sort By
            dbc.Row([
                dbc.Col([
                    dbc.Label("Week", style={"color": "#AAAAAA"}),
                    dcc.Dropdown(
                        id="week-dd",
                        options=[{"label": int(w), "value": int(w)} for w in weeks],
                        value=weeks[len(weeks)-1] if weeks else None,
                        clearable=False,
                        style={"backgroundColor": "white", "color": "#013080"}
                    ),
                ], md=4),
                dbc.Col([
                    dbc.Label("Team Filter", style={"color": "#AAAAAA"}),
                    dcc.Dropdown(
                        id="team-dd",
                        options=[{"label": t, "value": t} for t in all_teams],
                        value=None,
                        multi=True,
                        placeholder="Start typing a team...",
                        style={"backgroundColor": "white", "color": "#013080"}
                    ),
                ], md=4),
                dbc.Col([
                    dbc.Label("Sort by", style={"color": "#AAAAAA"}),
                    dcc.Dropdown(
                        id="sort-dd",
                        options=[
                            {"label": "Expected Value (%)", "value": "ev"},
                            {"label": "Win % Differential", "value": "win_diff"},
                        ],
                        value="ev",
                        clearable=False,
                        style={"backgroundColor": "white", "color": "#013080","maxHeight": "30px" }
                    ),
                ], md=4),
            ]),
            # # Bottom row: EV toggle on far right
            # dbc.Row([
            #     dbc.Col([
            #         dbc.Checklist(
            #             id="ev-only-toggle",
            #             options=[{"label": "Show only EV > 0 games", "value": 1}],
            #             value=[],
            #             switch=True,
            #             style={"color": "#AAAAAA"}  # softer gray label
            #         )
            #     ], width="auto", className="ms-auto"),  # pushes to far right
            # ], className="mt-2")
        ],style={"minHeight": "120px"} )
    ],
    className="shadow-sm",
    style={"backgroundColor": "#1A1A1A", "border": "1px solid #0074D9"}
)

# Containers for pages
game_cards_container = html.Div(id="game-cards", className="grid gap-3",
                                style={"maxHeight": "400px", "overflowY": "scroll",
                                       "padding": "10px", "border": "1px solid #444", "borderRadius": "5px"})

power_rankings_card = dbc.Card([
    dbc.CardHeader(
        html.H5("Power Rankings", className="mb-0 text-light"),
        style={"backgroundColor": "#001F3F"}  # dark blue header
    ),
    dbc.CardBody(
        dash_table.DataTable(
            id="power-rankings-table",
            columns=[
                {"name": "Rank", "id": "Rank", "type": "numeric"},
                {"name": "Team", "id": "Team"},
                {"name": "Score", "id": "Score", "type": "numeric", "format": {"specifier": ".4f"}},
                {"name": "Wins", "id": "Wins", "type": "numeric", "format": {"specifier": ".2f"}},
            ],
            style_table={
                "overflowX": "auto",
                "border": "1px solid #444",
                "borderRadius": "8px",
            },
            style_cell={
                "backgroundColor": "#1a1a1a",
                "color": "white",
                "textAlign": "center",
                "padding": "6px",
                "fontFamily": "Inter, system-ui, sans-serif",
                "fontSize": 13,
            },
            style_header={
                "backgroundColor": "#001F3F",
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "center",
                "fontSize": 14,
            },
            style_data_conditional=[
                # Top 3 teams highlight
                {"if": {"filter_query": "{Rank} <= 5"},
                 "backgroundColor": "#FFD700", "color": "gold", "fontWeight": "bold"},
                # Mid teams
                {"if": {"filter_query": "{Rank} > 5 && {Rank} <= 27"},
                 "backgroundColor": "#2a2a2a", "color": "white"},
                # Low teams
                {"if": {"filter_query": "{Rank} > 27"},
                 "backgroundColor": "#111", "color": "red"},

                # Stripe effect
                {"if": {"row_index": "odd"}, "backgroundColor": "#1a1a1a"},
                {"if": {"row_index": "even"}, "backgroundColor": "#111"},
            ],
            sort_action="native",
            page_size=32,
        )
    )
], className="shadow-sm bg-dark text-light")

power_rankings_controls_card = dbc.Card(
    [
        dbc.CardHeader(
            html.H5("Filters", className="mb-0 text-light"),
            style={"backgroundColor": "#001F3F"}
        ),
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label("Week", style={"color": "#AAAAAA"}),
                            dcc.Dropdown(
                                id="power-week-dd",
                                options=[{"label": int(w), "value": int(w)} for w in weeks],
                                value=weeks[len(weeks)-1] if weeks else None,
                                multi=False,
                                clearable=False,
                                placeholder="Filter by week...",
                                style={"backgroundColor": "white", "color": "#013080"}
                            ),
                        ],
                        width=6
                    ),
                    # Team filter
                    dbc.Col(
                        [
                            dbc.Label("Team Filter", style={"color": "#AAAAAA"}),
                            dcc.Dropdown(
                                id="power-team-dd",
                                options=[{"label": t, "value": t} for t in all_teams],
                                value=None,
                                multi=True,
                                placeholder="Filter by team...",
                                style={"backgroundColor": "white", "color": "#013080"}
                            ),
                        ],
                        width=6
                    ),
                ],
                className="g-3"
            )
        )
    ],
    className="shadow-sm bg-dark text-light"
)


# ---------------------------
# Page Layouts
# ---------------------------
# Navigation bar (tab-like) for pages
def navbar():
    return dbc.Nav(
        [
            dbc.NavLink("Game Predictions", href="/", active="exact", id="nav-home"),
            dbc.NavLink("Power Rankings", href="/power-rankings", active="exact", id="nav-power"),
            dbc.NavLink("Player Rankings", href="/player-rankings", active="exact", id="nav-player"),
            dbc.NavLink("Glossary", href="/glossary", active="exact", id="nav-glossary"),
        ],
        pills=True,  # makes it look like tabs
        justified=True,
        className="mb-4",
    )

# Example page layouts with navbar on top
home_page = dbc.Container([
    html.H2(TITLE, className="mt-3 mb-2 text-light"),
    navbar(),  # <--- navbar here
    controls_card,
    html.Hr(style={"borderColor": "#444"}),
    dbc.Row([
        dbc.Col(html.H4("Game Predictions", className="mt-2 text-light"), align="center"),
        dbc.Col(
            dbc.Checklist(
                id="ev-only-toggle",
                options=[{"label": "Show only EV > 0 games", "value": 1}],
                value=[],
                switch=True,
                style={"color": "#AAAAAA"}
            ),
            width="auto",
            align="center",
            className="ms-auto"
        ),
    ]),
    game_cards_container,
], fluid=True, style={"backgroundColor": "#111"})

power_page = dbc.Container([
    html.H2("Power Rankings", className="mt-3 mb-2 text-light"),
    navbar(),
    power_rankings_controls_card,  # filter card on top
    html.Br(),
    html.Div(
        id="power-rankings-cards",
        style={
            "maxHeight": "500px",
            "overflowY": "auto",
            "padding": "10px",
            "backgroundColor": "#1A1A1A",
            "border": "1px solid #0074D9",
            "borderRadius": "5px"
        }
    )
], fluid=True, style={"backgroundColor": "#111"})

player_page = dbc.Container([
    html.H2("Player Rankings", className="mt-3 mb-2 text-light"),
    navbar(),  # <--- navbar here
    player_tabs,
    # layout,
], fluid=True, style={"backgroundColor": "#111"})

glossary_page = dbc.Container([
    html.H2("Glossary", className="mt-3 mb-2 text-light"),
    navbar(),

    # Home Page
    dbc.Card([
        dbc.CardHeader("Home Page", className="text-light bg-primary"),
        dbc.CardBody([
            html.P("The Home Page displays weekly game predictions, allowing users to filter by week or team and sort results. It is designed to identify betting edges and highlight where the model’s projections differ from sportsbook lines."),
            html.Ul([
                html.Li([
                    html.B("Expected Value (%): "),
                    "Represents the long-term profitability of a bet.",
                    html.Ul([
                        html.Li("Calculated by comparing the model’s win probability to the implied probability from sportsbook odds.")
                    ])
                ]),
                html.Li([
                    html.B("Spread Edge: "),
                    "Measures how much the model’s projected point spread differs from the Vegas line.",
                    html.Ul([
                        html.Li("Positive values suggest value on the model’s favored team.")
                    ])
                ]),
                html.Li([
                    html.B("Win% Differential: "),
                    "The gap between the home and away team’s win probabilities.",
                    html.Ul([
                        html.Li("Shows how evenly matched a game is.")
                    ])
                ]),
                html.Li([
                    html.B("Matchup Chart: "),
                    "Visual representation of team strength distributions, adjusted for home-field advantage.",
                    html.Ul([
                        html.Li("Uses probability curves to show where each team’s outcomes overlap.")
                    ])
                ])
            ])
        ])
    ], className="mb-3"),

    # Power Rankings Page
    dbc.Card([
        dbc.CardHeader("Power Rankings Page", className="text-light bg-primary"),
        dbc.CardBody([
            html.P("The Power Rankings page ranks teams based on efficiency metrics rather than just win-loss records. It reflects true team strength across offense, defense, and schedule difficulty."),
            html.Ul([
                html.Li([
                    html.B("Score: "),
                    "Model-based rating derived from performance and underlying efficiency. Accounts for current results, strength of schedule, and expected performance.",
                    html.Ul([
                        html.Li("Higher scores = stronger teams. An average team would be 0.")
                    ])
                ]),
                html.Li([
                    html.B("Wins: "),
                    "Projected season win totals based on Team Score."
                ])
            ])
        ])
    ], className="mb-3"),

    # Player Rankings Page
    dbc.Card([
        dbc.CardHeader("Player Rankings Page", className="text-light bg-primary"),
        dbc.CardBody([
            html.P("The Player Rankings page evaluates quarterbacks, running backs, wide receivers, and tight ends using advanced efficiency metrics. Rankings highlight which players provide the most value to their teams."),
            html.Ul([
                html.Li([
                    html.B("EPA per Play: "),
                    "Average expected points added per play."
                ]),
                html.Li([
                    html.B("Total EPA: "),
                    "The total contribution of a player in terms of expected points.",
                    html.Ul([
                        html.Li("Summed across all plays the player is involved in.")
                    ])
                ]),
                html.Li([
                    html.B("WAR (Wins Above Replacement): "),
                    "The number of wins a player adds compared to a replacement-level player at their position."
                ]),
                html.Li([
                    html.B("PAAS (Points Above Average Starter): "),
                    "Measures how much better (or worse) a player performs compared to an average starter at the same position in terms of Total EPA."
                ])
            ])
        ])
    ], className="mb-3"),

], fluid=True, style={"backgroundColor": "#111"})





app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# ---------------------------
# Helpers
# ---------------------------
def apply_filters(frame, week, teams, ev_only):
    d = frame.copy()
    if week is None:
        max_week = d["Week"].max()
        d = d[d["Week"] == max_week]
    if week is not None:
        d = d[d["Week"] == week]
    if teams:
        teams_set = set(teams)
        d = d[(d["Home Team"].isin(teams_set)) | (d["Away Team"].isin(teams_set))]
    if ev_only:
        d = d[d["EV_Positive"]]
    return d

def make_game_card(row):
    ev = row["Expected Value (%)"]
    ev_team = row["Expected Value Team"]
    border_color = "success" if ev > 0 else "danger"

    return dbc.Card([
        dbc.CardHeader(html.Strong(f"{row['Away Team']} @ {row['Home Team']}")),
        dbc.CardBody([
            html.Div(
                style={"display": "flex", "alignItems": "center"},
                children=[
                    # Left side: EV info
                    html.Div(
                        [
                            # Top row: Home and Away Win % side by side
                            html.Div([
                                dbc.Badge(f"{row['Home Team']} Win %: {row['Home Win %']:.1f}%",
                                          color=team_colors.get(row["Home Team"]),className="me-1"
                                          ),
                                dbc.Badge(f"{row['Away Team']} Win %: {row['Away Win %']:.1f}%",
                                          color=team_colors.get(row["Away Team"]),className="me-1"
                                          ),
                            ], style={"display": "flex", "marginBottom": "8px"}),

                            # Bottom row: EV, Proj, Vegas, Edge
                            html.Div([
                                dbc.Badge(f"EV: {ev:.1f}% ({ev_team})", color="success" if ev > 0 else "danger",
                                         className="me-1"),
                                dbc.Badge(f"Model Home Team Spread Proj: {row['Home Team Projected Spread']:+.1f}", color="info",
                                          className="me-1"),
                                dbc.Badge(f"Vegas Home Team Spread: {row['Home Team Vegas Spread']:+.1f}", color="black",
                                          className="me-1"),
                                dbc.Badge(f"Home Team Spread Edge: {row['Spread Edge']:+.1f}", color="secondary",
                                          className="me-1"),
                            ], style={"display": "flex"})
                        ],
                        style={"flex": "1"}  # text takes remaining space
                    ),  # text takes remaining space

                    # Right side: Strength chart
                    html.Div(
                        make_strength_chart(
                            row["Home Team Str Mean"],
                            row["Home Team Str Var"],
                            row["Away Team Str Mean"],
                            row["Away Team Str Var"],
                            row["HFA"],
                            row["Home Team"],
                            row["Away Team"]
                        ),
                        style={"width": "35%", "minWidth": "120px", "height": "160px", "flexShrink": 0}
                    )
                ]
            )
        ])
    ], className=f"border-{border_color} mb-2")

def make_power_rankings_cards(power_df,week = None,filter_teams=None, sort_by="Rank"):
    pills = []
    if week is None:
        max_week = power_df["Week"].max()
        power_df = power_df[power_df["Week"] == max_week]
    if week is not None:
        power_df = power_df[power_df["Week"] == week]

    # Apply team filter
    if filter_teams:
        power_df = power_df[power_df["Team"].isin(filter_teams)]


    # Header row
    header_row = dbc.Row(
        [
            dbc.Col(html.Div("Rank", className="text-center fw-bold text-light"), width=3),
            dbc.Col(html.Div("Team", className="text-center fw-bold text-light"), width=3),
            dbc.Col(html.Div("Power Rating", className="text-center fw-bold text-light"), width=3),
            dbc.Col(html.Div("Wins", className="text-center fw-bold text-light"), width=3),
        ],
        className="mb-2 g-2"
    )
    pills.append(header_row)

    max_value = max(power_df["Score"].max(), power_df["Wins"].max(), 50)

    for _, row in power_df.iterrows():
        rank = int(row["Rank"])  # convert scalar to int
        rank_color = rank_to_color(rank)
        team_color = team_colors.get(row["Team"], "#AAAAAA")
        alpha_color = f"rgba({int(int(team_color[1:3],16))},{int(int(team_color[3:5],16))},{int(int(team_color[5:7],16))},0.4)"

        pill_row = dbc.Row(
            [
                # Rank pill
                dbc.Col(
                    html.Div(
                        str(int(row["Rank"])),
                        className="text-center fw-bold text-light p-1",
                        style={
                            "backgroundColor": rank_color,
                            "borderRadius": "12px"
                        }
                    ),
                    width=3
                ),
                # Team pill
                dbc.Col(
                    html.Div(
                        row["Team"],
                        className="text-center fw-bold text-light p-1",
                        style={
                            "backgroundColor": alpha_color,
                            "borderRadius": "12px"
                        }
                    ),
                    width=3
                ),
                # Score pill with fill
                dbc.Col(
                    html.Div(
                        className="text-center fw-bold text-light p-1",
                        style={
                            "position": "relative",
                            "height": "28px",
                            "borderRadius": "12px",
                            "backgroundColor": "#333",
                            "overflow": "hidden",
                        },
                        children=[
                            html.Div(
                                style={
                                    "position": "absolute",
                                    "left": 0,
                                    "top": 0,
                                    "height": "100%",
                                    "width": f"100%",
                                    "backgroundColor": "#333",
                                    "zIndex": 0,
                                }
                            ),
                            html.Span(
                                f"{row['Score']:.3f}",
                                style={"position": "relative", "zIndex": 1, "color": "white", "fontWeight": "bold"}
                            )
                        ]
                    ),
                    width=3
                ),
                # Wins pill with fill
                dbc.Col(
                    html.Div(
                        className="text-center fw-bold text-light p-1",
                        style={
                            "position": "relative",
                            "height": "28px",
                            "borderRadius": "12px",
                            "backgroundColor": "#333",
                            "overflow": "hidden",
                        },
                        children=[
                            html.Div(
                                style={
                                    "position": "absolute",
                                    "left": 0,
                                    "top": 0,
                                    "height": "100%",
                                    "width": f"100%",
                                    "backgroundColor": "#333",
                                    "zIndex": 0,
                                }
                            ),
                            html.Span(
                                f"{row['Wins']:.2f}",
                                style={"position": "relative", "zIndex": 1, "color": "white", "fontWeight": "bold"}
                            )
                        ]
                    ),
                    width=3
                ),
            ],
            className="mb-2 g-2 align-items-center"
        )

        pills.append(pill_row)

    return pills

# Function to create a player pill/card
def create_player_card(player):
    return dbc.Card(
        dbc.Row(
            [
                dbc.Col(
                    html.Div([
                        html.H5(player['Player'], className="mb-1"),
                        html.P(player['TM'], className="mb-0"),
                        html.P(f"GP: {player['GP']}", className="mb-0")
                    ]),
                    width=6
                ),
                dbc.Col(
                    html.Div([
                        html.P(f"Total EPA: {player['Total EPA']}", className="mb-1"),
                        html.P(f"EPA per Play: {player['EPA per Play ( all plays contributed )']}", className="mb-1"),
                        html.P(f"WAR: TBD", className="mb-1")  # You can calculate Wins Above Average QB if you have formula
                    ]),
                    width=6,
                    style={"textAlign": "right"}
                ),
            ],
            className="g-0 align-items-center"
        ),
        className="mb-2 p-2",
        style={"borderRadius": "15px", "border": "1px solid #ccc"}
    )


# ---------------------------
# Callbacks
# ---------------------------

@app.callback(
    Output("game-cards", "children"),
    Input("week-dd", "value"),
    Input("team-dd", "value"),
    Input("ev-only-toggle", "value"),
    Input("sort-dd", "value"),
)
def update_game_cards(week, teams, ev_only_toggle, sort_by):
    ev_only = 1 in (ev_only_toggle or [])
    filtered = apply_filters(df, week, teams, ev_only)

    # Sorting
    if sort_by == "ev":
        filtered = filtered.sort_values("Expected Value (%)", ascending=False)
    elif sort_by == "win_diff":
        filtered = filtered.sort_values("Win% Differential", ascending=False)

    return [make_game_card(r) for _, r in filtered.iterrows()]

@app.callback(
    Output("power-rankings-cards", "children"),
    Input("url", "pathname"),
    Input("power-week-dd","value"),
    Input("power-team-dd", "value"),
)
def update_power_cards(pathname, selected_week, selected_teams):
    if pathname != "/power-rankings":
        raise dash.exceptions.PreventUpdate

    # Recalculate power_df
    team_stats = {}

    for _, r in df.iterrows():
        for week, team, mean in [
            (r["Week"], r["Home Team"], r["Home Team Str Mean"]),
            (r["Week"], r["Away Team"], r["Away Team Str Mean"])
        ]:
            if team not in team_stats:
                team_stats[team] = {}
            if week not in team_stats[team]:
                team_stats[team][week] = {"total": 0, "count": 0}

            team_stats[team][week]["total"] += mean
            team_stats[team][week]["count"] += 1

    # Now build a DataFrame with week info
    records = []
    for team, weeks in team_stats.items():
        for week, stats in weeks.items():
            avg_score = stats["total"] / stats["count"]
            records.append({"Week": week, "Team": team, "Score": avg_score})

    power_df = pd.DataFrame(records)

    # Calculate rank and wins per week
    power_df = power_df.sort_values(["Week", "Score"], ascending=[True, False])
    power_df["Rank"] = power_df.groupby("Week")["Score"].rank(method="min", ascending=False).astype(int)
    power_df["Wins"] = power_df["Score"] * 33.146 + 8.3641

    # Optional: sort by week and then rank
    power_df = power_df.sort_values(["Week", "Rank"])

    if selected_week:
        power_df = power_df[power_df["Week"] == selected_week]
    # Apply team filter
    if selected_teams:
        power_df = power_df[power_df["Team"].isin(selected_teams)]

    # Return scrollable pills
    return html.Div(
        make_power_rankings_cards(power_df,selected_week),
        style={
            "maxHeight": "500px",
            "overflowY": "auto",
            "padding": "10px",
            "backgroundColor": "#1A1A1A",
            "border": "1px solid #0074D9",
            "borderRadius": "5px"
        }
    )

# @dash.callback(
#     dash.Output("player-cards-container", "children"),
#     dash.Input("position-tabs", "value")
# )
# def update_player_cards(position):
#     """Update cards when switching positions"""
#     return [player_card(p) for p in players[position]]

# Callback to render content based on clicked tab
@app.callback(
    Output("tab-content", "children"),
    Input("position-tabs", "value")
)
def render_tab_content(active_tab):
    # Fallback if None

    if not active_tab:
        active_tab = "QB"
    if active_tab == "QB":   # QB
        return html.Div(qb_cards)
    elif active_tab == "RB": # RB
        return html.Div(rb_cards)
    elif active_tab == "WR": # WR
        return html.Div(wr_cards)
    elif active_tab == "TE": # TE
        return html.Div(te_cards)
    return "No data available"
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/power-rankings':
        return power_page
    elif pathname == '/player-rankings':
        return player_page
    elif pathname == '/glossary':
        return glossary_page
    else:
        return home_page

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8010)