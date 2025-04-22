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

# Styles and assets
ALERT_SOUND = """
<audio id=\"beep\" autoplay loop>
  <source src=\"https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg\" type=\"audio/ogg\">  
  Your browser does not support the audio element.
</audio>
<script>
  const sound = document.getElementById("beep");
  sound.play();
  setTimeout(() => { sound.pause(); sound.currentTime = 0; }, 10000);
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

DARK_MODE_STYLE = """
<style>
body { background-color: #1e1e1e; color: white; }
.sidebar .sidebar-content { background-color: #2e2e2e; color: white; }
</style>
"""

st.set_page_config(page_title="Tennis Scheduler", layout="wide")
st.markdown(DARK_MODE_STYLE, unsafe_allow_html=True)

# Data persistence
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"courts": [], "players": []}

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({"courts": st.session_state.courts, "players": st.session_state.players}, f)

# Sidebar: manage courts and players
def sidebar_management():
    with st.sidebar:
        tab1, tab2 = st.tabs(["Manage Courts", "Manage Players"])

        with tab1:
            if 'courts' not in st.session_state:
                st.session_state.courts = []
            st.header("Courts")
            for i, court in enumerate(st.session_state.courts):
                c1, c2 = st.columns([8,1])
                c1.text(court)
                if c2.button("❌", key=f"rm_court_{i}"):
                    st.session_state.courts.pop(i)
                    save_data()
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

        with tab2:
            if 'players' not in st.session_state:
                st.session_state.players = []
            st.header("Players")
            for i, player in enumerate(st.session_state.players):
                c1, c2 = st.columns([8,1])
                c1.text(player)
                if c2.button("❌", key=f"rm_player_{i}"):
                    st.session_state.players.pop(i)
                    save_data()
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

# Export helpers
def generate_pdf(matches, round_no):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter
    y = h - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Tennis Schedule - Round {round_no}")
    y -= 30
    c.setFont("Helvetica", 12)
    for court, pts in matches:
        text = f"Court {court}: {' vs '.join(pts)}"
        c.drawString(50, y, text)
        y -= 20
        if y < 50:
            c.showPage()
            y = h - 40
    c.save()
    buf.seek(0)
    return buf

def generate_csv(matches):
    df = pd.DataFrame([(court, ', '.join(pts)) for court, pts in matches], columns=["Court","Players"])
    buf = BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return buf

# Main scheduling logic
def schedule_matches():
    # Initialize session state
    for var, val in [('history', defaultdict(lambda: defaultdict(int))),
                     ('schedule', []), ('round', 1), ('recent_ad', set())]:
        if var not in st.session_state:
            st.session_state[var] = val

    st.header("Schedule Matches")
    game_type = st.radio("Match Type", ["Doubles","Singles"])
    leftover_opt = st.radio("Leftover Players", ["Rest","Play American Doubles"])
    match_time = st.number_input("Match Time (min)", 5, 60, 15)

    if st.button("Generate Next Round"):
        players = st.session_state.players[:]
        random.shuffle(players)
        courts = st.session_state.courts[:]
        matches, used = [], set()

        # check court capacity
        req = 4 if game_type=='Doubles' else 2
        max_m = len(players)//req
        if len(courts) < max_m:
            st.warning("Not enough courts. Please add more courts.")

        # create full matches up to courts
        while courts and len(players) >= req:
            grp = players[:req]; players=players[req:]
            court = courts.pop(0)
            matches.append((court, grp))
            used.update(grp)
            # record head-to-head
            for i in range(len(grp)):
                for j in range(i+1,len(grp)):
                    st.session_state.history[grp[i]][grp[j]] +=1
                    st.session_state.history[grp[j]][grp[i]] +=1

        # handle leftovers
        if players:
            if game_type=='Singles' and len(players)==1 and leftover_opt=="Play American Doubles" and len(used)>=2:
                cand=[p for p in used if p not in st.session_state.recent_ad]
                if len(cand)<2: cand=list(used)
                pick=random.sample(cand,2)
                st.session_state.recent_ad=set(pick+players)
                matches.append(("Rotate", players+pick))
            else:
                matches.append(("Rest", players))

        st.session_state.schedule.append(matches)
        st.session_state.round=len(st.session_state.schedule)

    # display current round
    if st.session_state.schedule and st.session_state.round>0:
        rnd=st.session_state.round
        st.subheader(f"Round {rnd}")
        curr=st.session_state.schedule[rnd-1]
        for c,pts in curr:
            st.markdown(f"**Court {c}:** {' vs '.join(pts)}")

        if st.button("Start Play"):
            timer=match_time*60
            st.markdown(CLOCK_STYLE,unsafe_allow_html=True)
            ph=st.empty()
            for t in range(timer,0,-1):
                m,s=divmod(t,60)
                ph.markdown(f"<div class='big-clock'>{m:02d}:{s:02d}</div>",unsafe_allow_html=True)
                time.sleep(1)
            ph.markdown("<div class='big-clock'>00:00</div>",unsafe_allow_html=True)
            st.markdown(ALERT_SOUND,unsafe_allow_html=True)
            st.success("Time's up!")

        # export
        st.download_button("Download PDF", data=generate_pdf(curr,rnd), file_name=f"round_{rnd}.pdf")
        st.download_button("Download CSV", data=generate_csv(curr), file_name=f"round_{rnd}.csv")

    # navigation and reset
    c1,c2,c3=st.columns(3)
    if c1.button("Prev Round") and st.session_state.round>1:
        st.session_state.round-=1
    if st.session_state.round < len(st.session_state.schedule):
        if c2.button("Next Round"): st.session_state.round+=1
    else:
        c2.button("Next Round", disabled=True)
    if c3.button("Reset Rounds"):
        st.session_state.schedule=[]
        st.session_state.history=defaultdict(lambda:defaultdict(int))
        st.session_state.round=0
        st.session_state.recent_ad=set()

# initialize and run
if 'initialized' not in st.session_state:
    data=load_data()
    st.session_state.courts=data['courts']
    st.session_state.players=data['players']
    st.session_state.initialized=True

sidebar_management()
schedule_matches()
