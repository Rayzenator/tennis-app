import streamlit as st
import json
import os

# File paths
PLAYER_FILE = "players.json"
COURT_FILE = "courts.json"

# Load players and courts from JSON
def load_list(file_path, default=[]):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return default

# Save players and courts to JSON
def save_list(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f)

# Initialize session state
if "players" not in st.session_state:
    st.session_state.players = load_list(PLAYER_FILE)
if "courts" not in st.session_state:
    st.session_state.courts = load_list(COURT_FILE)
if "selected_players" not in st.session_state:
    st.session_state.selected_players = st.session_state.players.copy()
if "selected_courts" not in st.session_state:
    st.session_state.selected_courts = st.session_state.courts.copy()
if "rounds" not in st.session_state:
    st.session_state.rounds = []

# UI Tabs
tabs = st.tabs(["Courts", "Players", "Schedule"])

# --- Courts Tab ---
with tabs[0]:
    st.header("Courts")
    st.session_state.selected_courts = st.multiselect(
        "Select Courts for Tonight",
        st.session_state.courts,
        default=st.session_state.selected_courts,
    )
    court_input = st.text_input("Add a new court")
    if st.button("Add Court") and court_input:
        st.session_state.courts.append(court_input)
        save_list(COURT_FILE, st.session_state.courts)
    if st.button("Reset Courts"):
        st.session_state.courts.clear()
        save_list(COURT_FILE, st.session_state.courts)
    st.write("Current Courts:", st.session_state.courts)

# --- Players Tab ---
with tabs[1]:
    st.header("Players")
    st.session_state.selected_players = st.multiselect(
        "Select Players for Tonight",
        st.session_state.players,
        default=st.session_state.selected_players,
    )
    player_input = st.text_input("Add a new player")
    if st.button("Add Player") and player_input:
        st.session_state.players.append(player_input)
        save_list(PLAYER_FILE, st.session_state.players)
    if st.button("Reset Players"):
        st.session_state.players.clear()
        save_list(PLAYER_FILE, st.session_state.players)
    st.write("Current Players:", st.session_state.players)

# --- Schedule Tab ---
with tabs[2]:
    st.header("Schedule Matches")
    st.write("Selected Players:", st.session_state.selected_players)
    st.write("Selected Courts:", st.session_state.selected_courts)

    if st.button("Generate First Round") or st.button("Generate Next Round"):
        # Placeholder for scheduling logic
        round_number = len(st.session_state.rounds) + 1
        st.session_state.rounds.append({
            "round": round_number,
            "matches": [("Player A", "Player B") for _ in st.session_state.selected_courts]
        })

    if st.session_state.rounds:
        last_round = st.session_state.rounds[-1]
        st.subheader(f"Round {last_round['round']}")
        for i, match in enumerate(last_round["matches"]):
            st.write(f"Court {i+1}: {match[0]} vs {match[1]}")

        st.text("Enter Scores")
        for i, match in enumerate(last_round["matches"]):
            st.text_input(f"Score for Court {i+1} ({match[0]} vs {match[1]})", key=f"score_{last_round['round']}_{i}")

        st.button("Submit Scores")

    if st.button("Reset Rounds"):
        st.session_state.rounds = []
