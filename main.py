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

# Embed alert sound
ALERT_SOUND = """
<audio id=\"beep\" autoplay loop>
  <source src=\"https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg\" type=\"audio/ogg\">  
  Your browser does not support the audio element.
</audio>
<script>
  const sound = document.getElementById("beep");
  sound.play();
  setTimeout(() => { sound.pause(); sound.currentTime = 0; }, 10000);
</script>
"""

# Large digital clock style
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

# Dark mode style
DARK_MODE_STYLE = """
<style>
body { background-color: #1e1e1e; color: white; }
.sidebar .sidebar-content { background-color: #2e2e2e; color: white; }
</style>
"""

# Page configuration and style
st.set_page_config(page_title="Tennis Scheduler", layout="wide")
st.markdown(DARK_MODE_STYLE, unsafe_allow_html=True)

# Data persistence file
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"courts": [], "players": []}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({"courts": st.session_state.courts, "players": st.session_state.players}, f)

# Sidebar for managing courts and players
def sidebar_management():
    with st.sidebar:
        tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = []
            st.header("Courts")
            for i, court in enumerate(st.session_state.courts):
                c1, c2 = st.columns([8, 1])
                c1.write(court)
                if c2.button("❌", key=f"rm_court_{i}"):
                    st.session_state.courts.pop(i)
                    save_data()
            new_court = st.text_input("Add Court", key="court_in")
            if st.button("Add Court") and new_court:
                if new_court not in st.session_state.courts:
                    st.session_state.courts.append(new_court)
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
                p1, p2 = st.columns([8,1])
                p1.write(player)
                if p2.button("❌", key=f"rm_player_{i}"):
                    st.session_state.players.pop(i)
                    save_data()
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

# Helpers for exporting schedule
def generate_pdf(matches, round_no):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Tennis Schedule - Round {round_no}")
    y -= 30
    c.setFont("Helvetica", 12)
    for court, pts in matches:
        c.drawString(50, y, f"Court {court}: {' vs '.join(pts)}")
        y -= 20
        if y < 50:
            c.showPage()
            y = height - 40
    c.save()
    buffer.seek(0)
    return buffer

def generate_csv(matches):
    df = pd.DataFrame([(court, ', '.join(players)) for court, players in matches], columns=["Court", "Players"])
    buffer = BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer

# Main scheduling function
def schedule_matches():
    # Initialize session state variables
    if 'history' not in st.session_state:
        st.session_state.history = defaultdict(lambda: defaultdict(int))
    if 'schedule' not in st.session_state:
        st.session_state.schedule = []
    if 'round' not in st.session_state:
        st.session_state.round = 1
    if 'recent_ad' not in st.session_state:
        st.session_state.recent_ad = set()

    st.header("Schedule Matches")
    game_type = st.radio("Match Type", ["Doubles", "Singles"])
    leftover_action = st.radio("Leftover Action", ["Rest", "Play American Doubles"])
    match_time = st.number_input("Match Time (minutes)", min_value=5, max_value=60, value=15)

    # Generate next round
    if st.button("Generate Next Round"):
        players = st.session_state.players.copy()
        random.shuffle(players)
        courts = st.session_state.courts.copy()
        matches = []
        used_players = set()
        required = 4 if game_type == "Doubles" else 2

        # Warn if not enough courts
        max_matches = len(players) // required
        if len(courts) < max_matches:
            st.warning("Not enough courts. Add more courts to utilize all players.")

        # Schedule full matches
        while courts and len(players) >= required:
            group = players[:required]
            players = players[required:]
            court = courts.pop(0)
            matches.append((court, group))
            used_players.update(group)
            # record head-to-head
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    st.session_state.history[group[i]][group[j]] += 1
                    st.session_state.history[group[j]][group[i]] += 1

        # Handle leftovers on next available court
        leftovers = players
        if leftovers:
            if courts:
                court = courts.pop(0)
                if game_type == "Singles" and len(leftovers) == 1 and leftover_action == "Play American Doubles" and len(used_players) >= 2:
                    candidates = [p for p in used_players if p not in st.session_state.recent_ad]
                    if len(candidates) < 2:
                        candidates = list(used_players)
                    pick = random.sample(candidates, 2)
                    st.session_state.recent_ad = set(pick + leftovers)
                    group = leftovers + pick
                else:
                    group = leftovers
                matches.append((court, group))
                # record if more than one player
                if len(group) > 1:
                    for i in range(len(group)):
                        for j in range(i + 1, len(group)):
                            st.session_state.history[group[i]][group[j]] += 1
                            st.session_state.history[group[j]][group[i]] += 1
            else:
                matches.append(("Rest", leftovers))

        st.session_state.schedule.append(matches)
        st.session_state.round = len(st.session_state.schedule)

    # Display current round
    if st.session_state.schedule and st.session_state.round > 0:
        rnd = st.session_state.round
        st.subheader(f"Round {rnd}")
        current = st.session_state.schedule[rnd - 1]
        for court, players in current:
            st.markdown(f"**Court {court}:** {' vs '.join(players)}")

        # Timer
        if st.button("Start Play"):
            total = match_time * 60
            st.markdown(CLOCK_STYLE, unsafe_allow_html=True)
            timer_slot = st.empty()
            for remaining in range(total, 0, -1):
                mins, secs = divmod(remaining, 60)
                timer_slot.markdown(f"<div class='big-clock'>{mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)
                time.sleep(1)
            timer_slot.markdown("<div class='big-clock'>00:00</div>", unsafe_allow_html=True)
            st.markdown(ALERT_SOUND, unsafe_allow_html=True)
            st.success("Time's up! Round is over.")

        # Export options
        st.download_button("Download as PDF", data=generate_pdf(current, rnd), file_name=f"round_{rnd}.pdf")
        st.download_button("Download as CSV", data=generate_csv(current), file_name=f"round_{rnd}.csv")

    # Navigation and reset
    prev_col, next_col, reset_col = st.columns([1,1,1])
    if prev_col.button("Previous Round") and st.session_state.round > 1:
        st.session_state.round -= 1
    if st.session_state.round < len(st.session_state.schedule):
        if next_col.button("Next Round"):
            st.session_state.round += 1
    else:
        next_col.button("Next Round", disabled=True)
    if reset_col.button("Reset Rounds"):
        st.session_state.schedule = []
        st.session_state.history = defaultdict(lambda: defaultdict(int))
        st.session_state.round = 0
        st.session_state.recent_ad = set()

# Initialization
if 'initialized' not in st.session_state:
    data = load_data()
    st.session_state.courts = data.get('courts', [])
    st.session_state.players = data.get('players', [])
    st.session_state.initialized = True

# Run app
sidebar_management()
schedule_matches()
