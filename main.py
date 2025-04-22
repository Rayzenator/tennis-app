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

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"courts": [], "players": []}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({
            "courts": st.session_state.courts,
            "players": st.session_state.players
        }, f)

# Sidebar management: courts & players
def sidebar_management():
    with st.sidebar:
        tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = []
            st.header("Courts")
            for i, c in enumerate(st.session_state.courts):
                col1, col2 = st.columns([8,1])
                col1.write(c)
                if col2.button("❌", key=f"rm_court_{i}"):
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
            for i, p in enumerate(st.session_state.players):
                col1, col2 = st.columns([8,1])
                col1.write(p)
                if col2.button("❌", key=f"rm_player_{i}"):
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
    for court, players in matches:
        c.drawString(50, y, f"Court {court}: {' vs '.join(players)}")
        y -= 20
        if y < 50:
            c.showPage()
            y = h - 40
    c.save()
    buf.seek(0)
    return buf

def generate_csv(matches):
    df = pd.DataFrame([(c, ', '.join(p)) for c, p in matches], columns=["Court", "Players"])
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf

# Main scheduling logic
def schedule_matches():
    # Initialize session state
    if 'history' not in st.session_state:
        st.session_state.history = defaultdict(lambda: defaultdict(int))
    if 'schedule' not in st.session_state:
        st.session_state.schedule = []
    if 'round' not in st.session_state:
        st.session_state.round = 0
    if 'recent_ad' not in st.session_state:
        st.session_state.recent_ad = set()

    st.header("Schedule Matches")
    game_type = st.radio("Match Type", ["Doubles", "Singles"])
    format_opt = st.radio("Format", ["Timed", "Fast Four"])
    leftover_opt = st.radio("Leftover Action", ["Rest", "Play American Doubles"])
    if format_opt == "Timed":
        match_time = st.number_input("Match Time (minutes)", 5, 60, 15)
    else:
        st.info("Fast Four: first to 4 games wins.")

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
            st.warning("Not enough courts to schedule all matches.")

        # Full matches on available courts
        while courts and len(players) >= required:
            group = players[:required]
            players = players[required:]
            court = courts.pop(0)
            matches.append((court, group))
            used_players.update(group)
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    st.session_state.history[group[i]][group[j]] += 1
                    st.session_state.history[group[j]][group[i]] += 1

        # Place leftovers on next court if available
        leftovers = players
        if leftovers:
            if courts:
                court = courts.pop(0)
                if format_opt == "Fast Four":
                    group = leftovers
                elif game_type == "Singles" and len(leftovers) == 1 and leftover_opt == "Play American Doubles" and len(used_players) >= 2:
                    candidates = [p for p in used_players if p not in st.session_state.recent_ad]
                    if len(candidates) >= 2:
                        picks = random.sample(candidates, 2)
                        st.session_state.recent_ad = set(picks + leftovers)
                        group = leftovers + picks
                    else:
                        group = leftovers
                else:
                    group = leftovers
                matches.append((court, group))
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
        for c, p in current:
            st.markdown(f"**Court {c}:** {' vs '.join(p)}")

        # Start controls
        if format_opt == "Timed":
            if st.button("Start Play"):
                total = match_time * 60
                st.markdown(CLOCK_STYLE, unsafe_allow_html=True)
                placeholder = st.empty()
                for t in range(total, 0, -1):
                    mins, secs = divmod(t, 60)
                    placeholder.markdown(f"<div class='big-clock'>{mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)
                    time.sleep(1)
                placeholder.markdown("<div class='big-clock'>00:00</div>", unsafe_allow_html=True)
                st.markdown(ALERT_SOUND, unsafe_require_html=True)
                st.success("Time's up!")
        else:
            if st.button("Begin Fast Four"):
                st.info("Fast Four match: first to 4 games wins.")

        # Export options
        st.download_button("Download PDF", data=generate_pdf(current, rnd), file_name=f"round_{rnd}.pdf")
        st.download_button("Download CSV", data=generate_csv(current), file_name=f"round_{rnd}.csv")

    # Navigation & reset
    col1, col2, col3 = st.columns(3)
    if col1.button("Previous Round") and st.session_state.round > 1:
        st.session_state.round -= 1
    if st.session_state.round < len(st.session_state.schedule):
        if col2.button("Next Round"):
            st.session_state.round += 1
    else:
        col2.button("Next Round", disabled=True)
    if col3.button("Reset Rounds"):
        st.session_state.schedule = []
        st.session_state.history = defaultdict(lambda: defaultdict(int))
        st.session_state.round = 0
        st.session_state.recent_ad = set()

# Initialize on first run
if 'initialized' not in st.session_state:
    data = load_data()
    st.session_state.courts = data.get('courts', [])
    st.session_state.players = data.get('players', [])
    st.session_state.initialized = True

sidebar_management()
schedule_matches()
