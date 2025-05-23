import streamlit as st
import random
import json
import os
import pandas as pd
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Tennis Scheduler", layout="wide")

# File paths
PLAYER_FILE = "players.json"
COURT_FILE = "courts.json"
SCORE_FILE = "scores.csv"

# Load and save functions
def load_json(path, default=[]):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def load_scores():
    if os.path.exists(SCORE_FILE):
        return pd.read_csv(SCORE_FILE, index_col=0)
    return pd.DataFrame(columns=['games'])

def save_scores(df):
    df.to_csv(SCORE_FILE)

# Scheduler logic
def schedule_round(players, courts, match_type='Singles', allow_american=False, history=None, player_roles=None):
    if history is None:
        history = set()
    if player_roles is None:
        player_roles = {p: [] for p in players}

    matches = []
    players = players.copy()

    def penalty(p):
        recent = player_roles.get(p, [])
        return recent[-1:] == ['rest'] or recent[-1:] == ['american']

    players.sort(key=penalty)
    random.shuffle(players)

    court_capacity = 2 if match_type == 'Singles' else 4
    max_players = len(courts) * court_capacity
    usable_players = players[:max_players]
    leftover_players = players[max_players:]

    step = 2 if match_type == 'Singles' else 4

    for i in range(0, len(usable_players), step):
        match = tuple(usable_players[i:i+step])
        if len(match) == step:
            matches.append(match)
            for p in match:
                player_roles.setdefault(p, []).append("match")

    lp = leftover_players
    if allow_american:
        if len(lp) == 1:
            convertible_idx = next((i for i, m in enumerate(matches) if len(m) == 4), None)
            if convertible_idx is not None:
                match_to_split = matches.pop(convertible_idx)
                singles_match = match_to_split[:2]
                american_group = match_to_split[2:] + lp
                matches.append(singles_match)
                matches.append(tuple(american_group))
                for p in singles_match:
                    player_roles.setdefault(p, []).append("match")
                for p in american_group:
                    player_roles.setdefault(p, []).append("american")
            else:
                for p in lp:
                    player_roles.setdefault(p, []).append("rest")
        elif len(lp) == 2:
            matches.append(tuple(lp))
            for p in lp:
                player_roles.setdefault(p, []).append("match")
        elif len(lp) == 3:
            matches.append(tuple(lp))
            for p in lp:
                player_roles.setdefault(p, []).append("american")
        else:
            for p in lp:
                player_roles.setdefault(p, []).append("rest")
    else:
        for p in lp:
            player_roles.setdefault(p, []).append("rest")

    all_matched_players = set(p for m in matches for p in m)
    resting = set(players) - all_matched_players
    for p in resting:
        player_roles.setdefault(p, []).append("rest")

    for m in matches:
        history.add(frozenset(m))

    named_matches = [(court, match) for court, match in zip(courts, matches)]
    return named_matches, history, player_roles

def update_scores(nightly_df, all_time_df, submitted_scores):
    for player, score in submitted_scores.items():
        if player not in nightly_df.index:
            nightly_df.loc[player] = 0
        nightly_df.at[player, 'games'] += score
        if player not in all_time_df.index:
            all_time_df.loc[player] = 0
        all_time_df.at[player, 'games'] += score

