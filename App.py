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
player_week = '22'
ratings_season = '2026'
ratings_week = '1'
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

create_master_predictions(f"{ratings_season}_Weekly_Predictions", file_type="csv")
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


# Shared filter values used by the page layouts and callbacks
weeks = sorted(df["Week"].dropna().unique().tolist())
all_teams = sorted(pd.unique(df[["Home Team", "Away Team"]].values.ravel()))

# -----------------------------------------------------------------------------
# Electric-blue, DraftKings-adjacent presentation layer
# -----------------------------------------------------------------------------
# The model/data calculations above are intentionally left intact. Everything
# below this point is presentation, layout, chart styling, and callbacks.

BG = "#040609"
CARD = "#0b1220"
CARD_ALT = "#0f1a2e"
TEXT = "#f7f9fc"
MUTED = "#8a96ac"
BORDER = "#1e2c42"
ELECTRIC = "#2f6bff"
ELECTRIC_BRIGHT = "#5ea1ff"
GLOW = "#6fe0ff"
GREEN = "#2fe28f"
RED = "#ff5470"
NAVY = "#0a1930"

# Backwards-compatible alias used throughout the rest of the file
BLUE = ELECTRIC


def rgba_from_hex(hex_color, alpha=0.14):
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def team_badge(team, dark_text=False):
    color = team_colors.get(team, "#64748b")
    return html.Span(
        team,
        style={
            "display": "inline-flex", "alignItems": "center", "justifyContent": "center",
            "width": "34px", "height": "34px", "borderRadius": "9px",
            "background": color, "color": "#fff" if not dark_text else TEXT,
            "fontWeight": "800", "fontSize": "11px", "letterSpacing": ".03em",
            "boxShadow": f"inset 0 0 0 1px {rgba_from_hex('#ffffff', .18)}",
        },
    )


def metric_box(label, value, sub=None, accent=ELECTRIC):
    return html.Div([
        html.Div(label, style={"fontSize": "11px", "fontWeight": "700", "color": MUTED, "textTransform": "uppercase", "letterSpacing": ".08em"}),
        html.Div(value, className="mobile-metric-value", style={"fontSize": "24px", "fontWeight": "800", "color": TEXT, "lineHeight": "1.15", "marginTop": "4px"}),
        html.Div(sub or "", style={"fontSize": "12px", "color": accent, "fontWeight": "600", "marginTop": "3px"}),
    ], className="mobile-metric", style={"padding": "16px 18px", "borderLeft": f"3px solid {accent}"})


def page_shell(children):
    return html.Div(children, style={
        "minHeight": "100vh", "background": BG, "color": TEXT,
        "fontFamily": "Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
    })


def top_nav(active="games"):
    links = [("games", "Games", "/"), ("power", "Power Ratings", "/power-rankings"),
             ("players", "Players", "/player-rankings"), ("glossary", "Methodology", "/glossary")]
    return html.Div([
        html.Div(className="mobile-brand", children=[
            html.A("POWER", href="/", style={
                "textDecoration": "none", "fontSize": "19px", "fontWeight": "900",
                "letterSpacing": ".08em", "color": TEXT,
            }),
            html.Span(" MODEL", style={
                "fontSize": "11px", "fontWeight": "800", "color": ELECTRIC_BRIGHT,
                "letterSpacing": ".14em", "marginLeft": "8px",
                "textShadow": f"0 0 12px {rgba_from_hex(ELECTRIC, .55)}",
            }),
        ]),
        html.Div(className="mobile-nav", children=[
            html.A(label, href=href, className="mobile-nav-link", style={
                "textDecoration": "none", "padding": "9px 14px", "borderRadius": "8px",
                "fontSize": "13px", "fontWeight": "700",
                "color": "#ffffff" if key == active else MUTED,
                "background": ELECTRIC if key == active else "transparent",
                "boxShadow": f"0 0 18px {rgba_from_hex(ELECTRIC, .45)}" if key == active else "none",
            }) for key, label, href in links
        ], style={"display": "flex", "gap": "3px", "alignItems": "center"}),
    ], className="mobile-header", style={
        "maxWidth": "1180px", "margin": "0 auto", "height": "68px", "padding": "0 18px",
        "display": "flex", "alignItems": "center", "justifyContent": "space-between",
        "borderBottom": f"1px solid {BORDER}",
        "background": BG,
    })


