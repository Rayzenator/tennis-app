import streamlit as st
from fpdf import FPDF  # We will use this for exporting to PDF

# Helper to create PDF of the schedule
def export_to_pdf(rounds):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Tennis Match Schedule", ln=True, align="C")
    pdf.ln(10)

    # Adding rounds to the PDF
    pdf.set_font("Arial", size=12)
    for round_num, court_matches in rounds:
        pdf.cell(200, 10, f"Round {round_num}", ln=True)
        for court, players in court_matches:
            players_str = ", ".join(players)
            pdf.cell(200, 10, f"**{court}**: {players_str}", ln=True)
        pdf.ln(5)

    # Save file
    pdf_output = "/mnt/data/tennis_schedule.pdf"
    pdf.output(pdf_output)
    return pdf_output

# -----------------
# Schedule Tab
# -----------------
with tab3:
    st.header("Tonight's Match Schedule")

    if "selected_players" not in st.session_state or not st.session_state.selected_players:
        st.warning("Please select players first.")
    elif "selected_courts" not in st.session_state or not st.session_state.selected_courts:
        st.warning("Please select courts first.")
    else:
        if "rounds" not in st.session_state:
            st.session_state.rounds = []
            st.session_state.round_number = 1
            st.session_state.match_time = 20  # Default estimated time per round in minutes

        # Set up the input for match time per round
        st.sidebar.number_input("Estimated time per round (minutes):", 
            min_value=10, max_value=60, value=st.session_state.match_time)

        if st.button("Generate Round"):
            matches = schedule_matches(
                st.session_state.selected_players,
                st.session_state.selected_courts,
                st.session_state.match_type
            )
            st.session_state.rounds.append((st.session_state.round_number, matches))
            st.session_state.round_number += 1

        # Display rounds
        if st.session_state.rounds:
            for round_num, court_matches in st.session_state.rounds:
                st.subheader(f"Round {round_num} (Estimated time: {st.session_state.match_time} mins)")
                if st.session_state.match_type != "Rest":
                    for i, (court, players) in enumerate(court_matches):
                        court_name = f"Court {i + 1}"
                        players_str = ", ".join(players)
                        st.write(f"**{court_name}** - {st.session_state.match_type} ({st.session_state.scoring_type}): {players_str}")
                else:
                    st.subheader("Players Resting")
                    for player in st.session_state.selected_players:
                        st.write(player)

        # Export button for the entire schedule
        if st.button("Export Schedule to PDF"):
            pdf_path = export_to_pdf(st.session_state.rounds)
            st.success(f"Schedule exported! You can download it here: [Download PDF](sandbox:{pdf_path})")

