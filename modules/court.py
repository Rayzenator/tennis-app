import streamlit as st

def manage_courts():
    st.header("Manage Courts")
    new_court = st.text_input("Add Court Number", key="court_input")
    if st.button("Add Court"):
        if new_court and new_court not in st.session_state.courts:
            st.session_state.courts.append(new_court)
            st.session_state.courts.sort()
    for court in st.session_state.courts:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"Court {court}")
        with col2:
            if st.button("❌", key=f"remove_court_{court}"):
                st.session_state.courts.remove(court)
