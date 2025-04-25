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
        tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])
        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = []
            if 'editing_court' not in st.session_state:
                st.session_state.editing_court = {}
            st.header("Courts")
            st.markdown("Drag to reorder:")
            new_order = sort_items(st.session_state.courts, direction="vertical")
            if new_order != st.session_state.courts:
                st.session_state.courts = new_order
                save_data()

            for i, court in enumerate(st.session_state.courts):
                c1, c2, c3 = st.columns([6, 1, 1])
                if st.session_state.editing_court.get(i, False):
                    new_name = c1.text_input("Rename", value=court, label_visibility="collapsed", key=f"rename_court_input_{i}")
                    if c2.button("✅", key=f"save_court_{i}"):
                        if new_name and new_name != court and new_name not in st.session_state.courts:
                            st.session_state.courts[i] = new_name
                            save_data()
                        elif new_name in st.session_state.courts:
                            st.warning("Court name already exists.")
                        st.session_state.editing_court[i] = False
                else:
                    c1.write(court)
                    if c2.button("✏️", key=f"edit_court_{i}"):
                        st.session_state.editing_court[i] = True
                if c3.button("❌", key=f"rm_court_{i}"):
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
            if 'editing_player' not in st.session_state:
                st.session_state.editing_player = {}
            st.header("Players")
            for i, player in enumerate(st.session_state.players):
                p1, p2, p3 = st.columns([6, 1, 1])
                if st.session_state.editing_player.get(i, False):
                    newp = p1.text_input("Rename", value=player, label_visibility="collapsed", key=f"rename_player_input_{i}")
                    if p2.button("✅", key=f"save_player_{i}"):
                        if newp and newp != player and newp not in st.session_state.players:
                            st.session_state.players[i] = newp
                            save_data()
                        elif newp in st.session_state.players:
                            st.warning("Player name already exists.")
                        st.session_state.editing_player[i] = False
                else:
                    p1.write(player)
                    if p2.button("✏️", key=f"edit_player_{i}"):
                        st.session_state.editing_player[i] = True
                if p3.button("❌", key=f"rm_player_{i}"):
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

# rest of your code remains unchanged...


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
        # Schedule full matches with minimal repeats
        while courts and len(players) >= req:
            # Try combinations that have least history
            best_group = None
            min_repeat = float('inf')
            for _ in range(20):  # Try 20 random groupings
                group = random.sample(players, req)
                repeat_score = sum(
                    st.session_state.history[group[i]][group[j]]
                    for i in range(len(group))
                    for j in range(i + 1, len(group))
                )
                if repeat_score < min_repeat:
                    min_repeat = repeat_score
                    best_group = group
            for p in best_group:
                players.remove(p)
            court = courts.pop(0)
            matches.append((court, best_group))
            used.update(best_group)
            for i in range(len(best_group)):
                for j in range(i + 1, len(best_group)):
                    st.session_state.history[best_group[i]][best_group[j]] += 1
                    st.session_state.history[best_group[j]][best_group[i]] += 1

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
    
    # Show History
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
