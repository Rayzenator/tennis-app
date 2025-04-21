import streamlit as st

def manage_players():
    st.header("Manage Players")
    new_player = st.text_input("Add Player Name", key="player_input")
    if st.button("Add Player"):
        if new_player and new_player not in st.session_state.players:
            st.session_state.players.append(new_player)
            st.session_state.players.sort()
    for player in st.session_state.players:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(player)
        with col2:
            if st.button("❌", key=f"remove_player_{player}"):
                st.session_state.players.remove(player)
