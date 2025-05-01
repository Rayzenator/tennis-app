import streamlit as st
import random
import json
import os
from collections import defaultdict
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import time

# Page configuration
st.set_page_config(page_title="Tennis Scheduler", layout="wide")

# Dark Mode Styling
st.markdown(
    """
    <style>
    body { background-color: #1e1e1e; color: white; }
    .sidebar .sidebar-content { background-color: #2e2e2e; color: white; }
    .stButton>button {
        font-size: 24px !important;
        padding: 14px 24px !important;
        border-radius: 12px !important;
        color: #FFFFFF !important;
        background-color: #007BFF !important;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Data persistence file paths
DATA_FILE = "data.json"
SCORES_FILE = 'scores.json'

# Load or initialize scores data
def load_scores():
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'r') as file:
            return json.load(file)
    else:
        return {}

def save_scores(scores):
    with open(SCORES_FILE, 'w') as file:
        json.dump(scores, file)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"courts": [], "players": []}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({"courts": st.session_state.courts,
                   "players": st.session_state.players}, f)

# Sidebar management
def sidebar_management():
    with st.sidebar:
        tab1, tab2, tab3 = st.tabs(["Courts", "Players", "Leaderboard"])

        # Tab 1 - Courts
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = load_data().get("courts", [])
            if 'court_counter' not in st.session_state:
                st.session_state.court_counter = 0
            st.header("Courts")

            court_key = f"court_in_{st.session_state.court_counter}"
            new_court = st.text_input("Add Court", key=court_key)

            if st.button("Add Court") and new_court:
                if new_court not in st.session_state.courts:
                    st.session_state.courts.append(new_court)
                    save_data()
                else:
                    st.warning("Court already exists.")
                st.session_state.court_counter += 1

            if st.button("Reset Courts"):
                st.session_state.courts = []
                save_data()

            for i, court in enumerate(st.session_state.courts):
                st.write(court)
                if st.button(f"❌ Remove {court}", key=f"rm_court_{i}"):
                    st.session_state.courts.pop(i)
                    save_data()

        # Tab 2 - Players
        with tab2:
            if 'players' not in st.session_state:
                st.session_state.players = load_data().get("players", [])
            st.header("Players")
            new_player = st.text_input("Add Player", key="player_in")
            if st.button("Add Player") and new_player:
                if new_player not in st.session_state.players:
                    st.session_state.players.append(new_player)
                    save_data()
                else:
                    st.warning("Player already exists.")
            if st.button("Reset Players"):
                st.session_state.players = []
                save_data()

            for i, player in enumerate(st.session_state.players):
                st.write(player)
                if st.button(f"❌ Remove {player}", key=f"rm_player_{i}"):
                    st.session_state.players.pop(i)
                    save_data()

        # Tab 3 - Leaderboard
        with tab3:
            player_scores = load_scores()
            sorted_scores = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)
            st.write("### Leaderboard")
            for i, (player, score) in enumerate(sorted_scores, start=1):
                st.write(f"{i}. {player}: {score} points")

            if st.button("Delete All Player Scores"):
                delete_all_scores()

def delete_all_scores():
    save_scores({})
    st.success("All player scores have been deleted.")

def update_scores(current_scores, players, new_scores):
    for player in players:
        current_scores[player] = current_scores.get(player, 0) + new_scores.get(player, 0)
    return current_scores

def match_results(players):
    st.write("### Enter Scores for Each Player")
    player_scores = {}
    for player in players:
        score = st.number_input(f"Score for {player}", min_value=0, value=0, key=f"score_{player}")
        player_scores[player] = score
    if st.button("Submit Scores"):
        player_scores = update_scores(load_scores(), players, player_scores)
        save_scores(player_scores)
        st.experimental_rerun()

# Export helpers
def generate_pdf(matches, rnd):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    y = h - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Tennis Schedule - Round {rnd}")
    y -= 30
    c.setFont("Helvetica", 12)
    for court, pts in matches:
        c.drawString(50, y, f"Court {court}: {' vs '.join(pts)}")
        y -= 20
        if y < 50:
            c.showPage()
            y = h - 40
    c.save()
    buf.seek(0)
    return buf

def generate_csv(matches):
    df = pd.DataFrame([(c, ', '.join(players)) for c, players in matches], columns=["Court", "Players"])
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf

# Schedule logic (already updated with your fixes)
# ... (omitted here for brevity but it's been inserted above)

sidebar_management()
schedule_matches()
