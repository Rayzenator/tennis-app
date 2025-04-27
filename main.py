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

st.markdown(
    """
    <style>
    /* General page */
    body {
        background-color: #FFFFFF;
        color: #000000;
    }

    /* Sidebar */
    .sidebar .sidebar-content {
        background-color: #F8F9FA;
        color: #000000;
    }

    /* Main headings (like Match Type, Format, Leftover Action) */
    h1, h2, h3 {
        font-size: 32px !important;
        padding: 16px !important;
        background-color: #FFF9C4 !important; /* Softer Pastel Yellow */
        color: #000000 !important; /* Black text */
        border-radius: 10px;
        width: 100%;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.2);
    }

    /* Body text */
    .stMarkdown, .stTextInput, .stNumberInput, .stSelectbox, .stButton, .stRadio, .stTabs, .stCheckbox, .stTextArea, .stDataFrame {
        font-size: 22px !important;
        color: #000000 !important;
    }

    /* Radio options themselves */
    div[role="radiogroup"] > div {
        font-size: 22px !important;
        color: #000000 !important;
    }

    /* Selectboxes and text inputs */
    select, input[type="text"], input[type="number"] {
        font-size: 22px !important;
        height: 50px !important;
        padding: 12px !important;
        border-radius: 10px !important;
        color: #000000 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #CCC;
    }

    /* Buttons */
    .stButton>button {
        font-size: 24px !important;
        padding: 14px 24px !important;
        border-radius: 12px !important;
        color: #FFFFFF !important;
        background-color: #007BFF !important;
        border: none;
    }

    /* Match Info (Court matches text) */
    .element-container p {
        font-size: 24px !important;
        font-weight: bold;
        color: #000000 !important;
    }

    /* Timed match info box */
    .timed-info {
        font-size: 26px !important;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        background-color: #4CAF50;
        color: #FFFFFF;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        font-size: 22px !important;
        color: #000000 !important;
    }

    /* Increase the size of + and - buttons */
    .stNumberInput button {
        font-size: 28px !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
        background-color: #007BFF !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
        tab1, tab2, tab3 = st.tabs(["Manage Courts", "Manage Players", "Leaderboard"])
        
        # Tab 1 - Manage Courts
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
        
        # Tab 2 - Manage Players
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

        # Tab 3 - Leaderboard
        with tab3:
            player_scores = load_scores()
            display_leaderboard(player_scores)

            if st.button("Delete All Player Scores"):
                delete_all_scores()

def display_leaderboard(player_scores):
    sorted_scores = sorted(player_scores.items(), key=lambda x: x[1], reverse=True)
    st.write("### Leaderboard")
    for i, (player, score) in enumerate(sorted_scores, start=1):
        st.write(f"{i}. {player}: {score} points")

def delete_all_scores():
    # Delete all scores by clearing the scores file
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
        display_leaderboard(player_scores)

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

# Define the schedule and history state if not already present
def schedule_matches():
    if 'history' not in st.session_state:
        st.session_state.history = defaultdict(lambda: defaultdict(int))
    if 'schedule' not in st.session_state:
        st.session_state.schedule = []
    if 'round' not in st.session_state:
        st.session_state.round = 0
    if 'recent_ad' not in st.session_state:
        st.session_state.recent_ad = set()

    if 'player_scores' not in st.session_state:
        st.session_state.player_scores = {player: 0 for player in st.session_state.players}

    st.header("Schedule Matches")

    # Sidebar for Player and Court Selection
    st.sidebar.header("Select Players and Courts")

    available_players = st.session_state.players
    available_courts = st.session_state.courts

    # Sidebar: Player selection
    selected_players = []
    st.sidebar.subheader("Select Players:")
    for player in available_players:
        if st.sidebar.checkbox(f"Select {player}", key=player):
            selected_players.append(player)

    # Sidebar: Court selection
    selected_courts = []
    st.sidebar.subheader("Select Courts:")
    for court in available_courts:
        if st.sidebar.checkbox(f"Select Court {court}", key=f"court_{court}"):
            selected_courts.append(court)

    # Match type and format
    game_type = st.radio("Match Type", ["Doubles", "Singles"])
    format_opt = st.radio("Format", ["Timed", "Fast Four"])

    leftover_opt = st.checkbox("Leftover Action (Rest or Play American Doubles)", value=False)
    
    if format_opt == "Timed":
        match_time = st.number_input("Match Time (minutes)", 5, 60, 15)
    else:
        st.info("Fast Four: first to 4 games wins.")

    if st.button("Generate Next Round"):
        if not selected_players or not selected_courts:
            st.warning("Please select at least one player and one court.")
            return

        # Reset player scores to zero for the new round
        st.session_state.player_scores = {player: 0 for player in selected_players}

        matches = []
        random.shuffle(selected_players)
        for court in selected_courts:
            if len(selected_players) >= 4:  # For Doubles match
                grp = selected_players[:4]
                selected_players = selected_players[4:]
                matches.append((court, grp))

        st.session_state.schedule.append(matches)
        st.session_state.round = len(st.session_state.schedule)

    # Show scheduled matches
    if st.session_state.schedule and st.session_state.round > 0:
        r = st.session_state.round
        st.subheader(f"Round {r}")
        cr = st.session_state.schedule[r-1]
        for court, grp in cr:
            st.markdown(f"**Court {court}:** {' vs '.join(grp)}")

        if format_opt == "Timed":
            st.markdown(
                f"""
                <style>
                    .timed-info {{
                        font-size: 20px;
                        font-weight: bold;
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px;
                        border-radius: 5px;
                    }}
                </style>
                <div class="timed-info">
                    Timed match: Set Stopwatch to {match_time} minutes.
                </div>
                """, unsafe_allow_html=True)
        else:
            if st.button("Begin Fast Four"):
                st.info("Fast Four match: first to 4 games wins.")

        st.download_button("PDF", data=generate_pdf(cr,r), file_name=f"round_{r}.pdf")
        st.download_button("CSV", data=generate_csv(cr), file_name=f"round_{r}.csv")

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

sidebar_management()
schedule_matches()