def hero(title, eyebrow, description):
    return html.Div([
        html.Div(eyebrow, style={
            "fontSize": "12px", "fontWeight": "800", "letterSpacing": ".06em",
            "color": ELECTRIC_BRIGHT, "marginBottom": "10px",
        }),
        html.H1(title, style={
            "fontSize": "40px", "lineHeight": "1.08", "letterSpacing": "-.03em",
            "fontWeight": "850", "margin": "0 0 12px", "color": TEXT,
        }),
        html.P(description, className="mobile-hero-description", style={
            "maxWidth": "700px", "fontSize": "15px", "lineHeight": "1.65",
            "color": MUTED, "margin": "0",
        }),
    ], className="mobile-hero", style={
        "padding": "42px 0 26px",
        "borderBottom": f"1px solid {BORDER}",
        "marginBottom": "26px",
    })

def stat_legend():
    terms = [
        ("EPA", "How many points a play added or subtracted vs. what was expected."),
        ("WAR", "How many extra wins a player is worth vs. a replacement-level player at their position."),
        ("PAAS", "How much value a player added vs. an average starter at their position."),
    ]
    return html.Div([
        html.Div([
            html.Span(term, style={"fontWeight": "800", "fontSize": "12px", "color": ELECTRIC_BRIGHT, "marginRight": "8px"}),
            html.Span(desc, style={"fontSize": "12px", "color": MUTED}),
        ], style={"padding": "10px 16px", "flex": "1", "minWidth": "220px"})
        for term, desc in terms
    ], style={
        "display": "flex", "flexWrap": "wrap", "background": CARD, "border": f"1px solid {BORDER}",
        "borderRadius": "10px", "marginBottom": "18px",
    })


def section_heading(title, kicker=None, right=None):
    return html.Div([
        html.Div([
            html.Div(kicker, style={
                "fontSize": "11px", "fontWeight": "800", "letterSpacing": ".06em",
                "color": ELECTRIC_BRIGHT, "marginBottom": "5px",
            }) if kicker else None,
            html.H2(title, style={"fontSize": "21px", "fontWeight": "800", "letterSpacing": "-.02em", "margin": "0", "color": TEXT}),
        ]),
        right,
    ], className="mobile-section-heading", style={"display": "flex", "alignItems": "end", "justifyContent": "space-between", "marginBottom": "14px"})


def make_strength_chart(home_mean, home_var, away_mean, away_var, hfa, home_team, away_team):
    home_var = max(float(home_var), 0.0001)
    away_var = max(float(away_var), 0.0001)
    x = np.linspace(min(home_mean, away_mean) - 0.6, max(home_mean, away_mean) + 0.6, 240)
    home_center = home_mean + hfa
    home_y = (1 / np.sqrt(2 * np.pi * home_var)) * np.exp(-((x - home_center) ** 2) / (2 * home_var))
    away_y = (1 / np.sqrt(2 * np.pi * away_var)) * np.exp(-((x - away_mean) ** 2) / (2 * away_var))
    hc, ac = team_colors.get(home_team, "#64748b"), team_colors.get(away_team, "#94a3b8")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=home_y, mode="lines", name=home_team,
        line=dict(color=hc, width=2.5), fill="tozeroy", fillcolor=rgba_from_hex(hc, .12),
        hovertemplate=f"{home_team} strength<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=away_y, mode="lines", name=away_team,
        line=dict(color=ac, width=2.5), fill="tozeroy", fillcolor=rgba_from_hex(ac, .10),
        hovertemplate=f"{away_team} strength<extra></extra>"))
    fig.update_layout(
        margin=dict(l=2, r=2, t=2, b=2), height=150,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", y=-.05, x=.5, xanchor="center", font=dict(color=MUTED, size=10)),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        hovermode="x unified",
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"width": "100%", "height": "150px"})


def apply_filters(frame, week, teams, ev_only):
    d = frame.copy()
    if week is None:
        week = d["Week"].max()
    d = d[d["Week"] == week]
    if teams:
        ts = set(teams)
        d = d[(d["Home Team"].isin(ts)) | (d["Away Team"].isin(ts))]
    if ev_only:
        d = d[d["EV_Positive"]]
    return d


