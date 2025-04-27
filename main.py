import streamlit as st
import json
from fpdf import FPDF

# Load and save data functions
def load_data():
    try:
        with open('data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"players": [], "courts": []}

def save_data():
    with open('data.json', 'w') as f:
        json.dump({"players": st.session_state.players, "courts": st.session_state.courts}, f)

def load_scores():
    try:
        with open('scores.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_scores(scores):
    with open('scores.json', 'w') as f:
        json.dump(scores, f)

# Sidebar management
def sidebar_management():
    with st.sidebar:
        tab1, tab2, tab3 = st.tabs(["Courts", "Players", "Leaderboard"])

        # Tab 1 - Courts
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = load_data().get("courts", [])
            st.header("Courts")
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

# Scheduling matches based on selected players and courts
def schedule_matches():
    # Initialize selected players and courts
    if 'selected_players' not in st.session_state:
        st.session_state.selected_players = []

    if 'selected_courts' not in st.session_state:
        st.session_state.selected_courts = []

    # Get the list of selected players for tonight's matches
    selected_players = st.session_state.selected_players
    if len(selected_players) < 2:
        st.warning("Please select at least two players to schedule a match.")
        return

    # Get courts from the session state
    selected_courts = st.session_state.selected_courts
    if len(selected_courts) == 0:
        st.warning("Please select at least one court for scheduling.")
        return

    # Match type options
    match_type = st.radio("Match Type", ["Singles", "Doubles", "American Doubles", "Timed/Fast Four"])

    # Generate matchups based on selected players
    matches = []
    if match_type == "Singles":
        while len(selected_players) >= 2:
            match = (selected_players.pop(), selected_players.pop())
            matches.append(match)
    elif match_type == "Doubles":
        while len(selected_players) >= 4:
            match = (selected_players.pop(), selected_players.pop(), selected_players.pop(), selected_players.pop())
            matches.append(match)
    elif match_type == "American Doubles":
        while len(selected_players) >= 4:
            match = (selected_players.pop(), selected_players.pop(), selected_players.pop(), selected_players.pop())
            matches.append(match)
    elif match_type == "Timed/Fast Four":
        # Implement any rules for Timed/Fast Four if applicable
        while len(selected_players) >= 2:
            match = (selected_players.pop(), selected_players.pop())
            matches.append(match)

    # Display generated matches and the available courts
    st.write("### Scheduled Matches")
    match_courts = []
    for match in matches:
        st.write(f"Match: {match[0]} vs {match[1]}")
        if len(match) == 4:
            st.write(f"Match: {match[0]} & {match[1]} vs {match[2]} & {match[3]}")

    for match in matches:
        court = st.selectbox(f"Select court for match {match[0]} vs {match[1]}" if len(match) == 2 else f"Select court for match {match[0]} & {match[1]} vs {match[2]} & {match[3]}", st.session_state.courts)
        match_courts.append((match, court))

    if st.button("Generate Round"):
        st.write("### Match Schedule")
        for (match, court) in match_courts:
            st.write(f"{match[0]} vs {match[1]} on {court}" if len(match) == 2 else f"{match[0]} & {match[1]} vs {match[2]} & {match[3]} on {court}")
        st.session_state.match_courts = match_courts

    # Allow score entry after the round is generated
    if st.session_state.match_courts:
        st.write("### Enter Scores")
        score_dict = {}
        for i, (match, court) in enumerate(st.session_state.match_courts):
            if len(match) == 2:
                score_dict[f"{match[0]} vs {match[1]}"] = st.text_input(f"Score for {match[0]} vs {match[1]}", key=f"score_{i}")
            else:
                score_dict[f"{match[0]} & {match[1]} vs {match[2]} & {match[3]}"] = st.text_input(f"Score for {match[0]} & {match[1]} vs {match[2]} & {match[3]}", key=f"score_{i}")

        if st.button("Submit Scores"):
            save_scores(score_dict)
            st.success("Scores submitted successfully!")

# Reset rounds
def reset_rounds():
    st.session_state.match_courts = []
    st.session_state.selected_players = []
    st.session_state.round_scores = []

# Main app layout
def main():
    st.title("Tennis Match Scheduler")
    sidebar_management()

    # Tab for scheduling matches
    with st.container():
        st.header("Schedule Matches for Tonight")
        st.write("Select the players and courts for tonight's matches.")

        # Initialize selected players and courts
        if 'selected_players' not in st.session_state:
            st.session_state.selected_players = []

        if 'selected_courts' not in st.session_state:
            st.session_state.selected_courts = []

        # Selector for courts
        st.session_state.selected_courts = st.multiselect(
            "Select Courts",
            st.session_state.courts,
            key="selected_courts"
        )

        # Selector for players
        st.session_state.selected_players = st.multiselect(
            "Select Players",
            st.session_state.players,
            key="selected_players"
        )

        # Button to generate matches
        if st.button("Generate Matches"):
            schedule_matches()

        # Button to reset rounds
        if st.button("Reset Rounds"):
            reset_rounds()

if __name__ == "__main__":
    main()
