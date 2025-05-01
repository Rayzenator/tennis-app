import streamlit as st
import random
import json
import os
from collections import defaultdict
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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
        tab1, tab2, tab3 = st.tabs(["Courts", "Players", "Leaderboard"])  # Simplified tab names
        
        # Tab 1 - Courts
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = load_data().get("courts", [])
            st.header("Courts")
            new_court = st.text_input("Add Court", key=f"court_in_{st.session_state.get('round', 0)}")  # Unique key
            if st.button("Add Court") and new_court:
                if new_court not in st.session_state.courts:
                    st.session_state.courts.append(new_court)
                    save_data()
                else:
                    st.warning("Court already exists.")
            if st.button("Reset Courts"):
                st.session_state.courts = []
                save_data()

            # Display Courts
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

            # Display Players
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
        sidebar_management()  # Refresh leaderboard

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

def schedule_matches():
    if 'history' not in st.session_state:
        st.session_state.history = defaultdict(lambda: defaultdict(int))
    if 'schedule' not in st.session_state:
        st.session_state.schedule = []
    if 'round' not in st.session_state:
        st.session_state.round = 0
    if 'recent_ad' not in st.session_state:
        st.session_state.recent_ad = set()

    # Initialize player scores if not already initialized
    if 'player_scores' not in st.session_state:
        st.session_state.player_scores = {player: 0 for player in st.session_state.players}

    st.header("Schedule Matches")
    game_type = st.radio("Match Type", ["Doubles", "Singles"])
    format_opt = st.radio("Format", ["Timed", "Fast Four"])
    leftover_opt = st.radio("Leftover Action", ["Rest", "Play American Doubles"])
    if format_opt == "Timed":
        match_time = st.number_input("Match Time (minutes)", 5, 60, 15)
    else:
        st.info("Fast Four: first to 4 games wins.")

    if st.button("Generate Round"):
        # Reset player scores to zero for the new round
        st.session_state.player_scores = {player: 0 for player in st.session_state.players}

        players = st.session_state.players.copy()
        random.shuffle(players)
        courts = st.session_state.courts.copy()
        matches = []
        used = set()
        req = 4 if game_type == "Doubles" else 2
        maxm = len(players) // req
        if len(courts) < maxm:
            st.warning("Not enough courts to schedule all matches.")

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

        leftovers = players
        if leftovers:
            if game_type == "Singles" and len(leftovers) == 1 and leftover_opt == "Play American Doubles":
                inserted = False
                for idx, (court, grp) in enumerate(matches):
                    if len(grp) == 2:
                        if not any(p in st.session_state.recent_ad for p in grp):
                            new_grp = grp + leftovers
                            matches[idx] = (court, new_grp)
                            st.session_state.recent_ad = set(new_grp)
                            inserted = True
                            break
                if not inserted and courts:
                    court = courts.pop(0)
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

    if st.session_state.schedule and st.session_state.round > 0:
        r = st.session_state.round
        st.subheader(f"Round {r}")
        cr = st.session_state.schedule[r - 1]

        # Display matchups before the scores table
        st.write("### Matchups:")
        for court, players in cr:
            st.write(f"Court {court}: {' vs '.join(players)}")
        
        # Display all matches in a table for score entry
        scores = {}
        for court, players in cr:
            for player in players:
                score_key = f"score_{r}_{court}_{player}"
                scores[score_key] = st.number_input(f"Score for {player} (Court: {court})", min_value=0, value=0, key=score_key)
        
        # Submit button for all scores
        if st.button(f"Submit Scores for Round {r}"):
            # Collect all scores
            round_scores = {player: scores[f"score_{r}_{court}_{player}"] for court, players in cr for player in players}
            player_scores = update_scores(load_scores(), [player for court, players in cr for player in players], round_scores)
            save_scores(player_scores)
            st.success("Scores submitted successfully!")
            sidebar_management()  # Refresh leaderboard

        # CSV and PDF export buttons
        st.download_button(
            "Download CSV", generate_csv(cr), file_name=f"round_{r}.csv", mime="text/csv"
        )

        st.download_button(
            "Download PDF", generate_pdf(cr, r), file_name=f"round_{r}.pdf", mime="application/pdf"
        )

    if st.button("Reset Rounds"):
        st.session_state.schedule = []
        st.session_state.round = 0
        st.session_state.recent_ad = set()
        st.success("Rounds reset. You can start generating again.")

sidebar_management()
schedule_matches()
