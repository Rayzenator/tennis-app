import streamlit as st
import random
import time
from collections import defaultdict
import json
import os
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# -----------------
# Sidebar Settings
# -----------------

with st.sidebar:
    st.header("Settings")

    match_type = st.selectbox(
        "Match Type",
        ["Singles", "Doubles", "American Doubles", "Rest"],
        key="match_type"
    )

    scoring_type = st.selectbox(
        "Scoring Type",
        ["Timed", "Fast Four"],
        key="scoring_type"
    )

# -----------------
# Helper Functions
# -----------------

def reset_players():
    st.session_state.players = []
    st.session_state.selected_players = []

def reset_courts():
    st.session_state.courts = []
    st.session_state.selected_courts = []

def add_player(name):
    if "players" not in st.session_state:
        st.session_state.players = []
    if name and name not in st.session_state.players:
        st.session_state.players.append(name)

def add_court(name):
    if "courts" not in st.session_state:
        st.session_state.courts = []
    if name and name not in st.session_state.courts:
        st.session_state.courts.append(name)

def schedule_matches(players, courts, match_type):
    matches = []
    players = players.copy()
    random.shuffle(players)

    if match_type == "Singles":
        group_size = 2
    elif match_type == "Doubles":
        group_size = 4
    elif match_type == "American Doubles":
        group_size = 3
    else:
        group_size = 0  # For Rest

    if group_size > 0:
        for i in range(0, len(players), group_size):
            group = players[i:i+group_size]
            if len(group) == group_size:
                matches.append(group)
    else:
        matches = [[player] for player in players]

    court_assignments = []
    for idx, match in enumerate(matches):
        court = courts[idx % len(courts)]
        court_assignments.append((court, match))

    return court_assignments

# -----------------
# Tabs
# -----------------

tab1, tab2, tab3 = st.tabs(["Players", "Courts", "Schedule"])

# -----------------
# Players Tab
# -----------------
with tab1:
    st.header("Manage Players")

    if "players" not in st.session_state:
        st.session_state.players = []

    if "selected_players" not in st.session_state:
        st.session_state.selected_players = []

    new_player = st.text_input("Add Player")
    if st.button("Add Player"):
        add_player(new_player)

    st.button("Reset Players", on_click=reset_players)

    if st.session_state.players:
        st.subheader("Select Players for Tonight")
        st.session_state.selected_players = st.multiselect(
            "Players",
            st.session_state.players,
            default=st.session_state.players
        )

# -----------------
# Courts Tab
# -----------------
with tab2:
    st.header("Manage Courts")

    if "courts" not in st.session_state:
        st.session_state.courts = []

    if "selected_courts" not in st.session_state:
        st.session_state.selected_courts = []

    new_court = st.text_input("Add Court")
    if st.button("Add Court"):
        add_court(new_court)

    st.button("Reset Courts", on_click=reset_courts)

    if st.session_state.courts:
        st.subheader("Select Courts for Tonight")
        st.session_state.selected_courts = st.multiselect(
            "Courts",
            st.session_state.courts,
            default=st.session_state.courts
        )

# -----------------
# Schedule Tab
# -----------------
with tab3:
    st.header("Tonight's Match Schedule")

    if "selected_players" not in st.session_state or not st.session_state.selected_players:
        st.warning("Please select players first.")
    elif "selected_courts" not in st.session_state or not st.session_state.selected_courts:
        st.warning("Please select courts first.")
    else:
        court_matches = schedule_matches(
            st.session_state.selected_players,
            st.session_state.selected_courts,
            st.session_state.match_type
        )

        if st.session_state.match_type != "Rest":
            for court, players in court_matches:
                players_str = ", ".join(players)
                st.write(f"**{court}** - {st.session_state.match_type} ({st.session_state.scoring_type}): {players_str}")
        else:
            st.subheader("Players Resting")
            for player in st.session_state.selected_players:
                st.write(player)
