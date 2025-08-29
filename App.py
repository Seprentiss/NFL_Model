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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------
# Config
# ---------------------------
CSV_PATH = os.environ.get(
    "PREDICTIONS_CSV",
    os.path.join(BASE_DIR, "2025_Weekly_Predictions", "Week_1_Predictions_Full_Season.csv")
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
df["Spread Edge"] = abs(df["Home Team Projected Spread"] - df["Home Team Vegas Spread"])

df["Win% Differential"] = (df["Home Win %"] - df["Away Win %"]).abs()

qb_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats","2024","22","qb_data.csv"))
rb_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats","2024","22","rb_data.csv"))
wr_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats","2024","22","wr_data.csv"))
te_df = pd.read_csv(os.path.join(BASE_DIR, "Player Stats","2024","22","te_data.csv"))

def add_waa(df):
    # Calculate WAA based on top 32 players at this position
    top32_avg_epa = df['EPA per Play ( all offense )'].nlargest(32).mean()
    df['WAA'] = (df['EPA per Play ( all offense )'] * 33.146 + 8.3641) - (top32_avg_epa * 33.146 + 8.3641)
    return df

qb_df = add_waa(qb_df)
rb_df = add_waa(rb_df)
wr_df = add_waa(wr_df)
te_df = add_waa(te_df)

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
                        html.P(f"EPA per Play: {round(player['EPA per Play ( all offense )'],2)}", className="mb-1"),
                        html.P(f"WAA: {player['WAA']:.2f}", className="mb-1")
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
                        value=weeks[0] if weeks else None,
                        clearable=False,
                        style={"backgroundColor": "white", "color": "#013080"}
                    ),
                ], md=4),
                dbc.Col([
                    dbc.Label("Team filter (optional)", style={"color": "#AAAAAA"}),
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
                    # Team filter
                    dbc.Col(
                        [
                            dbc.Label("Filter by Team", style={"color": "#AAAAAA"}),
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


app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# ---------------------------
# Helpers
# ---------------------------
def apply_filters(frame, week, teams, ev_only):
    d = frame.copy()
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
                                dbc.Badge(f"Proj: {row['Home Team Projected Spread']:+.1f}", color="info",
                                          className="me-1"),
                                dbc.Badge(f"Vegas: {row['Home Team Vegas Spread']:+.1f}", color="black",
                                          className="me-1"),
                                dbc.Badge(f"Edge: {row['Spread Edge']:+.1f}", color="secondary",
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

def make_power_rankings_cards(power_df,filter_teams=None, sort_by="Rank"):
    pills = []

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
                        html.P(f"WAA: TBD", className="mb-1")  # You can calculate Wins Above Average QB if you have formula
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
    Input("power-team-dd", "value"),
)
def update_power_cards(pathname, selected_teams):
    if pathname != "/power-rankings":
        raise dash.exceptions.PreventUpdate

    # Recalculate power_df
    team_stats = {}
    for _, r in df.iterrows():
        for team, mean in [(r["Home Team"], r["Home Team Str Mean"]), (r["Away Team"], r["Away Team Str Mean"])]:
            if team not in team_stats:
                team_stats[team] = {"total": 0, "count": 0}
            team_stats[team]["total"] += mean
            team_stats[team]["count"] += 1

    power_df = pd.DataFrame([
        {"Team": t, "Score": s["total"]/s["count"]} for t, s in team_stats.items()
    ]).sort_values("Score", ascending=False)  # original sorting
    power_df["Rank"] = range(1, len(power_df)+1)
    power_df["Wins"] = power_df["Score"] * 33.146 + 8.3641

    # Apply team filter
    if selected_teams:
        power_df = power_df[power_df["Team"].isin(selected_teams)]

    # Return scrollable pills
    return html.Div(
        make_power_rankings_cards(power_df),
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
    print(active_tab)
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
    else:
        return home_page

# ---------------------------
# Main
# ---------------------------
if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8040)
