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

# Page configuration and dark mode styling
st.set_page_config(page_title="Tennis Scheduler", layout="wide")
DARK_MODE_STYLE = """
<style>
body { background-color: #1e1e1e; color: white; }
.sidebar .sidebar-content { background-color: #2e2e2e; color: white; }
</style>
"""
st.markdown(DARK_MODE_STYLE, unsafe_allow_html=True)

# Clock & alert styles
CLOCK_STYLE = """
<style>
.big-clock {
    font-size: 72px;
    font-weight: bold;
    color: #00FF00;
    background-color: #000000;
    padding: 20px;
    text-align: center;
    border-radius: 15px;
}
</style>
"""
ALERT_SOUND = """
<audio id="beep" autoplay loop>
  <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg">
  Your browser does not support the audio element.
</audio>
<script>
  const sound = document.getElementById('beep');
  sound.play();
  setTimeout(() => { sound.pause(); sound.currentTime = 0; }, 10000);
</script>
"""

# Data persistence
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

def delete_all_scores():
    if os.path.exists(SCORES_FILE):
        os.remove(SCORES_FILE)

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

# Sidebar management
def sidebar_management():
    with st.sidebar:
        tab1, tab2, tab3 = st.tabs(["Manage Courts", "Manage Players", "Settings"])
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = []
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
            if 'players' not in st.session_state:
                st.session_state.players = []
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
            if "confirm_delete_scores" not in st.session_state:
                st.session_state.confirm_delete_scores = False
        
            if not st.session_state.confirm_delete_scores:
                if st.button("🗑️ Delete All Scores"):
                    st.session_state.confirm_delete_scores = True
                    st.warning("Are you sure? Click confirm to delete ALL scores.")
            else:
                c1, c2 = st.columns([1, 1])
                if c1.button("✅ Confirm Delete"):
                    delete_all_scores()
                    st.success("✅ All scores have been deleted.")
                    st.session_state.confirm_delete_scores = False
                if c2.button("❌ Cancel"):
                    st.session_state.confirm_delete_scores = False

# Display leaderboard in sidebar or right column
def display_leaderboard(player_scores):
    if not player_scores:
        return
    sorted_scores = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Leaderboard")
        for i, (player, score) in enumerate(sorted_scores, start=1):
            st.write(f"{i}. {player}: {score} points")

# Update leaderboard scores after each round
def update_scores(current_scores, players, new_scores):
    for player in players:
        current_scores[player] = current_scores.get(player, 0) + new_scores.get(player, 0)
    save_scores(current_scores)
    return current_scores

# Enter match scores and trigger leaderboard update
def match_results(players):
    st.write("### Enter Scores for Each Player")
    round_scores = {}
    for player in players:
        score = st.number_input(f"Score for {player}", min_value=0, value=0, key=f"score_{player}_{time.time()}")
        round_scores[player] = score
    if st.button("Submit Scores"):
        all_scores = load_scores()
        updated_scores = update_scores(all_scores, players, round_scores)
        st.success("Scores submitted and leaderboard updated.")
        time.sleep(1)
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

# App state initialization
if 'initialized' not in st.session_state:
    d = load_data()
    st.session_state.courts = d['courts']
    st.session_state.players = d['players']
    st.session_state.initialized = True

# Sidebar UI
sidebar_management()

# Match scheduling logic
def schedule_matches():
    players = st.session_state.players
    courts = st.session_state.courts
    if not players or not courts:
        st.warning("Please add players and courts to schedule matches.")
        return

    st.write("### Match Schedule")
    random.shuffle(players)
    matches = []
    court_assignments = min(len(players) // 2, len(courts))

    for i in range(court_assignments):
        p1 = players[2 * i]
        p2 = players[2 * i + 1]
        matches.append((courts[i], [p1, p2]))

    for court, match_players in matches:
        st.write(f"**Court {court}:** {match_players[0]} vs {match_players[1]}")

    match_players = [p for _, match in matches for p in match]
    match_results(match_players)

    st.download_button("Download as PDF", generate_pdf(matches, 1), file_name="tennis_schedule.pdf")
    st.download_button("Download as CSV", generate_csv(matches), file_name="tennis_schedule.csv")

# Display match scheduling UI and leaderboard
schedule_matches()
display_leaderboard(load_scores())
