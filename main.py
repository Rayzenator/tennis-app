import streamlit as st
import random
import time
from collections import defaultdict
import json
import os

# Embed base64-encoded sound for alert
ALERT_SOUND = """
<audio id="beep" autoplay loop>
  <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" type="audio/ogg">
  Your browser does not support the audio element.
</audio>
<script>
  const sound = document.getElementById("beep");
  sound.play();
  setTimeout(() => {
    sound.pause();
    sound.currentTime = 0;
  }, 10000);
</script>
"""

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

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"courts": [], "players": []}

def save_data():
    data = {
        "courts": st.session_state.courts,
        "players": st.session_state.players
    }
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def sidebar_management():
    with st.sidebar:
        tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])

        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = []
            st.header("Courts")
            for i, court in enumerate(st.session_state.courts):
                col1, col2 = st.columns([8, 1])
                col1.text(court)
                if col2.button("X", key=f"remove_court_{i}"):
                    st.session_state.courts = st.session_state.courts[:i] + st.session_state.courts[i+1:]
                    save_data()
            court_input = st.text_input("Add Court Number", key="court_input")
            if st.button("Add Court") and court_input:
                if court_input not in st.session_state.courts:
                    st.session_state.courts.append(court_input)
                    save_data()
                else:
                    st.warning("Court already exists.")

        with tab2:
            if 'players' not in st.session_state:
                st.session_state.players = []
            st.header("Players")
            for i, player in enumerate(st.session_state.players):
                col1, col2 = st.columns([8, 1])
                col1.text(player)
                if col2.button("X", key=f"remove_player_{i}"):
                    st.session_state.players = st.session_state.players[:i] + st.session_state.players[i+1:]
                    save_data()
            player_input = st.text_input("Add Player Name", key="player_input")
            if st.button("Add Player") and player_input:
                if player_input not in st.session_state.players:
                    st.session_state.players.append(player_input)
                    save_data()
                else:
                    st.warning("Player already exists.")

def schedule_matches():
    if 'history' not in st.session_state:
        st.session_state.history = defaultdict(lambda: defaultdict(int))
    if 'schedule' not in st.session_state:
        st.session_state.schedule = []
    if 'round' not in st.session_state:
        st.session_state.round = 1

    st.header("Schedule Matches")
    game_type = st.radio("Select Match Type", ["Doubles", "Singles"])
    leftover_option = st.radio("Leftover Players Should", ["Rest", "Play American Doubles"])
    match_time = st.number_input("Match Time (minutes)", min_value=5, max_value=60, value=15)

    if st.button("Generate Next Round"):
        players = st.session_state.players.copy()
        random.shuffle(players)
        courts = st.session_state.courts.copy()
        matches = []
        used_players = set()

        def already_played(p1, p2):
            return st.session_state.history[p1][p2] > 0

        def record_match(players_in_match):
            for i in range(len(players_in_match)):
                for j in range(i + 1, len(players_in_match)):
                    st.session_state.history[players_in_match[i]][players_in_match[j]] += 1
                    st.session_state.history[players_in_match[j]][players_in_match[i]] += 1

        while courts and len(players) >= (4 if game_type == "Doubles" else 2):
            if game_type == "Doubles" and len(players) >= 4:
                match_players = players[:4]
                players = players[4:]
            elif game_type == "Singles" and len(players) >= 2:
                match_players = players[:2]
                players = players[2:]
            else:
                break
            court = courts.pop(0)
            matches.append((court, match_players))
            used_players.update(match_players)
            record_match(match_players)

        leftovers = players
        if leftovers:
            if game_type == "Singles":
                if len(leftovers) == 1:
                    matches.append(("Overflow", leftovers + random.sample(list(used_players), 2)))
            else:
                if len(leftovers) == 3:
                    matches.append(("Overflow", leftovers))
                elif len(leftovers) == 2:
                    matches.append(("Overflow", leftovers))
                elif len(leftovers) == 1:
                    if leftover_option == "Rest":
                        matches.append(("Rest", leftovers))
                    else:
                        matches.append(("Rotate", leftovers + random.sample(list(used_players), 3)))

        st.session_state.schedule.append(matches)
        st.session_state.round = len(st.session_state.schedule)

    st.subheader(f"Round {st.session_state.round}")
    if st.session_state.schedule:
        current_matches = st.session_state.schedule[st.session_state.round - 1]
        for court, players in current_matches:
            st.markdown(f"**Court {court}:** {' vs. '.join(players)}")

        if st.button("Start Play"):
            countdown = match_time * 60
            st.markdown(CLOCK_STYLE, unsafe_allow_html=True)
            timer_placeholder = st.empty()
            for remaining in range(countdown, 0, -1):
                mins, secs = divmod(remaining, 60)
                timer_placeholder.markdown(f"<div class='big-clock'>{mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)
                time.sleep(1)
            timer_placeholder.markdown("<div class='big-clock'>00:00</div>", unsafe_allow_html=True)
            st.markdown(ALERT_SOUND, unsafe_allow_html=True)
            st.success("Time's up! Round is over.")

    col1, col2 = st.columns(2)
    if col1.button("Previous Round"):
        if st.session_state.round > 1:
            st.session_state.round -= 1
    if st.session_state.round < len(st.session_state.schedule):
        if col2.button("Next Round"):
            st.session_state.round += 1
    else:
        col2.button("Next Round", disabled=True)

if 'initialized' not in st.session_state:
    loaded = load_data()
    st.session_state.courts = loaded.get("courts", [])
    st.session_state.players = loaded.get("players", [])
    st.session_state.initialized = True

sidebar_management()
schedule_matches()