def make_game_card(row):
    ev = float(row["Expected Value (%)"])
    ev_team = row["Expected Value Team"]
    positive = ev > 0
    home, away = row["Home Team"], row["Away Team"]
    model_spread = float(row["Home Team Projected Spread"])
    vegas_spread = float(row["Home Team Vegas Spread"])
    edge = float(row["Spread Edge"])
    return html.Div([
        html.Div([
            html.Div([
                html.Span(f"WEEK {int(row['Week'])}", style={"fontSize": "10px", "fontWeight": "800", "letterSpacing": ".1em", "color": MUTED}),
                html.Span("+EV", style={
                    "fontSize": "10px", "fontWeight": "800", "color": "#04150f",
                    "background": GREEN, "borderRadius": "5px", "padding": "4px 8px",
                    "boxShadow": f"0 0 14px {rgba_from_hex(GREEN, .5)}",
                }) if positive else None,
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "13px"}),
            html.Div([
                html.Div([team_badge(away), html.Span(away, style={"fontWeight": "800", "fontSize": "15px", "marginLeft": "9px", "color": TEXT})], style={"display": "flex", "alignItems": "center"}),
                html.Div("@", style={"color": MUTED, "fontWeight": "700", "fontSize": "12px", "margin": "0 10px"}),
                html.Div([team_badge(home), html.Span(home, style={"fontWeight": "800", "fontSize": "15px", "marginLeft": "9px", "color": TEXT})], style={"display": "flex", "alignItems": "center"}),
            ], className="mobile-game-teams", style={"display": "flex", "alignItems": "center", "marginBottom": "16px"}),
            html.Div([
                html.Div([html.Div("WIN PROBABILITY", style={"fontSize": "9px", "fontWeight": "800", "color": MUTED, "letterSpacing": ".08em"}),
                         html.Div(f"{row['Away Win %']:.1f}%  /  {row['Home Win %']:.1f}%", style={"fontSize": "19px", "fontWeight": "800", "marginTop": "3px", "color": TEXT})]),
                html.Div([html.Div("MODEL SPREAD", style={"fontSize": "9px", "fontWeight": "800", "color": MUTED, "letterSpacing": ".08em"}),
                         html.Div(f"{model_spread:+.1f}", style={"fontSize": "19px", "fontWeight": "800", "marginTop": "3px", "color": TEXT})]),
                html.Div([html.Div("MARKET", style={"fontSize": "9px", "fontWeight": "800", "color": MUTED, "letterSpacing": ".08em"}),
                         html.Div(f"{vegas_spread:+.1f}", style={"fontSize": "19px", "fontWeight": "800", "marginTop": "3px", "color": TEXT})]),
            ], className="mobile-game-stats", style={"display": "grid", "gridTemplateColumns": "1.3fr 1fr 1fr", "gap": "16px"}),
            html.Div([
                html.Span(f"EV {ev:+.1f}%", style={"fontWeight": "800", "color": GREEN if positive else RED}),
                html.Span(f"{ev_team}", style={"color": MUTED, "marginLeft": "8px"}),
            ], style={"fontSize": "12px", "paddingTop": "14px", "marginTop": "14px", "borderTop": f"1px solid {BORDER}"}),
        ], className="mobile-game-main", style={"flex": "1", "minWidth": "330px"}),
        html.Div([
            html.Div("MODEL DISTRIBUTION", style={"fontSize": "9px", "fontWeight": "800", "letterSpacing": ".08em", "color": MUTED, "marginBottom": "2px"}),
            make_strength_chart(row["Home Team Str Mean"], row["Home Team Str Var"], row["Away Team Str Mean"], row["Away Team Str Var"], row["HFA"], home, away),
        ], className="mobile-game-chart", style={"width": "39%", "minWidth": "300px", "borderLeft": f"1px solid {BORDER}", "paddingLeft": "20px"}),
    ], className="mobile-game-card", style={
        "display": "flex", "gap": "24px", "padding": "20px", "background": CARD,
        "border": f"1px solid {GREEN if positive else BORDER}",
        "borderLeft": f"4px solid {GREEN if positive else ELECTRIC}",
        "borderRadius": "10px", "marginBottom": "10px",
        "boxShadow": f"0 0 0 1px rgba(0,0,0,.2), 0 10px 30px {rgba_from_hex('#000000', .35)}",
    })


def filter_bar():
    return html.Div([
        html.Div([html.Div("WEEK", style={"fontSize": "10px", "fontWeight": "800", "color": MUTED, "marginBottom": "5px"}), dcc.Dropdown(id="week-dd", options=[{"label": int(w), "value": int(w)} for w in weeks], value=weeks[-1] if weeks else None, clearable=False, className="clean-dropdown")], style={"minWidth": "120px", "flex": "0 0 120px"}),
        html.Div([html.Div("TEAMS", style={"fontSize": "10px", "fontWeight": "800", "color": MUTED, "marginBottom": "5px"}), dcc.Dropdown(id="team-dd", options=[{"label": t, "value": t} for t in all_teams], multi=True, placeholder="All teams", className="clean-dropdown")], style={"minWidth": "190px", "flex": "1"}),
        html.Div([html.Div("SORT", style={"fontSize": "10px", "fontWeight": "800", "color": MUTED, "marginBottom": "5px"}), dcc.Dropdown(id="sort-dd", options=[{"label": "Expected value", "value": "ev"}, {"label": "Win probability gap", "value": "win_diff"}], value="ev", clearable=False, className="clean-dropdown")], style={"minWidth": "180px", "flex": "0 0 180px"}),
        html.Div([html.Div("", style={"height": "15px"}), dcc.Checklist(id="ev-only-toggle", options=[{"label": " +EV only", "value": 1}], value=[], inputClassName="ev-check", labelStyle={"fontSize": "12px", "fontWeight": "700", "color": TEXT, "whiteSpace": "nowrap"})], style={"display": "flex", "alignItems": "center"}),
    ], className="mobile-filter-bar", style={"display": "flex", "gap": "12px", "alignItems": "end", "padding": "13px", "background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px", "marginBottom": "18px"})


