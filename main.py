import streamlit as st
import random
import time
import json
import os
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Page configuration and dark mode styling
st.set_page_config(page_title="Tennis Scheduler", layout="wide")
DARK_MODE_STYLE = """
<style>
body { background-color: #1e1e1e; color: white; }
.sidebar .sidebar-content { background-color: #2e2e2e; color: white; }
</style>
"""
st.markdown(DARK_MODE_STYLE, unsafe_allow_html=True)

# Data persistence
DATA_FILE = "data.json"
SCORES_FILE = "scores.json"

# Load player and court data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"courts": [], "players": []}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({"courts": st.session_state.courts,
                   "players": st.session_state.players}, f)

# Load or initialize scores data
def load_scores():
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_scores(scores):
    with open(SCORES_FILE, 'w') as f:
        json.dump(scores, f)

def delete_all_scores():
    if os.path.exists(SCORES_FILE):
        os.remove(SCORES_FILE)

# Sidebar management
def sidebar_management():
    with st.sidebar:
        tab1, tab2, tab3 = st.tabs(["Manage Courts", "Manage Players", "Settings"])
        with tab1:
            st.header("Courts")
            from streamlit_sortables import sort_items
            st.markdown("Drag to reorder:")
            new_order = sort_items(st.session_state.courts, direction="vertical")
            if new_order != st.session_state.courts:
                st.session_state.courts = new_order
                save_data()

            for i, court in enumerate(st.session_state.courts):
                c1, c2 = st.columns([8, 1])
                c1.write(court)
                if c2.button("❌", key=f"rm_court_{i}"):
                    st.session_state.courts.pop(i)
                    save_data()
            new = st.text_input("Add Court", key="court_in")
            if st.button("Add Court") and new:
                if new not in st.session_state.courts:
                    st.session_state.courts.append(new)
                    save_data()
                else:
                    st.warning("Court already exists.")
            if st.button("Reset Courts"):
                st.session_state.courts = []
                save_data()
        with tab2:
            st.header("Players")
            for i, player in enumerate(st.session_state.players):
                p1, p2 = st.columns([8, 1])
                p1.write(player)
                if p2.button("❌", key=f"rm_player_{i}"):
                    st.session_state.players.pop(i)
                    save_data()
            newp = st.text_input("Add Player", key="player_in")
            if st.button("Add Player") and newp:
                if newp not in st.session_state.players:
                    st.session_state.players.append(newp)
                    save_data()
                else:
                    st.warning("Player already exists.")
            if st.button("Reset Players"):
                st.session_state.players = []
                save_data()
        with tab3:
            st.header("Settings")
            if st.button("Delete All Scores"):
                st.warning("Are you sure you want to delete all scores? This cannot be undone.")
                if st.button("Confirm Delete", key="confirm_delete"):
                    delete_all_scores()
                    st.success("All scores have been deleted.")

        st.markdown("---")
        st.markdown("### Leaderboard")
        scores = load_scores()
        if scores:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            for i, (player, score) in enumerate(sorted_scores, 1):
                st.write(f"{i}. {player}: {score} points")

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

# App state initialization
if 'initialized' not in st.session_state:
    d = load_data()
    st.session_state.courts = d['courts']
    st.session_state.players = d['players']
    st.session_state.initialized = True
    st.session_state.round_number = 0
    st.session_state.history = []
    st.session_state.scores = load_scores()

# Sidebar UI
sidebar_management()

# Main page
st.title("🎾 Tennis Scheduler")

# Match scheduling logic
def schedule_matches():
    players = st.session_state.players.copy()
    courts = st.session_state.courts
    if not players or not courts:
        st.warning("Please add players and courts to schedule matches.")
        return []

    random.shuffle(players)
    matches = []
    court_assignments = min(len(players) // 2, len(courts))

    for i in range(court_assignments):
        p1 = players[2 * i]
        p2 = players[2 * i + 1]
        matches.append((courts[i], [p1, p2]))

    return matches

def enter_scores(players):
    st.subheader("Enter Scores")
    scores = {}
    for player in players:
        scores[player] = st.number_input(f"Score for {player}", min_value=0, value=0, key=f"score_{player}_{time.time()}")
    if st.button("Submit Scores"):
        all_scores = load_scores()
        for player, pts in scores.items():
            all_scores[player] = all_scores.get(player, 0) + pts
        save_scores(all_scores)
        st.success("Scores updated!")
        time.sleep(1)
        st.experimental_rerun()

# Timer logic
def display_timer():
    st.markdown("<h3 style='text-align: center;'>Big Timer</h3>", unsafe_allow_html=True)
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
        st.session_state.running = False
    if "elapsed_time" not in st.session_state:
        st.session_state.elapsed_time = 0

    if st.session_state.running:
        st.session_state.elapsed_time = time.time() - st.session_state.start_time
    minutes, seconds = divmod(int(st.session_state.elapsed_time), 60)
    st.markdown(f"<div class='big-clock'>{minutes:02}:{seconds:02}</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Start Timer"):
            st.session_state.start_time = time.time() - st.session_state.elapsed_time
            st.session_state.running = True
    with col2:
        if st.button("Stop Timer"):
            st.session_state.running = False
    with col3:
        if st.button("Reset Timer"):
            st.session_state.start_time = None
            st.session_state.elapsed_time = 0
            st.session_state.running = False

# Match scheduling and score handling
st.markdown(f"## Round {st.session_state.round_number}")

if st.button("Schedule New Round"):
    st.session_state.round_number += 1
    matches = schedule_matches()
    st.session_state.history.append({"round": st.session_state.round_number, "matches": matches})

if st.session_state.history:
    latest_round = st.session_state.history[-1]
    st.write(f"### Matches for Round {latest_round['round']}")
    players_in_round = []
    for court, players in latest_round['matches']:
        st.write(f"**Court {court}:** {players[0]} vs {players[1]}")
        players_in_round.extend(players)

    enter_scores(players_in_round)

    st.download_button("Download as PDF", generate_pdf(latest_round['matches'], latest_round['round']), file_name=f"tennis_schedule_round_{latest_round['round']}.pdf")
    st.download_button("Download as CSV", generate_csv(latest_round['matches']), file_name=f"tennis_schedule_round_{latest_round['round']}.csv")
    
    # Timer placement
    display_timer()
