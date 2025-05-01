import streamlit as st
import random
import json
import os
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Tennis Scheduler", layout="wide")

# Apply CSS for mobile optimization
st.markdown("""
    <style>
        body {
            font-size: 18px;
            line-height: 1.6;
        }
        .stButton>button {
            padding: 12px 24px;
            font-size: 16px;
            border-radius: 8px;
        }
        .stMultiselect, .stTextInput {
            font-size: 16px;
            padding: 10px;
        }
        .stNumberInput input {
            font-size: 16px;
            height: 40px;
        }
        .stSidebar {
            font-size: 16px;
        }
        .stTextInput, .stSelectbox, .stCheckbox {
            font-size: 16px;
        }
        .stMultiSelect, .stSelectbox {
            font-size: 16px;
        }
        .stMarkdown {
            font-size: 16px;
        }
        .stTextInput input {
            padding: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# File paths
PLAYER_FILE = "players.json"
COURT_FILE = "courts.json"
SCORE_FILE = "scores.csv"

# Load and save functions
def load_json(path, default=[]):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_scores():
    if os.path.exists(SCORE_FILE):
        return pd.read_csv(SCORE_FILE, index_col=0)
    return pd.DataFrame(columns=['games'])

def save_scores(df):
    df.to_csv(SCORE_FILE)

# Scheduler logic
def schedule_round(players, courts, match_type='Singles', allow_american=False, history=None, player_roles=None):
    if history is None:
        history = set()
    if player_roles is None:
        player_roles = {p: [] for p in players}
    
    # Ensure every player has a role entry (in case some players are missing from player_roles)
    for p in players:
        if p not in player_roles:
            player_roles[p] = []

    matches = []
    players = players.copy()

    def penalty(p):
        recent = player_roles.get(p, [])
        return recent[-1:] == ['rest'] or recent[-1:] == ['american']

    players.sort(key=penalty)
    random.shuffle(players)

    court_capacity = 2 if match_type == 'Singles' else 4
    max_players = len(courts) * court_capacity
    usable_players = players[:max_players]

    step = 2 if match_type == 'Singles' else 4
    leftover_players = players[max_players:]

    if match_type == 'Singles' and allow_american and len(usable_players) % 2 != 0:
        american = usable_players[:3]
        matches.append(tuple(american))
        for p in american:
            player_roles[p].append("american")
        usable_players = usable_players[3:]

    for i in range(0, len(usable_players), step):
        match = tuple(usable_players[i:i+step])
        if len(match) == step:
            matches.append(match)
            for p in match:
                player_roles[p].append("match")

    resting = set(players) - set(p for m in matches for p in m)
    for p in resting:
        player_roles[p].append("rest")

    for m in matches:
        history.add(frozenset(m))

    named_matches = [(court, match) for court, match in zip(courts, matches)]
    return named_matches, history, player_roles

def update_scores(nightly_df, all_time_df, submitted_scores):
    for player, score in submitted_scores.items():
        if player not in nightly_df.index:
            nightly_df.loc[player] = 0
        nightly_df.at[player, 'games'] += score
        if player not in all_time_df.index:
            all_time_df.loc[player] = 0
        all_time_df.at[player, 'games'] += score

def app():
    st.title("🎾 Tennis Round-Robin Scheduler")

    players = load_json(PLAYER_FILE)
    courts = load_json(COURT_FILE)

    if 'all_time' not in st.session_state:
        st.session_state.all_time = load_scores()

    if 'nightly' not in st.session_state:
        st.session_state.nightly = pd.DataFrame(0, index=players, columns=['games'])
    if 'history' not in st.session_state:
        st.session_state.history = set()
    if 'rounds' not in st.session_state:
        st.session_state.rounds = []
    if 'round_number' not in st.session_state:
        st.session_state.round_number = 1
    if 'player_roles' not in st.session_state:
        st.session_state.player_roles = {p: [] for p in players}

    with st.sidebar:
        st.header("Manage Players & Courts")
        new_player = st.text_input("Add Player")
        if st.button("Add Player") and new_player:
            players.append(new_player)
            save_json(PLAYER_FILE, players)

        new_court = st.text_input("Add Court")
        if st.button("Add Court") and new_court:
            courts.append(new_court)
            save_json(COURT_FILE, courts)

    selected_players = st.multiselect("Select Players for This Night", players)
    selected_courts = st.multiselect("Select Active Courts", courts)
    match_type = st.selectbox("Match Type", ["Singles", "Doubles"])
    format_type = st.selectbox("Format", ["Fast Four", "Timed"])
    allow_american = st.checkbox("Allow American Doubles")

    if st.button("Generate Round"):
        matches, st.session_state.history, st.session_state.player_roles = schedule_round(
            selected_players, selected_courts, match_type, allow_american,
            st.session_state.history, st.session_state.player_roles)

        st.session_state.rounds.append({
            'round': st.session_state.round_number,
            'matches': matches,
            'scores': {player: 0 for _, m in matches for player in m}
        })
        st.session_state.round_number += 1

    for round_info in st.session_state.rounds:
        st.subheader(f"Round {round_info['round']}")
        cols = st.columns(len(round_info['matches']))
        for i, (court_name, match) in enumerate(round_info['matches']):
            with cols[i]:
                st.markdown(f"**{court_name}:**")
                for player in match:
                    score = st.number_input(f"{player} score", min_value=0, key=f"r{round_info['round']}_{player}")
                    round_info['scores'][player] = score

        if st.button(f"Submit Scores for Round {round_info['round']}"):
            update_scores(st.session_state.nightly, st.session_state.all_time, round_info['scores'])
            save_scores(st.session_state.all_time)
            st.success(f"Scores for Round {round_info['round']} submitted.")

    st.subheader("🎯 Nightly Leaderboard")
    st.dataframe(st.session_state.nightly.sort_values("games", ascending=False))

    st.subheader("🏆 All-Time Leaderboard")
    st.dataframe(st.session_state.all_time.sort_values("games", ascending=False))

    if st.button("Export Leaderboard to CSV"):
        st.session_state.all_time.to_csv("all_time_leaderboard.csv")
        st.success("Exported to all_time_leaderboard.csv")

    if st.button("Reset Night"):
        st.session_state.nightly = pd.DataFrame(0, index=players, columns=['games'])
        st.session_state.history = set()
        st.session_state.rounds = []
        st.session_state.round_number = 1
        st.session_state.player_roles = {p: [] for p in players}
        st.success("Nightly session reset.")

    with st.expander("⚠️ Danger Zone: All-Time Leaderboard"):
        if st.button("Delete All-Time Leaderboard"):
            if st.checkbox("Are you sure? This cannot be undone."):
                if os.path.exists(SCORE_FILE):
                    os.remove(SCORE_FILE)
                st.session_state.all_time = pd.DataFrame(columns=['games'])
                save_scores(st.session_state.all_time)
                st.success("All-Time Leaderboard has been deleted.")

if __name__ == '__main__':
    app()