def player_table(df_pos):
    d = df_pos.copy()
    d = d.sort_values("WAR", ascending=False)
    rows = []
    for i, (_, r) in enumerate(d.iterrows(), 1):
        rows.append(html.Div([
            html.Div(str(i), style={"width": "34px", "color": MUTED, "fontWeight": "700"}),
            html.Div([html.Div(str(r["Player"]), style={"fontWeight": "800", "color": TEXT}), html.Div(str(r["TM"]), style={"fontSize": "11px", "color": MUTED, "marginTop": "2px"})], style={"flex": "1"}),
            html.Div(f"{r['GP']:.0f}", className="player-num"),
            html.Div(f"{r['Total EPA']:.1f}", className="player-num"),
            html.Div(f"{r['EPA per Play ( all plays contributed )']:.3f}", className="player-num"),
            html.Div(f"{r['WAR']:.2f}", className="player-num strong-num"),
            html.Div(f"{r['PAAS']:.1f}", className="player-num"),
        ], className="player-row"))
    table = html.Div([
        html.Div([html.Div("#", style={"width":"34px"}), html.Div("PLAYER", style={"flex":"1"}), html.Div("GP", className="player-head"), html.Div("TOTAL EPA", className="player-head"), html.Div("EPA/PLAY", className="player-head"), html.Div("WAR", className="player-head"), html.Div("PAAS", className="player-head")], className="player-row player-header"),
        *rows,
    ], style={"background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px", "overflow": "hidden"})
    return html.Div(table, className="player-table-scroll")


def make_power_rankings_cards(power_df, week=None, filter_teams=None):
    """Minimal, edgy power rankings board.

    The visible row only ever shows team, power rating, and projected wins.
    The 95% model range is computed but stays hidden inside a hover panel that
    reveals on mouse-over, keeping the base view intentionally sparse.
    """
    if week is None:
        week = power_df["Week"].max()
    d = power_df[power_df["Week"] == week].copy()
    if filter_teams:
        d = d[d["Team"].isin(filter_teams)]
    d = d.sort_values("Rank")
    if d.empty:
        return html.Div("No teams match the selected filter.", style={"padding": "30px", "color": MUTED, "textAlign": "center"})

    header = html.Div([
        html.Div("#", style={"width": "48px"}),
        html.Div("TEAM", style={"flex": "1"}),
        html.Div("POWER RATING", style={"width": "150px", "textAlign": "right"}),
        html.Div("WINS EQUIVALENT", style={"width": "150px", "textAlign": "right"}),
    ], className="mobile-power-header", style={
        "display": "flex", "alignItems": "center", "padding": "12px 20px",
        "color": MUTED, "fontSize": "9px", "fontWeight": "800", "letterSpacing": ".09em",
        "borderBottom": f"1px solid {BORDER}", "background": CARD_ALT,
    })

    rows = []
    for _, r in d.iterrows():
        team = r["Team"]
        rating = float(r["Score"])
        rank = int(r["Rank"])
        wins = float(r["Wins"])
        rank_style = {"color": ELECTRIC_BRIGHT if rank <= 5 else MUTED, "fontWeight": "900", "fontSize": "15px"}

        rows.append(html.Div([
            html.Div(str(rank), className="mobile-power-rank", style={"width": "48px", **rank_style}),
            html.Div([
                team_badge(team),
                html.Div(team, style={"fontWeight": "850", "fontSize": "14px", "marginLeft": "11px", "color": TEXT}),
            ], className="mobile-power-team", style={"flex": "1", "display": "flex", "alignItems": "center"}),
            html.Div(f"{rating:+.3f}", className="mobile-power-rating", style={
                "width": "150px", "textAlign": "right", "fontSize": "16px", "fontWeight": "900",
                "fontVariantNumeric": "tabular-nums", "color": TEXT,
            }),
            html.Div(f"{wins:.1f}", className="mobile-power-wins", style={
                "width": "150px", "textAlign": "right", "fontSize": "15px", "fontWeight": "850",
                "fontVariantNumeric": "tabular-nums", "color": TEXT,
            }),
        ], className="power-ranking-row mobile-power-row", style={
            "position": "relative", "display": "flex", "alignItems": "center", "minHeight": "58px",
            "padding": "0 20px", "borderBottom": f"1px solid {BORDER}",
            "background": CARD if rank % 2 else CARD_ALT,
        }))

    return html.Div([header, *rows], className="power-list mobile-power-list", style={
        "background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "12px", "overflow": "visible",
        "boxShadow": f"0 16px 40px {rgba_from_hex('#000000', .45)}",
    })


