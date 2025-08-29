import pandas as pd

ev_table = pd.read_excel("Cover Prob EV.xlsx",engine="openpyxl")
value = ev_table[(ev_table["true_line"] == -2.5) & (ev_table["market_line"] == -3)]['ev_roi'].values[0]