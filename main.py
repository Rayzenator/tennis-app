import streamlit as st
import json
import os
import pandas as pd
import random

def load_json(path, default=[]):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_players():
    return load_json('players.json')

def save_players(players):
    save_json('players.json', players)

def load_courts():
    return load_json('courts.json')

def save_courts(courts):
    save_json('courts.json', courts)

def load_all_time_scores():
    if os.path.exists('scores.csv'):
        return pd.read_csv('scores.csv', index_col=0)
    return pd.DataFrame(columns=['games'])

def save_all_time_scores(df):
    df.to_csv('scores.csv')

def schedule_round(players, courts, match_type='Singles', allow_american=False, history=None):
    if history is None:
        history = set()
    matches = []
    players = players.copy()
    random.shuffle(players)

    if match_type == 'Singles' and allow_american and len(players) % 2 != 0:
        matches.append(tuple(players[:3]))
        players = players[3:]

    court_capacity = 2 if match_type == 'Singles' else 4
    max_players = len(courts) * court_capacity
    players = players[:max_players]

    step = 2 if match_type == 'Singles' else 4
    for i in range(0, len(players), step):
        match = tuple(players[i:i+step])
        if len(match) == step:
            matches.append(match)

    for m in matches:
        history.add(frozenset(m))
    return matches, history

def update_scores(nightly, all_time, match, scores):
    for idx, player in enumerate(match):
        nightly.at[player, 'games'] = nightly.get(player, {}).get('games', 0) + scores[idx]
        if player not in all_time.index:
            all_time.loc[player] = 0
        all_time.at[player, 'games'] += scores[idx]

def app():
    st.set_page_config(page_title="Tennis Scheduler", layout="wide")
    st.title("🎾 Tennis Night Round-Robin Scheduler")

    players = load_players()
    courts = load_courts()
    all_time = load_all_time_scores()

    st.sidebar.header("Manage Players & Courts")
    new_player = st.sidebar.text_input("Add Player")
    if st.sidebar.button("Add Player") and new_player:
        players.append(new_player)
        save_players(players)

    new_court = st.sidebar.text_input("Add Court")
    if st.sidebar.button("Add Court") and new_court:
        courts.append(new_court)
        save_courts(courts)

    selected_players = st.multiselect("Select Players Playing Tonight", players)
    selected_courts = st.multiselect("Select Active Courts", courts)
    match_type = st.selectbox("Match Type", ["Singles", "Doubles"])
    match_format = st.selectbox("Format", ["Fast Four", "Timed"])
    allow_american = st.checkbox("Use American Doubles if Odd Singles")

    # Initialize session state
    if 'nightly' not in st.session_state:
        st.session_state.nightly = pd.DataFrame(0, index=selected_players, columns=['games'])
    if 'history' not in st.session_state:
        st.session_state.history = set()

    if st.button("Generate Round"):
        matches, st.session_state.history = schedule_round(
            selected_players, selected_courts, match_type, allow_american, st.session_state.history)
        st.session_state.matches = matches

    if 'matches' in st.session_state:
        st.subheader("Scheduled Matches")
        for i, match in enumerate(st.session_state.matches):
            st.write(f"Court {i+1}: {', '.join(match)}")
            score_inputs = [st.number_input(f"Games won by {p}", min_value=0, key=f"{i}_{p}") for p in match]
            if st.button(f"Submit Score for Match {i}"):
                update_scores(st.session_state.nightly, all_time, match, score_inputs)
                save_all_time_scores(all_time)

    st.subheader("🎯 Nightly Leaderboard")
    st.dataframe(st.session_state.nightly.sort_values("games", ascending=False))

    st.subheader("🏆 All-Time Leaderboard")
    st.dataframe(all_time.sort_values("games", ascending=False))

    if st.button("Export All-Time Leaderboard to CSV"):
        all_time.to_csv("all_time_leaderboard.csv")
        st.success("Exported to all_time_leaderboard.csv")

    if st.button("Reset Night"):
        st.session_state.nightly = pd.DataFrame(0, index=players, columns=['games'])
        st.session_state.history = set()
        st.session_state.matches = []
        st.success("Nightly stats cleared.")

if __name__ == '__main__':
    app()