def build_power_df():
    """Power rating per team/week, built from the net-rating blend model:

    - Week 1: blends last season's closing net rating with this season's
      Vegas win-total implied strength.
    - Weeks 2-13: blends this season's most recent Net_Ratings.csv reading
      with that same preseason prior, decaying the prior's weight as the
      season progresses.
    - Week 14+: pure in-season net rating from the prior week's file.
    - An optional per-team QB adjustment is applied on top.
    """
    season = int(ratings_season)

    vegas_path = os.environ.get(
        "VEGAS_WINS_CSV",
        os.path.join(BASE_DIR,f"NFL Vegas Win Totals {season}.csv"),
    )
    vegas_df = pd.read_csv(vegas_path)

    def team_stats_path(yr, wk):
        return os.path.join(BASE_DIR, "Team Stats", str(yr), str(wk), "Net_Ratings.csv")

    def preseason_prior(team, last_season_df):
        vegas_wins = vegas_df.loc[vegas_df["Team"] == team, "Vegas Wins"].iloc[0]
        return ((last_season_df[team].iloc[0] * 2 / 3) * .35) + (
            ((vegas_wins - 8.3641) / 33.146) * .65
        )

    records = []
    for wk in weeks:
        wk = int(wk)

        if wk == 1:
            last_season_df = pd.read_csv(team_stats_path(season - 1, 22))
            net_df = None
        elif wk < 14:
            net_df = pd.read_csv(team_stats_path(season, wk - 1))
            last_season_df = pd.read_csv(team_stats_path(season - 1, 22))
        else:
            net_df = pd.read_csv(team_stats_path(season, wk - 1))
            last_season_df = None

        for team in all_teams:
            if wk == 1:
                score = preseason_prior(team, last_season_df)
            elif wk < 14:
                prior = preseason_prior(team, last_season_df)
                w = (wk - 1) / 13
                score = (net_df[team].iloc[0] * w) + (prior * (1 - w))
            else:
                score = net_df[team].iloc[0]

            if team in QB_ADJUSTMENTS:
                score += QB_ADJUSTMENTS[team]

            records.append({"Week": wk, "Team": team, "Score": float(score)})

    power_df = pd.DataFrame(records)
    power_df["Wins"] = power_df["Score"] * 33.146 + 8.3641
    power_df["Rank"] = power_df.groupby("Week")["Score"].rank(method="min", ascending=False).astype(int)
    return power_df.sort_values(["Week", "Rank"])


# Fill in per-team point adjustments here if/when you have them, e.g. {"KC": 0.05}
QB_ADJUSTMENTS = {}

# Computed once at startup rather than on every dropdown change.
POWER_DF = build_power_df()




# ---------------------------
# App + layout
# ---------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
app.title = "Spencer's Power Ratings & Predictions Dashboard"

