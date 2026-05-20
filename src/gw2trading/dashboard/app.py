"""GW2 Trading Assistant — Streamlit Dashboard.

Main app shell with sidebar navigation between pages.
Run with: streamlit run src/gw2trading/dashboard/app.py
"""

import streamlit as st

st.set_page_config(
    page_title="GW2 Trading Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation
st.sidebar.title("GW2 Trading")
st.sidebar.markdown("---")

# Use session state to track current page
if "current_page" not in st.session_state:
    st.session_state.current_page = "Market Overview"

pages = ["Market Overview", "Trading Signals", "Patch Analysis"]

# Render navigation links with spacing
for p in pages:
    is_active = st.session_state.current_page == p
    if is_active:
        st.sidebar.markdown(f"#### **►\u00a0\u00a0\u00a0{p}**")
    else:
        if st.sidebar.button(p, key=p, type="tertiary"):
            st.session_state.current_page = p
            st.rerun()
    st.sidebar.markdown("")  # spacing

st.sidebar.markdown("---")

# Route to pages
page = st.session_state.current_page

if page == "Market Overview":
    from gw2trading.dashboard.views.market import render
    render()
elif page == "Trading Signals":
    from gw2trading.dashboard.views.signals import render
    render()
elif page == "Patch Analysis":
    from gw2trading.dashboard.views.patches import render
    render()
