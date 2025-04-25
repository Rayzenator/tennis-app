import random
import time
from collections import defaultdict
import json
import os
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

try:
    import streamlit as st
    from streamlit_sortables import sort_items
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

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

def sidebar_management():
    with st.sidebar:
        st.header("Edit Mode")
        edit_button = st.button("Edit Courts and Players")
        
        if edit_button:
            st.session_state.edit_mode = True
        else:
            st.session_state.edit_mode = False

        if st.session_state.edit_mode:
            tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])
            with tab1:
                if 'courts' not in st.session_state:
                    st.session_state.courts = []
                st.header("Courts")
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

        else:
            st.write("You are not in edit mode. Press 'Edit Courts and Players' to manage them.")

def schedule_round(players, courts, match_type, leftover_action, history, recent_ad):
    random.shuffle(players)
    matches = []
    leftover = []

    if match_type == "Doubles":
        while len(players) >= 4 and courts:
            court = courts.pop(0)
            group = players[:4]
            players = players[4:]
            matches.append((court, group))
        leftover = players

        if leftover_action == "Play American Doubles":
            if len(leftover) == 1 and len(matches) >= 2:
                court_to_singles = matches.pop()
                court_to_ad = matches.pop()
                matches.append((court_to_singles[0], court_to_singles[1][:2]))
                ad_group = court_to_ad[1][:3] + [leftover[0]]
                matches.append(("Extra", ad_group))
                recent_ad.update(ad_group)
                leftover = []
            elif len(leftover) == 2:
                matches.append(("Extra", leftover))
                leftover = []
            elif len(leftover) == 3:
                matches.append(("Extra", leftover))
                recent_ad.update(leftover)
                leftover = []

    elif match_type == "Singles":
        while len(players) >= 2 and courts:
            court = courts.pop(0)
            group = players[:2]
            players = players[2:]
            matches.append((court, group))
        leftover = players

        if leftover_action == "Play American Doubles":
            if len(leftover) == 1 and matches:
                for i, (court, group) in enumerate(matches):
                    if len(group) == 2:
                        matches[i] = (court, group + [leftover[0]])
                        recent_ad.add(leftover[0])
                        leftover = []
                        break

    for court, group in matches:
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                p1, p2 = group[i], group[j]
                history[p1][p2] += 1
                history[p2][p1] += 1

    return {"matches": matches, "history": history, "recent_ad": recent_ad}

def schedule_matches():
    st.header("Schedule Matches")
    game_type = st.radio("Match Type", ["Doubles", "Singles"])
    format_opt = st.radio("Format", ["Timed", "Fast Four"])
    leftover_opt = st.radio("Leftover Action", ["Rest", "Play American Doubles"])

    if format_opt == "Timed":
        match_time = st.number_input("Match Time (minutes)", 5, 60, 15)
    else:
        st.info("Fast Four: first to 4 games wins.")

    if st.button("Generate Next Round"):
        results = schedule_round(
            st.session_state.players.copy(),
            st.session_state.courts.copy(),
            game_type,
            leftover_opt,
            st.session_state.get("history", defaultdict(lambda: defaultdict(int))),
            st.session_state.get("recent_ad", set())
        )
        st.session_state.schedule = st.session_state.get("schedule", []) + [results["matches"]]
        st.session_state.round = len(st.session_state.schedule)
        st.session_state.history = results["history"]
        st.session_state.recent_ad = results["recent_ad"]

    if st.session_state.get("schedule") and st.session_state.get("round", 0) > 0:
        r = st.session_state.round
        st.subheader(f"Round {r}")
        cr = st.session_state.schedule[r-1]
        for court, pts in cr:
            st.markdown(f"**Court {court}:** {' vs '.join(pts)}")

        if format_opt == "Timed":
            if st.button("Start Play"):
                total = match_time * 60
                pl = st.empty()
                for t in range(total, 0, -1):
                    m, s = divmod(t, 60)
                    pl.markdown(f"<h1 style='text-align:center;'>{m:02d}:{s:02d}</h1>", unsafe_allow_html=True)
                    time.sleep(1)
                pl.markdown("<h1 style='text-align:center;'>00:00</h1>", unsafe_allow_html=True)
                st.success("Time's up!")
        else:
            if st.button("Begin Fast Four"):
                st.info("Fast Four match: first to 4 games wins.")

        st.download_button("PDF", data=generate_pdf(cr, r), file_name=f"round_{r}.pdf")
        st.download_button("CSV", data=generate_csv(cr), file_name=f"round_{r}.csv")

    if st.checkbox("Show Player Pairing History"):
        st.subheader("Player Pairing History")
        players = st.session_state.players
        data = []
        for p1 in players:
            row = []
            for p2 in players:
                if p1 == p2:
                    row.append("-")
                else:
                    row.append(st.session_state.history[p1][p2])
            data.append(row)
        df = pd.DataFrame(data, index=players, columns=players)
        st.dataframe(df)

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

def main():
    st.set_page_config(page_title="Tennis Scheduler", layout="wide")
    st.markdown("""
        <style>
        body { background-color: #1e1e1e; color: white; }
        .sidebar .sidebar-content { background-color: #2e2e2e; color: white; }
        </style>
    """, unsafe_allow_html=True)

    if 'initialized' not in st.session_state:
        d = load_data()
        st.session_state.courts = d['courts']
        st.session_state.players = d['players']
        st.session_state.round = 0  # Initialize round here
        st.session_state.initialized = True

    sidebar_management()
    schedule_matches()

if __name__ == "__main__" and STREAMLIT_AVAILABLE:
    main()
