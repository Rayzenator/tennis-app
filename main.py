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

# Timer management (simplified)
def update_timer():
    if 'start_time' in st.session_state:
        elapsed_time = time.time() - st.session_state.start_time
        minutes = int(elapsed_time // 60)
        seconds = int(elapsed_time % 60)
        st.session_state.timer_display = f"{minutes:02}:{seconds:02}"
    else:
        st.session_state.timer_display = "00:00"

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
    st.session_state.timer_display = "00:00"
    st.session_state.timer_running = False

# Sidebar UI
def sidebar_management():
    with st.sidebar:
        tab1, tab2, tab3 = st.tabs(["Manage Courts", "Manage Players", "Settings"])
        with tab1:
            st.header("Courts")
            new = st.text_input("Add Court", key="court_in")
            if st.button("Add Court") and new:
                if new not in st.session_state.courts:
                    st.session_state.courts.append(new)
                    save_data()

        with tab2:
            st.header("Players")
            newp = st.text_input("Add Player", key="player_in")
            if st.button("Add Player") and newp:
                if newp not in st.session_state.players:
                    st.session_state.players.append(newp)
                    save_data()

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

# Timer control
st.subheader("Match Timer")
st.write("Match Duration: 30 minutes")
st.write(f"Time Remaining: {st.session_state.timer_display}")

if st.session_state.timer_running:
    if st.button("Pause Timer"):
        st.session_state.timer_running = False
elif st.button("Start Timer"):
    st.session_state.timer_running = True
    st.session_state.start_time = time.time()

if st.session_state.timer_running:
    update_timer()

if st.button("Stop Timer"):
    st.session_state.timer_running = False
    st.session_state.timer_display = "00:00"

# Schedule new round
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

    st.download_button("Download as PDF", generate_pdf(latest_round['matches'], latest_round['round']), file_name=f"tennis_schedule_round_{latest_round['round']}.pdf")
    st.download_button("Download as CSV", generate_csv(latest_round['matches']), file_name=f"tennis_schedule_round_{latest_round['round']}.csv")
