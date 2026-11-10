import streamlit as st
from views.utils.common import submit_message

SUGGESTIONS = {
    "TEST: Tech Refresh": """Wir müssen bei uns die alten Windows-Server austauschen, laufen noch auf Server 2012
    und der Support läuft bald aus. Sind so 15 Arbeitsplätze insgesamt, dazu kommt noch ein
    Fileserver und ein kleiner Terminalserver für die Buchhaltung. Am liebsten würden wir
    gleich auf eine aktuelle Windows Server Version umsteigen und schauen, ob wir Teile
    davon auch in die Cloud packen können, aber das ist noch nicht final entschieden.
    Zeitlich sollte das idealerweise noch dieses Jahr passieren, weil die Hardware auch
    schon in die Jahre gekommen ist.""",
    "TEST: Filialnetz + Warenwirtschaft": """Die ACME Corp möchte an drei Filialstandorten die
    Netzwerkinfrastruktur erneuern: alte Switches austauschen und ein neues WLAN für
    Mitarbeitende und Gäste aufbauen. Zusätzlich soll das bestehende Firewall-Regelwerk
    bereinigt und auf neue Hardware migriert werden. Außerdem soll eine neue
    Warenwirtschafts-Software entwickelt und an das bestehende ERP angebunden werden,
    inklusive Migration der Altdaten und Schulung der Mitarbeitenden.""",
}

def render_init_phase() -> None:
    """Render the initial project description phase."""
    st.subheader(":material/account_tree: Wie sieht dein Projekt aus?")
    st.caption(
        "Beschreib dein Projekt in ein paar Sätzen - ich stelle Rückfragen, "
        "bis die Projektbeschreibung steht, und erstelle daraus den PSP."
    )

    user_input = st.chat_input("Beschreibe dein Projekt...", key="initial_question")
    
    if st.button("Geführt starten", icon=":material/checklist:", help="Standardfragen Schritt für Schritt beantworten"):
        st.session_state.phase = "guide"
        st.rerun()
    for suggestion in SUGGESTIONS:
        if st.button(suggestion):
            st.session_state.phase = "desc"
            submit_message(SUGGESTIONS[suggestion])
            st.rerun()
    
    if user_input:
        st.session_state.phase = "desc"
        submit_message(user_input)
        st.rerun()