app.index_string = """
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>
      html, body { margin:0; padding:0; background:""" + BG + """; }
      * { box-sizing:border-box; }
      body, h1, h2, h3, h4, h5, h6, p, div, span { color: """ + TEXT + """; }
      .clean-dropdown .Select-control {
        border:1px solid """ + BORDER + """ !important; border-radius:7px !important;
        min-height:34px !important; box-shadow:none !important; background:""" + CARD_ALT + """ !important;
      }
      .clean-dropdown .Select-placeholder, .clean-dropdown .Select-value-label { color:""" + TEXT + """ !important; font-size:12px !important; font-weight:600 !important; }
      .clean-dropdown .Select-menu-outer { z-index:9999; background:""" + CARD_ALT + """ !important; color:""" + TEXT + """ !important; }
      .clean-dropdown .Select-menu-outer .Select-option { background:""" + CARD_ALT + """ !important; color:""" + TEXT + """ !important; }
      .clean-dropdown .Select-menu-outer .Select-option.is-focused { background:""" + rgba_from_hex(ELECTRIC, .25) + """ !important; }
      .clean-dropdown .Select-arrow { border-color: """ + MUTED + """ transparent transparent !important; }
      .player-row { display:flex; align-items:center; min-height:58px; padding:0 15px; }
      .player-row:nth-child(even) { background:""" + CARD_ALT + """; }
      .player-header { min-height:38px; background:""" + CARD_ALT + """; color:""" + MUTED + """; font-size:9px; font-weight:800; letter-spacing:.08em; }
      .player-head { width:85px; text-align:right; color:""" + MUTED + """; }
      .player-num { width:85px; text-align:right; font-size:12px; color:""" + MUTED + """; font-variant-numeric:tabular-nums; }
      .strong-num { color:""" + TEXT + """; font-weight:800; }
      a:hover { opacity:.82; }
      .power-ranking-row { transition: background .15s ease; }
      .power-ranking-row:hover { background:""" + rgba_from_hex(ELECTRIC, .10) + """ !important; }

      /* ---------------------------------------------------------
         Mobile / phone layout
         --------------------------------------------------------- */
      @media (max-width: 700px) {
        html, body {
          width: 100%;
          max-width: 100%;
          overflow-x: hidden;
        }

        body {
          -webkit-text-size-adjust: 100%;
        }

        /* Keep the brand and navigation usable without squeezing them. */
        .mobile-nav {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: none;
        }
        .mobile-nav::-webkit-scrollbar { display: none; }

        /* Dash dropdowns are easier to tap on a phone. */
        .clean-dropdown .Select-control {
          min-height: 44px !important;
          border-radius: 9px !important;
        }
        .clean-dropdown .Select-placeholder,
        .clean-dropdown .Select-value-label {
          font-size: 13px !important;
        }

        /* Player tables scroll horizontally instead of becoming unreadable. */
        .player-table-scroll {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
          border-radius: 10px;
        }
        .player-table-scroll > div {
          min-width: 650px;
        }

        .player-row {
          min-height: 58px;
          padding: 0 12px;
        }

        /* Don't rely on hover for important information on touch screens. */
        .power-ranking-row:hover {
          background: inherit !important;
        }
      }

      @media (max-width: 480px) {
        /* Page gutters */
        .mobile-main {
          padding-left: 12px !important;
          padding-right: 12px !important;
        }

        /* Compact mobile header */
        .mobile-header {
          height: auto !important;
          min-height: 58px !important;
          padding: 8px 12px !important;
          gap: 8px;
          align-items: center !important;
        }

        .mobile-brand {
          flex: 0 0 auto;
        }

        .mobile-nav {
          flex: 1 1 auto;
          justify-content: flex-start !important;
          gap: 3px !important;
          padding-bottom: 2px;
        }

        .mobile-nav a {
          flex: 0 0 auto;
          padding: 8px 10px !important;
          font-size: 11px !important;
          white-space: nowrap;
        }

        /* Smaller hero with less vertical dead space. */
        .mobile-hero {
          padding: 26px 0 18px !important;
          margin-bottom: 18px !important;
        }

        .mobile-hero h1 {
          font-size: 30px !important;
          line-height: 1.08 !important;
          margin-bottom: 9px !important;
        }

        .mobile-hero p {
          font-size: 13px !important;
          line-height: 1.55 !important;
        }

        /* Four desktop metrics become a clean 2x2 phone grid. */
        .mobile-metrics {
          grid-template-columns: repeat(2, 1fr) !important;
          margin-bottom: 20px !important;
        }

        .mobile-metric {
          padding: 12px 13px !important;
        }

        .mobile-metric-value {
          font-size: 20px !important;
        }

        /* Filters stack vertically and use full-width touch targets. */
        .mobile-filter-bar,
        .mobile-power-filters {
          display: flex !important;
          flex-direction: column !important;
          align-items: stretch !important;
          gap: 9px !important;
          padding: 11px !important;
        }

        .mobile-filter-bar > div,
        .mobile-power-filters > div {
          width: 100% !important;
          min-width: 0 !important;
          flex: 1 1 auto !important;
        }

        .mobile-filter-bar .ev-mobile {
          justify-content: flex-start !important;
          min-height: 42px;
        }

        /* Game cards become one-column cards. */
        .mobile-game-card {
          flex-direction: column !important;
          gap: 14px !important;
          padding: 14px !important;
        }

        .mobile-game-main {
          width: 100% !important;
          min-width: 0 !important;
        }

        .mobile-game-chart {
          width: 100% !important;
          min-width: 0 !important;
          border-left: none !important;
          border-top: 1px solid """ + BORDER + """;
          padding-left: 0 !important;
          padding-top: 12px;
        }

        .mobile-game-teams {
          flex-wrap: wrap !important;
          row-gap: 8px;
        }

        .mobile-game-teams .team-name {
          font-size: 14px !important;
        }

        .mobile-game-stats {
          grid-template-columns: 1.25fr 1fr 1fr !important;
          gap: 8px !important;
        }

        .mobile-game-stats .stat-value {
          font-size: 16px !important;
        }

        /* Power rankings: turn the desktop table into compact cards. */
        .mobile-power-header {
          display: none !important;
        }

        .mobile-power-row {
          display: grid !important;
          grid-template-columns: 30px minmax(0, 1fr) auto auto !important;
          gap: 8px !important;
          min-height: 62px !important;
          padding: 0 12px !important;
        }

        .mobile-power-rank {
          width: auto !important;
        }

        .mobile-power-team {
          min-width: 0 !important;
        }

        .mobile-power-team-name {
          font-size: 13px !important;
        }

        .mobile-power-rating,
        .mobile-power-wins {
          width: auto !important;
          min-width: 55px !important;
          font-size: 14px !important;
        }

        /* Keep the two numeric columns readable on small screens. */
        .mobile-power-list {
          overflow: hidden !important;
        }

        /* Position tabs should span the screen and remain easy to tap. */
        .mobile-position-tabs {
          width: 100% !important;
        }

        .mobile-position-tabs .tab {
          padding: 10px 8px !important;
          font-size: 11px !important;
        }

        /* Glossary cards use tighter gutters. */
        .mobile-glossary {
          padding-left: 14px !important;
          padding-right: 14px !important;
        }

        .mobile-section-heading {
          align-items: flex-start !important;
          flex-direction: column !important;
          gap: 5px;
        }

        /* Graph legend gets more room on narrow screens. */
        .mobile-game-chart .js-plotly-plot {
          max-width: 100%;
        }
      }

      @media (max-width: 360px) {
        .mobile-brand span {
          display: none !important;
        }

        .mobile-nav a {
          padding: 8px 8px !important;
          font-size: 10px !important;
        }

        .mobile-game-stats {
          grid-template-columns: 1fr 1fr !important;
        }

        .mobile-game-stats > div:first-child {
          grid-column: 1 / -1;
        }

        .mobile-power-row {
          grid-template-columns: 26px minmax(0, 1fr) auto !important;
        }

        .mobile-power-wins {
          display: none !important;
        }
      }
    </style>
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
"""


