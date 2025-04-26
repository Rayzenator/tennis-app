import streamlit as st
import time
import random
import json
import os
from collections import defaultdict
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

def sidebar_management():
    with st.sidebar:
        tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])

        # --- Courts Tab ---
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = []
            st.header("Courts")
            from streamlit_sortables import sort_items

            st.markdown("Drag to reorder:")
            new_order = sort_items(
                st.session_state.courts,
                direction="vertical",
                key="sortable_courts_tab"
            )

            if new_order != st.session_state.courts:
                st.session_state.courts = new_order
                save_data()

            for i, court in enumerate(st.session_state.courts):
                c1, c2 = st.columns([8, 1])
                c1.write(court)
                if c2.button("❌", key=f"remove_court_{i}"):
                    st.session_state.courts.pop(i)
                    save_data()
                    st.session_state.court_input = ""  # reset input

            new = st.text_input("Add Court", key="court_input")
            if st.button("Add Court", key="btn_add_court") and new:
                if new not in st.session_state.courts:
                    st.session_state.courts.append(new)
                    save_data()
                    st.session_state.court_input = ""  # Clear input
                else:
                    st.warning("Court already exists.")

            if st.button("Reset Courts", key="btn_reset_courts"):
                st.session_state.courts = []
                save_data()

        # --- Players Tab ---
        with tab2:
            if 'players' not in st.session_state:
                st.session_state.players = []
            st.header("Players")

            for i, player in enumerate(st.session_state.players):
                p1, p2 = st.columns([8, 1])
                p1.write(player)
                if p2.button("❌", key=f"remove_player_{i}"):
                    st.session_state.players.pop(i)
                    save_data()
                    st.session_state.player_input = ""  # reset input

            newp = st.text_input("Add Player", key="player_input")
            if st.button("Add Player", key="btn_add_player") and newp:
                if newp not in st.session_state.players:
                    st.session_state.players.append(newp)
                    save_data()
                    st.session_state.player_input = ""  # Clear input
                else:
                    st.warning("Player already exists.")

            if st.button("Reset Players", key="btn_reset_players"):
                st.session_state.players = []
                save_data()

# Initialize
if 'initialized' not in st.session_state:
    d = load_data()
    st.session_state.courts = d['courts']
    st.session_state.players = d['players']
    st.session_state.initialized = True

sidebar_management()
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
        while courts and len(players) >= req:
            grp = players[:req]
            players = players[req:]
            court = courts.pop(0)
            matches.append((court, grp))
            used.update(grp)
            for i in range(len(grp)):
                for j in range(i+1, len(grp)):
                    st.session_state.history[grp[i]][grp[j]] += 1
                    st.session_state.history[grp[j]][grp[i]] += 1

        # Handle leftover
        leftovers = players
        if leftovers:
            if game_type == "Singles" and len(leftovers) == 1 and leftover_opt == "Play American Doubles":
                # Insert into existing singles match to form AD
                inserted = False
                for idx, (court, grp) in enumerate(matches):
                    if len(grp) == 2:  # must be a singles match
                        # Check if any player in grp was in recent_ad
                        if not any(p in st.session_state.recent_ad for p in grp):
                            new_grp = grp + leftovers
                            matches[idx] = (court, new_grp)
                            st.session_state.recent_ad = set(new_grp)
                            inserted = True
                            break
                if not inserted and courts:
                    court = courts.pop(0)
                    # fallback to normal AD match
                    candidates = [p for p in used if p not in st.session_state.recent_ad]
                    if len(candidates) < 2:
                        candidates = list(used)
                    picks = random.sample(candidates, 2)
                    st.session_state.recent_ad = set(picks + leftovers)
                    grp = leftovers + picks
                    matches.append((court, grp))
                elif not inserted:
                    matches.append(("Rest", leftovers))
            elif courts:
                court = courts.pop(0)
                grp = leftovers
                matches.append((court, grp))
            else:
                matches.append(("Rest", leftovers))

        st.session_state.schedule.append(matches)
        st.session_state.round = len(st.session_state.schedule)

    # Display current round
    if st.session_state.schedule and st.session_state.round > 0:
        r = st.session_state.round
        st.subheader(f"Round {r}")
        cr = st.session_state.schedule[r-1]
        for court, pts in cr:
            st.markdown(f"**Court {court}:** {' vs '.join(pts)}")
            
            def start_timer(match_time: int, round_num: int):
                """
                Function to start or pause the timer, prevent screen sleep, and display the countdown in the app.
                match_time: The match time in minutes
                """
                if 'is_paused' not in st.session_state:
                    st.session_state.is_paused = False  # Initial state for pause
                    st.session_state.stop_timer = False  # Reset stop flag
                    st.session_state.duration = match_time * 60  # Set initial countdown duration

                # Ensure a unique timer ID
                countdown_id = f"countdown_{round_num}"

sidebar_management()
schedule_matches()
