import streamlit as st
import pandas as pd
from datetime import date
import json
import os
import base64

# Import functions from modules
from modules.data_handler import load_food_database, load_food_logs, save_food_logs
from modules.ui_components import (
    render_overview_section,
    render_search_section,
    render_food_log_section,
    render_settings_section
)
from modules.utils import format_date

# Set page configuration
st.set_page_config(
    page_title="burn.rate",
    page_icon="🔥",
    layout="centered"
)

# App title and description
st.markdown("<h1 style='text-align: center;'>🔥 burn.rate 🔥</h1>", unsafe_allow_html=True)
st.markdown("---")

# Initialize or load session state for food logs
if 'food_logs' not in st.session_state:
    st.session_state.food_logs = load_food_logs()

# Initialize expander states if they don't exist
if 'search_expanded' not in st.session_state:
    st.session_state.search_expanded = False
if 'log_expanded' not in st.session_state:
    st.session_state.log_expanded = False

# Load food database
try:
    food_db = load_food_database()
    if food_db is None:
        st.error("Failed to load food database")
        st.stop()
except Exception as e:
    st.error(f"Failed to load AUSNUT database: {e}")
    st.stop()

# Section 0: Overview
with st.expander(" 🔥Overview", expanded=True):
    render_overview_section(food_db)

# SECTION 1: Search functionality with autocomplete
with st.expander("🔎 Search", expanded=st.session_state.search_expanded):
    render_search_section(food_db)

# SECTION 2: Display food log for selected date
with st.expander("📋 Food Log", expanded=st.session_state.log_expanded):
    render_food_log_section(food_db)

# SECTION 3: Settings (new section for import/export)
with st.expander("⚙️ Settings", expanded=False):
    render_settings_section()