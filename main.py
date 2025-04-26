import streamlit as st
import random
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

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

# Schedule matches and generate rounds
def schedule_matches():
    players = st.session_state.players
    courts = st.session_state.courts
    if not players or not courts:
        st.warning("Please add players and courts to schedule matches.")
        return

    # Select match type and format
    game_type = st.radio("Match Type", ["Doubles", "Singles"], key="game_type")
    format_opt = st.radio("Format", ["Timed", "Fast Four"], key="format_opt")
    leftover_opt = st.radio("Leftover Action", ["Rest", "Play American Doubles"], key="leftover_opt")

    if format_opt == "Timed":
        match_time = st.number_input("Match Time (minutes)", 5, 60, 15)
    else:
        st.info("Fast Four: first to 4 games wins.")

    # Resting players logic
    resting_players = [player for player, status in st.session_state.get("player_status", {}).items() if status == "Rest"]
    available_players = [player for player in players if player not in resting_players]

    return available_players, game_type, format_opt, leftover_opt

# Control buttons to generate and navigate rounds
def control_buttons():
    if 'rounds' not in st.session_state:
        st.session_state.rounds = []
        st.session_state.current_round = 0  # Track current round

    # Generate Round button
    if st.button("Generate Round"):
        available_players, game_type, format_opt, leftover_opt = schedule_matches()

        st.write("### Available Players")
        st.write(', '.join(available_players))  # Show players cleanly in a comma-separated format

        # Shuffle players and schedule matches
        random.shuffle(available_players)
        matches = []
        court_assignments = min(len(available_players) // 2, len(st.session_state.courts))

        for i in range(court_assignments):
            p1 = available_players[2 * i]
            p2 = available_players[2 * i + 1]
            matches.append((st.session_state.courts[i], [p1, p2]))

        st.session_state.rounds.append(matches)  # Add generated matches to the rounds list
        st.session_state.current_round = len(st.session_state.rounds) - 1  # Set current round to the latest

        st.write("### Matches for this Round")
        for court, match_players in matches:
            st.write(f"**Court {court}:** {match_players[0]} vs {match_players[1]}")

        # Display Download Options
        st.download_button("Download as PDF", generate_pdf(matches, len(st.session_state.rounds)), file_name="tennis_schedule.pdf")
        st.download_button("Download as CSV", generate_csv(matches), file_name="tennis_schedule.csv")

    # Navigation buttons for rounds
    if st.session_state.rounds:
        if st.session_state.current_round > 0 and st.button("Previous Round"):
            st.session_state.current_round -= 1

        if st.session_state.current_round < len(st.session_state.rounds) - 1 and st.button("Next Round"):
            st.session_state.current_round += 1

        # Show matches for the current round
        current_round_matches = st.session_state.rounds[st.session_state.current_round]
        st.write(f"### Matches for Round {st.session_state.current_round + 1}")
        for court, match_players in current_round_matches:
            st.write(f"**Court {court}:** {match_players[0]} vs {match_players[1]}")

# Reset Rounds button
if st.button("Reset Rounds"):
    st.session_state.rounds = []
    st.session_state.current_round = 0
    st.write("Rounds have been reset!")

# PDF & CSV export helpers
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

# Run the app
if 'initialized' not in st.session_state:
    d = load_data()
    st.session_state.courts = d['courts']
    st.session_state.players = d['players']
    st.session_state.initialized = True

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

sidebar_management()  # Add sidebar management back
control_buttons()  # Call to control buttons and round navigation