def app():
    st.markdown("""
    <style>
        /* General styling for the app */
        html, body, [class*="css"] {
            font-size: 20px !important;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            background-color: #000000;  /* Dark background for the main app screen */
            color: #ffffff;  /* White text on dark background */
        }
    
        .stButton>button {
            background-color: #32CD32;
            color: white;
            border-radius: 0.5rem;
            padding: 0.5rem 1rem;
            font-size: 18px;
        }
    
        /* Set white text color for headings on the main app screen */
        h1, h2, h3, h4, h5, h6, .stMarkdown h3 {
            color: #ffffff !important;
        }
    
        /* Specific styling for labels in input components, select boxes, etc. */
        /* Targeting labels using a more specific class */
        .stTextInput label, 
        .stSelectbox label, 
        .stCheckbox label, 
        .stMultiselect label,
        .stRadio label,
        .stSlider label {
            color: #ffffff !important;  /* White text for all labels */
        }
    
        /* Ensure black text for inputs and selects (on light backgrounds) */
        input[type=number], 
        .stTextInput input, 
        .stSelectbox>div>div, 
        .stCheckbox>label>div, 
        .stMultiselect>div>div, 
        .stRadio>div, 
        .stSlider>div {
            font-size: 20px !important;
            color: #000000 !important;  /* Black text for inputs and selects */
            background-color: #ffffff !important; /* White background for inputs/selects */
        }
    
        /* Set bright yellow color for "Set Stopwatch" text and icons */
        .stTextInput div[role="alert"], 
        .stTextInput div[role="button"], 
        .stTextInput span, 
        .stTextInput i {
            color: #ff0 !important;  /* Force bright yellow for stopwatch text and icons */
        }
    
        /* Red buttons for deleting players and courts */
        div[data-testid="delete-player"] > button,
        div[data-testid="delete-court"] > button {
            background-color: #d9534f;
            color: white;
            font-weight: bold;
            border-radius: 0.5rem;
        }
    
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: #d3d3d3 !important;
            color: #000000 !important;
        }
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div {
            color: #000000 !important;
        }
        /* Change the heading text color in the sidebar */
        section[data-testid="stSidebar"] h2 {
            color: #000000 !important; /* Black color for the "Manage Players and Tabs" heading */
        }
    
        /* Sidebar Tab - Keep same format but change tab color */
        .stTabs>div>div {
            background-color: #ffff00 !important; /* Bright yellow background for the tabs */
            color: #000000 !important; /* Black text for tabs */
        }
    
        /* Adjust slider size to provide more space for text */
        .stSlider {
            width: 100% !important;
            height: 60px !important;  /* Increase the height of the slider */
        }
    
        /* Add space for the slider labels to display more clearly */
        .stSlider>div>div>div {
            padding-top: 10px !important;  /* Add space between the slider and the text */
            font-size: 22px !important;  /* Increase font size for slider labels */
            color: #ffffff !important;  /* White text for slider labels */
        }
    </style>
    
    """, unsafe_allow_html=True)

    st.title("🎾 Tennis Round-Robin Scheduler")

    players = load_json(PLAYER_FILE)
    courts = load_json(COURT_FILE)

    if 'all_time' not in st.session_state:
        st.session_state.all_time = load_scores()

    if 'nightly' not in st.session_state:
        st.session_state.nightly = pd.DataFrame(0, index=players, columns=['games'])
    if 'history' not in st.session_state or not isinstance(st.session_state.history, list):
        st.session_state.history = []
    if 'rounds' not in st.session_state:
        st.session_state.rounds = []
    if 'round_number' not in st.session_state:
        st.session_state.round_number = 1
    if 'player_roles' not in st.session_state:
        st.session_state.player_roles = {p: [] for p in players}

    with st.sidebar:
        st.header("Manage Players & Courts")
        new_player = st.text_input("Add Player")
        if st.button("Add Player") and new_player:
            if new_player not in players:
                players.append(new_player)
                save_json(PLAYER_FILE, players)
            else:
                st.warning("Player already exists!")

        player_to_delete = st.selectbox("Delete Player", players, key="delete-player-select")
        if st.button("Delete Player", key="delete-player"):
            if player_to_delete in players:
                players.remove(player_to_delete)
                save_json(PLAYER_FILE, players)
                st.success(f"Deleted {player_to_delete}")

        new_court = st.text_input("Add Court")
        if st.button("Add Court") and new_court:
            if new_court not in courts:
                courts.append(new_court)
                save_json(COURT_FILE, courts)
            else:
                st.warning("Court already exists!")

        court_to_delete = st.selectbox("Delete Court", courts, key="delete-court-select")
        if st.button("Delete Court", key="delete-court"):
            if court_to_delete in courts:
                courts.remove(court_to_delete)
                save_json(COURT_FILE, courts)
                st.success(f"Deleted {court_to_delete}")

    selected_players = st.multiselect("Select Players for This Night", sorted(set(players)))
    selected_courts = st.multiselect("Select Active Courts", sorted(set(courts)))
    match_type = st.selectbox("Match Type", ["Singles", "Doubles"])
    format_type = st.selectbox("Format", ["Fast Four", "Timed"], index=1)
    if format_type == "Timed":
        match_duration = st.slider("Match Duration (minutes)", min_value=5, max_value=60, value=15, step=5)
        st.info(f"⏱ Set stopwatch to **{match_duration} minutes**")
    allow_american = st.checkbox("Allow American Doubles")

    if st.button("Generate Round"):
        previous_history = st.session_state.history
        if not isinstance(previous_history, list):
            previous_history = []

        history_set = set(frozenset(h) for h in previous_history)

        matches, history_set, st.session_state.player_roles = schedule_round(
            selected_players, selected_courts, match_type, allow_american,
            history_set, st.session_state.player_roles)

        st.session_state.history = [tuple(m) for m in history_set]

        st.session_state.rounds.append({
            'round': st.session_state.round_number,
            'matches': matches,
            'scores': {player: 0 for _, m in matches for player in m}
        })
        st.session_state.round_number += 1

    for round_info in st.session_state.rounds:
        with st.expander(f"Round {round_info['round']}", expanded=(round_info['round'] == st.session_state.round_number - 1)):
            for court_name, match in round_info['matches']:
                with st.container():
                    st.markdown(f"### {court_name}")
                    for player in match:
                        score = st.number_input(f"{player} score", min_value=0, key=f"r{round_info['round']}_{player}")
                        round_info['scores'][player] = score

            if st.button(f"Submit Scores for Round {round_info['round']}"):
                update_scores(st.session_state.nightly, st.session_state.all_time, round_info['scores'])
                save_scores(st.session_state.all_time)
                st.success(f"Scores for Round {round_info['round']} submitted.")

    st.subheader("🎯 Nightly Leaderboard")
    st.dataframe(st.session_state.nightly.sort_values("games", ascending=False))

    st.subheader("🏆 All-Time Leaderboard")
    st.dataframe(st.session_state.all_time.sort_values("games", ascending=False))

    if st.button("Export Leaderboard to CSV"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tennis_leaderboard_{timestamp}.csv"
        st.session_state.all_time.to_csv(filename)
        st.success(f"Exported to {filename}")

    if st.button("Reset Night"):
        st.session_state.nightly = pd.DataFrame(0, index=players, columns=['games'])
        st.session_state.history = []
        st.session_state.rounds = []
        st.session_state.round_number = 1
        st.session_state.player_roles = {p: [] for p in players}
        st.success("Nightly session reset.")

    with st.expander("⚠️ Danger Zone: All-Time Leaderboard"):
        if 'confirm_delete' not in st.session_state:
            st.session_state.confirm_delete = False

        if not st.session_state.confirm_delete:
            if st.button("Delete All-Time Leaderboard"):
                st.session_state.confirm_delete = True
        else:
            st.warning("Are you sure you want to delete the All-Time Leaderboard? This cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Delete"):
                    if os.path.exists(SCORE_FILE):
                        os.remove(SCORE_FILE)
                    st.session_state.all_time = pd.DataFrame(columns=['games'])
                    save_scores(st.session_state.all_time)
                    st.success("All-Time Leaderboard has been deleted.")
                    st.session_state.confirm_delete = False
            with col2:
                if st.button("❌ No, Keep"):
                    st.session_state.confirm_delete = False

if __name__ == '__main__':
    app()