def home_page():
    latest_week = int(weeks[-1]) if weeks else 1
    week_df = df[df["Week"] == latest_week]
    positive_count = int((week_df["Expected Value (%)"] > 0).sum())
    avg_ev = week_df["Expected Value (%)"].mean() if len(week_df) else 0
    return page_shell([
        top_nav("games"),
        html.Main([
            hero("Data-driven NFL predictions", "WEEKLY MODEL", "A clean view of my weekly projections, market edges, and team strength distributions."),
            html.Div([
                metric_box("Week", str(latest_week), "current model slate", ELECTRIC_BRIGHT),
                metric_box("Games", str(len(week_df)), "projected matchups", ELECTRIC),
                metric_box("+EV games", str(positive_count), "positive expected value", GREEN),
                metric_box("Avg. EV", f"{avg_ev:+.1f}%", "across selected slate", GREEN if avg_ev > 0 else RED),
            ], style={"display": "grid", "gridTemplateColumns": "repeat(4,1fr)", "background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px", "marginBottom": "30px", "overflow": "hidden"}),
            section_heading("Weekly projections", "GAME MODEL", "Games are ranked by expected value by default."),
            filter_bar(),
            html.Div(id="game-cards"),
            html.Div([
                html.H3("Model notes", style={"fontSize": "16px", "fontWeight": "800", "marginBottom": "7px", "color": TEXT}),
                html.P("Positive-EV games are highlighted. The distribution chart shows the model's estimated team-strength outcomes after applying home-field advantage.", style={"color": MUTED, "fontSize": "12px", "lineHeight": "1.6", "margin": 0}),
            ], style={"margin": "28px 0 50px", "padding": "18px", "borderTop": f"1px solid {BORDER}"})
        ], className="mobile-main", style={"maxWidth": "1180px", "margin": "0 auto", "padding": "0 18px"})
    ])


