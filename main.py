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
        json.dump({"courts": st.session_state.courts,
                   "players": st.session_state.players}, f)

# Sidebar management
def sidebar_management():
    with st.sidebar:
        tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])
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
            
            # Show remove buttons separately
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
        used = set()
        req = 4 if game_type == "Doubles" else 2

        # Warn if not enough courts
        maxm = len(players) // req
        if len(courts) < maxm:
            st.warning("Not enough courts to schedule all matches.")

        # Schedule full matches
        full_matches = []
        while courts and len(players) >= req:
            grp = players[:req]
            players = players[req:]
            court = courts.pop(0)
            full_matches.append((court, grp))
            used.update(grp)
            for i in range(len(grp)):
                for j in range(i+1, len(grp)):
                    st.session_state.history[grp[i]][grp[j]] += 1
                    st.session_state.history[grp[j]][grp[i]] += 1

        # Handle leftover (1 extra player in doubles case with Play American Doubles)
        leftovers = players
        if game_type == "Doubles" and leftover_opt == "Play American Doubles" and len(leftovers) == 1:
            if len(full_matches) >= 2:
                # Convert one full match to Singles (take 2 from it)
                match_to_singles = full_matches.pop()
                p1, p2, *_ = match_to_singles[1]
                singles_grp = [p1, p2]
                full_matches.append((match_to_singles[0], singles_grp))

                # Add 1 leftover + 2 from another match to make American Doubles
                match_to_split = full_matches.pop()
                others = [p for p in match_to_split[1] if p not in singles_grp][:2]
                ad_grp = leftovers + others
                full_matches.append((match_to_split[0], ad_grp))
                used.update(ad_grp + singles_grp)
                for i in range(len(ad_grp)):
                    for j in range(i+1, len(ad_grp)):
                        st.session_state.history[ad_grp[i]][ad_grp[j]] += 1
                        st.session_state.history[ad_grp[j]][ad_grp[i]] += 1
                for i in range(len(singles_grp)):
                    for j in range(i+1, len(singles_grp)):
                        st.session_state.history[singles_grp[i]][singles_grp[j]] += 1
                        st.session_state.history[singles_grp[j]][singles_grp[i]] += 1
            else:
                # Fallback to court if available
                if courts:
                    court = courts.pop(0)
                    full_matches.append((court, leftovers))
                else:
                    full_matches.append(("Rest", leftovers))

        elif leftovers:
            if courts:
                court = courts.pop(0)
                full_matches.append((court, leftovers))
                if len(leftovers) > 1:
                    for i in range(len(leftovers)):
                        for j in range(i+1, len(leftovers)):
                            st.session_state.history[leftovers[i]][leftovers[j]] += 1
                            st.session_state.history[leftovers[j]][leftovers[i]] += 1
            else:
                full_matches.append(("Rest", leftovers))

        matches.extend(full_matches)

    # Display current round
    if st.session_state.schedule and st.session_state.round > 0:
        r = st.session_state.round
        st.subheader(f"Round {r}")
        cr = st.session_state.schedule[r-1]
        for court, pts in cr:
            st.markdown(f"**Court {court}:** {' vs '.join(pts)}")

        # Controls
        if format_opt == "Timed":
            if st.button("Start Play"):
                total = match_time * 60
                st.markdown(CLOCK_STYLE, unsafe_allow_html=True)
                pl = st.empty()
                for t in range(total,0,-1):
                    m,s=divmod(t,60)
                    pl.markdown(f"<div class='big-clock'>{m:02d}:{s:02d}</div>", unsafe_allow_html=True)
                    time.sleep(1)
                pl.markdown("<div class='big-clock'>00:00</div>", unsafe_allow_html=True)
                st.markdown(ALERT_SOUND, unsafe_allow_html=True)
                st.success("Time's up!")
        else:
            if st.button("Begin Fast Four"):
                st.info("Fast Four match: first to 4 games wins.")

        # Exports
        st.download_button("PDF", data=generate_pdf(cr,r), file_name=f"round_{r}.pdf")
        st.download_button("CSV", data=generate_csv(cr), file_name=f"round_{r}.csv")

    # Navigation & reset
    c1, c2, c3 = st.columns(3)
    if c1.button("Previous Round") and st.session_state.round > 1:
        st.session_state.round -= 1
    if st.session_state.round < len(st.session_state.schedule):
        if c2.button("Next Round"):
            st.session_state.round += 1
    else:
        c2.button("Next Round", disabled=True)
    if c3.button("Reset Rounds"):
        st.session_state.schedule = []
        st.session_state.history = defaultdict(lambda: defaultdict(int))
        st.session_state.round = 0
        st.session_state.recent_ad = set()

# Initialize
if 'initialized' not in st.session_state:
    d = load_data()
    st.session_state.courts = d['courts']
    st.session_state.players = d['players']
    st.session_state.initialized = True

sidebar_management()
schedule_matches()
