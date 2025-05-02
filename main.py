import streamlit as st
import random
import json
import os
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Tennis Scheduler", layout="wide")

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
    leftover_players = players[max_players:]

    step = 2 if match_type == 'Singles' else 4

    for i in range(0, len(usable_players), step):
        match = tuple(usable_players[i:i+step])
        if len(match) == step:
            matches.append(match)
            for p in match:
                player_roles.setdefault(p, []).append("match")

    lp = leftover_players
    if allow_american:
        if match_type == 'Singles':
            # Handle the case when there is 1 leftover player in Singles
            if len(lp) == 1:
                # Convert 1 leftover player into American Doubles
                singles_match = matches.pop()  # Pop a singles match to split
                american_group = singles_match[1:] + lp  # Add the leftover player
                matches.append(singles_match[:1])  # Keep the original singles match
                matches.append(tuple(american_group))  # Add American Doubles match
                for p in singles_match:
                    player_roles.setdefault(p, []).append("match")
                for p in american_group:
                    player_roles.setdefault(p, []).append("american")
            elif len(lp) == 2:
                matches.append(tuple(lp))  # Create a singles match
                for p in lp:
                    player_roles.setdefault(p, []).append("match")
            elif len(lp) == 3:
                matches.append(tuple(lp))  # Add an American Doubles match
                for p in lp:
                    player_roles.setdefault(p, []).append("american")
        else:
            # Doubles logic: handle remaining players as before (American Doubles or Rest)
            if len(lp) == 1:
                convertible_idx = next((i for i, m in enumerate(matches) if len(m) == 4), None)
                if convertible_idx is not None:
                    match_to_split = matches.pop(convertible_idx)
                    singles_match = match_to_split[:2]
                    american_group = match_to_split[2:] + lp
                    matches.append(singles_match)
                    matches.append(tuple(american_group))
                    for p in singles_match:
                        player_roles.setdefault(p, []).append("match")
                    for p in american_group:
                        player_roles.setdefault(p, []).append("american")
                else:
                    for p in lp:
                        player_roles.setdefault(p, []).append("rest")
            elif len(lp) == 2:
                matches.append(tuple(lp))
                for p in lp:
                    player_roles.setdefault(p, []).append("match")
            elif len(lp) == 3:
                matches.append(tuple(lp))
                for p in lp:
                    player_roles.setdefault(p, []).append("american")
            else:
                for p in lp:
                    player_roles.setdefault(p, []).append("rest")
    else:
        for p in lp:
            player_roles.setdefault(p, []).append("rest")

    all_matched_players = set(p for m in matches for p in m)
    resting = set(players) - all_matched_players
    for p in resting:
        player_roles.setdefault(p, []).append("rest")

    for m in matches:
        history.add(frozenset(m))

    named_matches = [(court, match) for court, match in zip(courts, matches)]
    return named_matches, history, player_roles

# Ensuring player and court names are unique
def ensure_unique_names(players, courts):
    # Ensure players are unique
    unique_players = list(set(players))
    if len(unique_players) != len(players):
        st.warning("Duplicate player names found. Removing duplicates.")
        players = unique_players

    # Ensure courts are unique
    unique_courts = list(set(courts))
    if len(unique_courts) != len(courts):
        st.warning("Duplicate court names found. Removing duplicates.")
        courts = unique_courts

    return players, courts

def app():
    st.title("🎾 Tennis Round-Robin Scheduler")

    players = load_json(PLAYER_FILE)
    courts = load_json(COURT_FILE)

    # Ensure player and court names are unique
    players, courts = ensure_unique_names(players, courts)

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
            if new_player not in players:
                players.append(new_player)
                save_json(PLAYER_FILE, players)
            else:
                st.warning("Player already exists!")

        new_court = st.text_input("Add Court")
        if st.button("Add Court") and new_court:
            if new_court not in courts:
                courts.append(new_court)
                save_json(COURT_FILE, courts)
            else:
                st.warning("Court already exists!")

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
        with st.expander(f"Round {round_info['round']}", expanded=(round_info['round'] == st.session_state.round_number - 1)):
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

    st.subheader("📜 All Time Leaderboard")
    st.dataframe(st.session_state.all_time.sort_values("games", ascending=False))

if __name__ == "__main__":
    app()