def power_page():
    latest = int(weeks[-1]) if weeks else 1
    return page_shell([
        top_nav("power"),
        html.Main([
            hero("Power ratings", "TEAM STRENGTH", "Team name, power rating, and equivalent wins."),
            html.Div(className="mobile-power-filters", children=[
                html.Div([html.Div("WEEK", style={"fontSize": "10px", "fontWeight": "800", "color": MUTED, "marginBottom": "5px"}), dcc.Dropdown(id="power-week-dd", options=[{"label": int(w), "value": int(w)} for w in weeks], value=latest, clearable=False, className="clean-dropdown")], style={"width": "150px"}),
                html.Div([html.Div("TEAMS", style={"fontSize": "10px", "fontWeight": "800", "color": MUTED, "marginBottom": "5px"}), dcc.Dropdown(id="power-team-dd", options=[{"label": t, "value": t} for t in all_teams], multi=True, placeholder="All teams", className="clean-dropdown")], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "12px", "padding": "13px", "background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px", "marginBottom": "18px"}),
            section_heading("NFL power rankings", "TEAM RATINGS", "Rating is the model score without accounting for QB adjustments"),
            html.Div(id="power-rankings-cards"),
        ], className="mobile-main", style={"maxWidth": "1180px", "margin": "0 auto", "padding": "0 18px 50px"})
    ])


def player_page():
    return page_shell([
        top_nav("players"),
        html.Main([
            hero("Player rankings", "PLAYER VALUE","A leaderboard of EPA, WAR, and PAAS by position."),
            stat_legend(),
            dcc.Tabs(id="position-tabs", className="mobile-position-tabs", value="QB", children=[
                dcc.Tab(
                    label=pos, value=pos,
                    style={"padding": "11px 22px", "fontWeight": "700", "fontSize": "12px", "border": f"1px solid {BORDER}", "background": CARD, "color": MUTED},
                    selected_style={"padding": "11px 22px", "fontWeight": "800", "fontSize": "12px", "border": f"1px solid {ELECTRIC}", "background": rgba_from_hex(ELECTRIC, .16), "color": ELECTRIC_BRIGHT},
                ) for pos in ["QB", "RB", "WR", "TE"]
            ], style={"marginBottom": "14px"}),
            html.Div(id="tab-content"),
        ], className="mobile-main", style={"maxWidth": "1180px", "margin": "0 auto", "padding": "0 18px 50px"})
    ])


def glossary_page():
    items = [
        ("Expected Value (%)", "Represents the long-term profitability of a bet by comparing model win probability with sportsbook-implied probability."),
        ("Spread Edge", "The difference between the model's projected spread and the Vegas spread."),
        ("Win% Differential", "The absolute gap between the home and away win probabilities."),
        ("Matchup Distribution", "The probability curves showing the model's estimated team-strength distributions, including home-field advantage."),
        ("Power Rating", "The underlying team-strength score used to rank teams and translate strength into projected wins."),
        ("WAR", "Wins Above Replacement, allocating player value relative to a replacement-level player at the same position."),
        ("PAAS", "Points Above Average Starter, measuring player total-EPA contribution relative to the starter baseline at that position."),
    ]
    return page_shell([
        top_nav("glossary"),
        html.Main([
            hero("Methodology & glossary", "MODEL CONTEXT", "Definitions for the metrics currently displayed throughout the dashboard."),
            html.Div([html.Div([html.H3(k, style={"fontSize": "14px", "fontWeight": "800", "margin": "0 0 5px", "color": TEXT}), html.P(v, style={"fontSize": "12px", "lineHeight": "1.65", "color": MUTED, "margin": 0})], style={"padding": "17px 0", "borderBottom": f"1px solid {BORDER}"}) for k, v in items], style={"background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px", "padding": "0 22px", "marginBottom": "50px"})
        ], style={"maxWidth": "900px", "margin": "0 auto", "padding": "0 18px"})
    ])


app.layout = html.Div([dcc.Location(id="url", refresh=False), html.Div(id="page-content")])


@app.callback(Output("game-cards", "children"), Input("week-dd", "value"), Input("team-dd", "value"), Input("ev-only-toggle", "value"), Input("sort-dd", "value"))
def update_game_cards(week, teams, ev_only_toggle, sort_by):
    filtered = apply_filters(df, week, teams, 1 in (ev_only_toggle or []))
    if sort_by == "ev":
        filtered = filtered.sort_values("Expected Value (%)", ascending=False)
    elif sort_by == "win_diff":
        filtered = filtered.sort_values("Win% Differential", ascending=False)
    return [make_game_card(r) for _, r in filtered.iterrows()] or html.Div("No games match these filters.", style={"padding": "35px", "textAlign": "center", "color": MUTED, "background": CARD, "border": f"1px solid {BORDER}", "borderRadius": "10px"})


@app.callback(Output("power-rankings-cards", "children"), Input("url", "pathname"), Input("power-week-dd", "value"), Input("power-team-dd", "value"))
def update_power_cards(pathname, selected_week, selected_teams):
    if pathname != "/power-rankings":
        raise dash.exceptions.PreventUpdate
    return make_power_rankings_cards(POWER_DF, selected_week, selected_teams)


@app.callback(Output("tab-content", "children"), Input("position-tabs", "value"))
def render_tab_content(active_tab):
    mapping = {"QB": qb_df, "RB": rb_df, "WR": wr_df, "TE": te_df}
    return player_table(mapping.get(active_tab or "QB", qb_df))


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/power-rankings":
        return power_page()
    if pathname == "/player-rankings":
        return player_page()
    if pathname == "/glossary":
        return glossary_page()
    return home_page()


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8010)
