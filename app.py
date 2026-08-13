import streamlit as st
from services.auth_service import is_admin_authenticated, login, logout
import streamlit.components.v1 as components
import pandas as pd
import math
import os
import time

from database.crud import get_all_stories
from services.storage_service import get_render_path_for_uuid, CAPTIONS_DIR, HASHTAGS_DIR, ARTICLES_DIR
from database.diagnostics import run_database_diagnostics
from ai.ranker import generate_score_explanation
from database.migrations import create_database
from services import logging_service
from services.queue_service import handle_generate_story_action, transition_article_status

# Initialize database to prevent "no such table" errors on first run
create_database()

st.set_page_config(
    page_title="CipherBrief Newsroom",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# 1. GLOBAL CSS & THEMING
# ==========================================
import base64
def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    bg_base64 = get_base64_of_bin_file("assets/cipherbrief_background.svg")
except:
    bg_base64 = ""

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    :root {
        --bg-main: #07090D;
        --bg-surface: rgba(10, 13, 18, 0.82);
        --bg-secondary: rgba(10, 13, 18, 0.6);
        --border-color: rgba(255, 255, 255, 0.07);
        --text-primary: #F5F7FA;
        --text-secondary: #9299A5;
        --text-muted: #666D78;
        
        --accent-blue: #4DA3FF;
        --accent-blue-glow: rgba(77, 163, 255, 0.15);
        --accent-success: #3DDC97;
        --accent-success-glow: rgba(61, 220, 151, 0.15);
        --accent-danger: #FF5C5C;
        --accent-danger-glow: rgba(255, 92, 92, 0.15);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: var(--bg-main) !important;
        background-image: url("data:image/svg+xml;base64,BACKGROUND_BASE64_PLACEHOLDER") !important;
        background-size: cover !important;
        background-attachment: fixed !important;
        background-position: center !important;
    }
    
    @keyframes cinematicFadeIn {
        from { opacity: 0; transform: translateY(16px); }
        to { opacity: 1; transform: translateY(0); }
    }
    div[data-testid="stMainBlockContainer"] {
        animation: cinematicFadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background: transparent !important;}
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1400px;
    }

    [data-testid="stSidebar"] {
        background-color: rgba(11, 14, 20, 0.8) !important;
        border-right: 1px solid var(--border-color);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
    }
    
    .sidebar-brand {
        font-size: 18px;
        font-weight: 800;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--text-primary);
        margin-bottom: 4px;
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 16px;
    }
    .sidebar-brand-subtitle {
        font-size: 10px;
        font-weight: 500;
        letter-spacing: 0.2em;
        color: var(--accent-blue);
        margin-top: -12px;
        margin-bottom: 24px;
    }
    .nav-header {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.16em;
        color: var(--text-muted);
        text-transform: uppercase;
        margin-top: 24px;
        margin-bottom: 12px;
    }

    [data-testid="metric-container"] {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.25);
        backdrop-filter: blur(12px);
        position: relative;
        overflow: hidden;
    }
    [data-testid="metric-container"]::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 3px;
        background-color: var(--accent-blue);
        opacity: 0.8;
    }
    [data-testid="metric-container"] label {
        color: var(--text-secondary) !important;
        font-size: 11px !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    [data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-weight: 700;
        font-size: 32px !important;
        letter-spacing: -0.02em;
    }

    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 1rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        backdrop-filter: blur(12px);
    }

    .stButton > button {
        background-color: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .stButton > button:hover {
        border-color: var(--accent-blue) !important;
        background-color: rgba(77, 163, 255, 0.05) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .stButton > button:active {
        transform: scale(0.94) !important;
    }
    .stButton > button[kind="primary"] {
        background-color: rgba(77, 163, 255, 0.1) !important;
        color: var(--accent-blue) !important;
        border: 1px solid var(--accent-blue) !important;
        box-shadow: 0 4px 16px var(--accent-blue-glow);
    }
    .stButton > button[kind="primary"]:hover {
        background-color: var(--accent-blue) !important;
        color: #000 !important;
    }
    .stButton > button[kind="primary"]:active {
        transform: scale(0.94) !important;
    }

    .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    .badge::before {
        content: "";
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .badge-new { background-color: rgba(255,255,255,0.05); color: var(--text-secondary); border: 1px solid rgba(255,255,255,0.1); }
    .badge-new::before { background-color: var(--text-secondary); }
    .badge-post_ready { background-color: var(--accent-blue-glow); color: var(--accent-blue); border: 1px solid rgba(77, 163, 255, 0.3); }
    .badge-post_ready::before { background-color: var(--accent-blue); box-shadow: 0 0 6px var(--accent-blue); }
    .badge-approved { background-color: var(--accent-success-glow); color: var(--accent-success); border: 1px solid rgba(61, 220, 151, 0.3); }
    .badge-approved::before { background-color: var(--accent-success); box-shadow: 0 0 6px var(--accent-success); }
    .badge-rejected { background-color: var(--accent-danger-glow); color: var(--accent-danger); border: 1px solid rgba(255, 92, 92, 0.3); }
    .badge-rejected::before { background-color: var(--accent-danger); box-shadow: 0 0 6px var(--accent-danger); }

    .story-card-wrapper {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 12px 32px rgba(0,0,0,0.2);
        backdrop-filter: blur(12px);
        margin-bottom: 8px;
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .story-card-wrapper:hover {
        border-color: rgba(255,255,255,0.15);
        transform: translateY(-2px);
    }
    .story-card-edge-glow-approved { border-left: 3px solid var(--accent-success); }
    .story-card-edge-glow-rejected { border-left: 3px solid var(--accent-danger); }
    .story-card-edge-glow-post_ready { border-left: 3px solid var(--accent-blue); }
    .story-card-edge-glow-new { border-left: 3px solid rgba(255,255,255,0.1); }
    
    .story-headline {
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 8px;
        line-height: 1.3;
        letter-spacing: -0.01em;
    }
    .story-meta {
        font-size: 11px;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 600;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .story-summary {
        font-size: 14px;
        color: var(--text-secondary);
        line-height: 1.5;
        margin-bottom: 20px;
    }
    
    .score-container {
        display: flex;
        align-items: baseline;
        gap: 2px;
    }
    .score-value {
        font-size: 28px;
        font-weight: 800;
        color: var(--accent-blue);
        line-height: 1;
        letter-spacing: -0.03em;
    }
    .score-max {
        font-size: 14px;
        font-weight: 600;
        color: var(--text-muted);
    }
    .score-label {
        font-size: 9px;
        font-weight: 700;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.2em;
        margin-top: 4px;
    }

    .preview-stage {
        background-color: rgba(0,0,0,0.5);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 40px;
        display: flex;
        justify-content: center;
        align-items: center;
        background-image: 
            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
        background-size: 20px 20px;
        box-shadow: inset 0 0 60px rgba(0,0,0,0.8);
    }
    .preview-stage img {
        border-radius: 8px;
        box-shadow: 0 24px 60px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.1);
    }

    .editorial-panel {
        background-color: rgba(11, 14, 20, 0.6);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 16px;
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .section-header {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--text-muted);
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 8px;
        margin-bottom: 16px;
    }
    .section-title {
        font-size: 20px;
        font-weight: 600;
        letter-spacing: -0.01em;
        margin-bottom: 24px;
        color: var(--text-primary);
    }
    
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        [data-testid="metric-container"] div[data-testid="stMetricValue"] {
            font-size: 24px !important;
        }
        .stButton > button {
            padding: 0.6rem 1rem !important;
            font-size: 14px !important;
        }
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0.75rem !important;
        }
    }

    /* 1. Custom Dark-Mode Scrollbars */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.2);
    }

    /* 2. Interactive Hover Lifts */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer;
    }
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.3);
        border-color: rgba(77, 163, 255, 0.2) !important;
    }
    
    /* Ensure links inside the clickable card keep their own styling and pointer */
    .story-card-wrapper a {
        color: var(--accent-blue);
        text-decoration: none;
        position: relative;
        z-index: 10; /* Ensure it catches clicks over the card */
    }
    .story-card-wrapper a:hover {
        text-decoration: underline;
    }

    /* 5. Skeleton Loading / Pulse Effects */
    @keyframes pulseGlow {
        0% { opacity: 1; box-shadow: 0 0 0 0 rgba(77, 163, 255, 0.4); }
        50% { opacity: 0.8; box-shadow: 0 0 0 10px rgba(77, 163, 255, 0); }
        100% { opacity: 1; box-shadow: 0 0 0 0 rgba(77, 163, 255, 0); }
    }
    .processing-pulse {
        animation: pulseGlow 2s infinite cubic-bezier(0.4, 0, 0.2, 1) !important;
        border-color: var(--accent-blue) !important;
    }
</style>
<script>
    const parentDoc = window.parent.document;
    if (!parentDoc.getElementById('briefbot-card-clicker')) {
        const script = parentDoc.createElement('script');
        script.id = 'briefbot-card-clicker';
        script.innerHTML = `
            document.addEventListener('click', function(e) {
                if (e.target.closest('a')) return; // Ignore link clicks
                if (e.target.closest('button')) return; // Ignore button clicks
                
                const container = e.target.closest('div[data-testid="stVerticalBlockBorderWrapper"]');
                if (container) {
                    const btn = container.querySelector('button');
                    if (btn && btn.innerText.toUpperCase().includes('REVIEW')) {
                        btn.click();
                    }
                }
            });
        `;
        parentDoc.head.appendChild(script);
    }
</script>
""".replace("BACKGROUND_BASE64_PLACEHOLDER", bg_base64), unsafe_allow_html=True)


# ==========================================
# 2. DATA LOAD & CACHE
# ==========================================
@st.cache_data(ttl=30)
def load_story_data():
    return get_all_stories(limit=100)

stories = load_story_data()


# ==========================================
# 3. ROUTING & STATE
# ==========================================
if 'role_selected' not in st.session_state:
    st.session_state.role_selected = None
if 'active_page' not in st.session_state:
    st.session_state.active_page = 'Overview'
if 'selected_story_id' not in st.session_state:
    st.session_state.selected_story_id = None



if st.session_state.role_selected is None:
    # --- LANDING PAGE ---
    st.markdown("""
    <style>
    .landing-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh;
        text-align: center;
    }
    .landing-title {
        font-size: 48px;
        font-weight: 800;
        letter-spacing: -0.05em;
        margin-bottom: 8px;
        color: var(--text-primary);
    }
    .landing-subtitle {
        font-size: 16px;
        font-weight: 500;
        letter-spacing: 0.2em;
        color: var(--accent-blue);
        text-transform: uppercase;
        margin-bottom: 48px;
    }
    .landing-prompt {
        font-size: 20px;
        color: var(--text-secondary);
        margin-bottom: 32px;
    }
    
    .role-card-btn {
        background-color: rgba(20, 24, 32, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 32px;
        height: 100%;
        text-align: left;
        transition: all 0.2s ease;
        cursor: pointer;
    }
    
    .role-card-btn:hover {
        border-color: rgba(255, 255, 255, 0.3);
        transform: translateY(-4px);
        box-shadow: 0 12px 32px rgba(0,0,0,0.4);
    }
    
    .role-title {
        font-size: 24px;
        font-weight: 700;
        margin-bottom: 12px;
        color: var(--text-primary);
        letter-spacing: 0.05em;
    }
    .role-desc {
        font-size: 14px;
        color: var(--text-secondary);
        line-height: 1.5;
        margin-bottom: 24px;
    }
    .role-badge {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.15em;
        padding: 6px 12px;
        border-radius: 20px;
        display: inline-block;
    }
    .role-badge-viewer {
        background-color: rgba(255, 255, 255, 0.05);
        color: var(--text-muted);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .role-badge-admin {
        background-color: rgba(77, 163, 255, 0.1);
        color: var(--accent-blue);
        border: 1px solid rgba(77, 163, 255, 0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="landing-container">', unsafe_allow_html=True)
    st.markdown('<div class="landing-title">CIPHERBRIEF</div>', unsafe_allow_html=True)
    st.markdown('<div class="landing-subtitle">NEWS INTELLIGENCE DESK</div>', unsafe_allow_html=True)
    st.markdown('<div class="landing-prompt">How would you like to enter?</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown(f"""
        <div class="role-card-btn" id="viewer-card">
            <div class="role-title">VIEWER</div>
            <div class="role-desc">Read the latest news, analysis and published briefs. Read-only access to the editorial dashboard.</div>
            <div class="role-badge role-badge-viewer">READ / EXPLORE</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter as Viewer", key="btn_viewer", use_container_width=True):
            st.session_state.role_selected = "viewer"
            st.rerun()
            
    with col2:
        st.markdown(f"""
        <div class="role-card-btn" id="admin-card">
            <div class="role-title">ADMIN</div>
            <div class="role-desc">Review stories, synthesize posts and manage the editorial workflow. Authorized access required.</div>
            <div class="role-badge role-badge-admin">EDITORIAL / CREATE</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter as Admin", key="btn_admin", use_container_width=True):
            st.session_state.role_selected = "admin_login"
            st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.role_selected == "admin_login":
    # --- ADMIN LOGIN PAGE ---
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background-color: var(--bg-surface);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        box-shadow: 0 24px 48px rgba(0,0,0,0.4);
        backdrop-filter: blur(12px);
    }
    .login-header {
        font-size: 24px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 8px;
    }
    .login-subheader {
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.15em;
        text-align: center;
        color: var(--accent-blue);
        text-transform: uppercase;
        margin-bottom: 32px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">Admin Authentication</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subheader">EDITORIAL WORKFLOW</div>', unsafe_allow_html=True)
        
        with st.form("admin_login_form"):
            admin_user = st.text_input("Username")
            admin_pass = st.text_input("Password", type="password")
            
            if st.form_submit_button("Authenticate", use_container_width=True):
                if login(admin_user, admin_pass):
                    st.session_state.role_selected = "admin"
                    st.rerun()
                else:
                    st.error("Authentication failed. Invalid credentials.")
                    
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("? Back to Role Selection", use_container_width=True):
            st.session_state.role_selected = None
            st.rerun()

else:
    # --- MAIN DASHBOARD ---
    # ==========================================
    # 4. TOP HEADER
    # ==========================================
    hdr_col1, hdr_col2 = st.columns([1, 15])
    with hdr_col1:
        if os.path.exists("assets/logo.png"):
            st.image("assets/logo.png", width=64)
    with hdr_col2:
        st.markdown("""
        <div class="app-header" style="border-bottom: none; padding-bottom: 0; margin-bottom: 0;">
            <div>
                <h1 class="app-title">CIPHERBRIEF</h1>
                <div class="app-subtitle">News Intelligence / Editorial Desk</div>
            </div>
            <div class="system-status">● ALL SYSTEMS OPERATIONAL</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<hr style='border-color: var(--border-color); margin-top: 16px; margin-bottom: 24px;'>", unsafe_allow_html=True)


    # ==========================================
    # 5. SIDEBAR (NAVIGATION & FILTERS)
    # ==========================================
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-brand">CIPHERBRIEF</div>
        <div class="sidebar-brand-subtitle">NEWS INTELLIGENCE</div>
        <div class="nav-header">NAVIGATION</div>
        """, unsafe_allow_html=True)
        
        # Custom Navigation
        page_options = {
            "Overview": "",
            "All Stories": ""
        }
        
        is_admin = is_admin_authenticated()
        if is_admin:
            page_options["Post Ready"] = ""
            page_options["Approved"] = ""
        
        for page, icon in page_options.items():
            if st.button(f"{page}", key=f"nav_{page}", use_container_width=True, type="primary" if st.session_state.active_page == page else "secondary"):
                st.session_state.active_page = page
                st.session_state.selected_story_id = None
                st.rerun()

        st.markdown("<br><hr style='border-color: #242933;'><br>", unsafe_allow_html=True)
        
        admin_view = "Editorial Feed"
        is_admin = is_admin_authenticated()
        if is_admin:
            st.markdown("<h3 style='font-size:14px; color:var(--accent-success); text-transform:uppercase; margin-bottom:12px;'>? AUTHENTICATED</h3>", unsafe_allow_html=True)
            if st.button("Log Out", use_container_width=True):
                logout()
                st.rerun()
                
            st.markdown("<br><h3 style='font-size:14px; color:#9299A5; text-transform:uppercase; margin-bottom:12px;'>Navigation</h3>", unsafe_allow_html=True)
            admin_view = st.radio("View", ["Editorial Feed", "User Feedback"], label_visibility="collapsed")
        else:
            st.markdown("<h3 style='font-size:14px; color:#9299A5; text-transform:uppercase; margin-bottom:12px;'>● PUBLIC VIEW (READ-ONLY)</h3>", unsafe_allow_html=True)
            if st.button("Admin Login", use_container_width=True):
                st.session_state.role_selected = "admin_login"
                st.rerun()
                
            st.markdown("<br><h3 style='font-size:14px; color:#9299A5; text-transform:uppercase; margin-bottom:12px;'>Submit Feedback</h3>", unsafe_allow_html=True)
            with st.expander("Report Bug or Feedback"):
                with st.form("feedback_form"):
                    fb_name = st.text_input("Your Name")
                    fb_text = st.text_area("Feedback")
                    if st.form_submit_button("Submit", use_container_width=True):
                        if fb_name and fb_text:
                            from database.models import FeedbackModel
                            from database.connection import get_session
                            from datetime import datetime
                            with get_session() as session:
                                new_fb = FeedbackModel(
                                    name=fb_name,
                                    feedback_text=fb_text,
                                    timestamp=datetime.utcnow().isoformat()
                                )
                                session.add(new_fb)
                                session.commit()
                            
                            @st.dialog("Feedback Received")
                            def success_dialog():
                                st.write("Your feedback has been successfully submitted. Thank you for helping us improve BriefBot.")
                            success_dialog()
                        else:
                            st.error("Please fill in both name and feedback.")
                
        st.markdown("<br><h3 style='font-size:14px; color:#9299A5; text-transform:uppercase; margin-bottom:12px;'>Actions</h3>", unsafe_allow_html=True)
        if st.button("Fetch & Process Latest", use_container_width=True):
            from settings import OPENROUTER_API_KEY
            if not OPENROUTER_API_KEY:
                st.error("Error: OPENROUTER_API_KEY is not set.")
            else:
                with st.status("Fetching and clustering news...", expanded=True) as status:
                    try:
                        import main, sys
                        from io import StringIO
                        original_stdout = sys.stdout
                        sys.stdout = StringIO()
                        try:
                            main.main()
                        finally:
                            output = sys.stdout.getvalue()
                            sys.stdout = original_stdout
                        status.update(label="News fetched successfully!", state="complete", expanded=False)
                    except Exception as e:
                        status.update(label=f"Error: {e}", state="error", expanded=True)
                import time
                time.sleep(2)
                st.cache_data.clear()
                st.rerun()

        st.markdown("<br><hr style='border-color: #242933;'><br>", unsafe_allow_html=True)
        
        if admin_view == "User Feedback":
            st.markdown("<div class='nav-header'>USER FEEDBACK</div>", unsafe_allow_html=True)
            from database.models import FeedbackModel
            from database.connection import get_session
            
            with get_session() as session:
                feedbacks = session.query(FeedbackModel).order_by(FeedbackModel.id.desc()).all()
                if not feedbacks:
                    st.info("No feedback submitted yet.")
                else:
                    for fb in feedbacks:
                        with st.container():
                            st.markdown(f"**{fb.name}** - <span style='color:var(--text-muted); font-size: 12px;'>{fb.timestamp[:19].replace('T', ' ')}</span>", unsafe_allow_html=True)
                            st.write(fb.feedback_text)
                            st.markdown("<hr style='border-color: #242933;'>", unsafe_allow_html=True)
            st.stop()

        st.markdown("<div class='nav-header'>EDITORIAL FEED</div>", unsafe_allow_html=True)
        
        with st.form("filter_form"):
            search = st.text_input("Search", placeholder="Search stories...")
            
            # Ensure "World" and "India" are always available, plus any others in the DB
            db_categories = list(set([s.category for s in stories if s.category])) if stories else []
            all_categories = sorted(list(set(db_categories + ["World", "India"])))
            categories = ["All"] + all_categories
            
            category = st.selectbox("Category", categories)
            
            sources_list = ["All"] + sorted(list(set([s.primary_source for s in stories if s.primary_source]))) if stories else ["All"]
            source_filter = st.selectbox("Source", sources_list)
            
            min_score = st.slider("Min Score", 0, 100, 0, 5)
            
            st.form_submit_button("Apply Filters", use_container_width=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.expander("System Diagnostics"):
            if is_admin_authenticated():
                if st.button("Run Health Check"):
                    diag = run_database_diagnostics()
                    st.json(diag)
            else:
                st.info("Admin access required for diagnostics.")

    # ==========================================
    # 6. FILTER LOGIC
    # ==========================================
    filtered_stories = stories
    if filtered_stories:
        # Auto-filter based on navigation route
        if st.session_state.active_page == "Post Ready":
            filtered_stories = [s for s in filtered_stories if s.status == "post_ready"]
        elif st.session_state.active_page == "Approved":
            filtered_stories = [s for s in filtered_stories if s.status == "approved"]
            
        # Manual filters
        if search:
            s_lower = search.lower()
            filtered_stories = [s for s in filtered_stories if (
                s_lower in s.story_title.lower() or 
                (s.caption and s_lower in s.caption.lower()) or 
                s_lower in s.category.lower() or 
                s_lower in s.primary_source.lower()
            )]
        if category != "All":
            filtered_stories = [s for s in filtered_stories if s.category == category]
        if source_filter != "All":
            filtered_stories = [s for s in filtered_stories if s.primary_source == source_filter]
        filtered_stories = [s for s in filtered_stories if s.overall_story_score >= min_score]
        
        # Sort
        sort_by = st.selectbox("Sort By", ["Latest", "Highest Reach Expectancy", "Most Cross-Verified", "Needs Review (Low Score)"])
        if sort_by == "Latest":
            def get_ts(s):
                try:
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(s.first_published).timestamp()
                except:
                    return 0
            filtered_stories = sorted(filtered_stories, key=get_ts, reverse=True)
        elif sort_by == "Highest Reach Expectancy":
            filtered_stories = sorted(filtered_stories, key=lambda s: s.overall_story_score, reverse=True)
        elif sort_by == "Most Cross-Verified":
            filtered_stories = sorted(filtered_stories, key=lambda s: s.num_sources, reverse=True)
        elif sort_by == "Needs Review (Low Score)":
            filtered_stories = sorted(filtered_stories, key=lambda s: s.overall_story_score)


    # ==========================================
    # 7. RENDER HELPER FUNCTIONS
    # ==========================================
    def render_story_card(story):
        """Renders a compact, editorial story card."""
        s_dict = story.to_dict()
        current_status = str(story.status or "new").lower()
        
        badge_class = f"badge-{current_status}" if current_status in ["new", "post_ready", "approved", "rejected"] else "badge-new"
        edge_class = f"story-card-edge-glow-{current_status}" if current_status in ["new", "post_ready", "approved", "rejected"] else "story-card-edge-glow-new"
        
        primary_art = story.articles[0] if story.articles else {}
        summary = primary_art.get('summary', '')
        if len(summary) > 150:
            summary = summary[:147] + "..."
            
        with st.container():
            st.markdown(f"""
            <div class='story-card-wrapper {edge_class}'>
                <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
                    <div style='flex: 1; padding-right: 16px;'>
                        <div class='story-meta'>
                            <span style='color:var(--text-primary);'>{story.primary_source}</span>
                            <span style='color:var(--border-color);'>|</span>
                            <span>{story.first_published[:16] if story.first_published else ''}</span>
                            <span style='color:var(--border-color);'>|</span>
                            <a href='{primary_art.url if hasattr(primary_art, "url") else primary_art.get("url", "#")}' target='_blank' style='font-weight: 600;'>Read Source ↗</a>
                        </div>
                        <div class='story-headline'>{story.story_title}</div>
                    </div>
                    <div style='text-align:right; margin-left:16px;'>
                        <div class='score-container'>
                            <span class='score-value'>{story.overall_story_score}</span>
                            <span class='score-max'>/100</span>
                        </div>
                        <div class='score-label'>SCORE</div>
                    </div>
                </div>
                <div class='story-summary'>{summary}</div>
                <div style='display:flex; justify-content:space-between; align-items:center; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 16px;'>
                    <div style='display:flex; align-items:center; gap: 12px;'>
                        <span class='badge {badge_class}'>{current_status.upper().replace('_', ' ')}</span>
                        <span style='font-size:10px; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.1em; font-weight:600;'>{story.category}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if is_admin_authenticated():
                col_dummy, col_btn = st.columns([5,2])
                with col_btn:
                    if st.button("Review", key=f"btn_review_{story.story_id}", use_container_width=True):
                        st.session_state.selected_story_id = story.story_id
                        st.rerun()

    def render_story_detail(story):
        """Renders the professional detail/workspace view for a single story."""
        if st.button("← Back to List"):
            st.session_state.selected_story_id = None
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        s_dict = story.to_dict()
        story_id = story.story_id
        current_status = str(story.status or "new").lower()
        
        c1, c2 = st.columns([1, 1.5], gap="large")
        
        render_path = story.rendered_image_path or get_render_path_for_uuid(story_id)
        has_render = bool(render_path and os.path.exists(render_path) and os.path.getsize(render_path) > 100)
        
        cap_p = os.path.join(CAPTIONS_DIR, f"caption_{story_id}.txt")
        has_caption_file = os.path.exists(cap_p) and os.path.getsize(cap_p) > 10
        
        hash_p = os.path.join(HASHTAGS_DIR, f"hashtags_{story_id}.txt")
        has_hashtags_file = os.path.exists(hash_p) and os.path.getsize(hash_p) > 10

        caption_text = story.caption
        if (not caption_text or pd.isna(caption_text)) and has_caption_file:
            try:
                with open(cap_p, "r", encoding="utf-8") as f: caption_text = f.read()
            except OSError: pass

        hashtags_text = story.hashtags
        if (not hashtags_text or pd.isna(hashtags_text)) and has_hashtags_file:
            try:
                with open(hash_p, "r", encoding="utf-8") as f: hashtags_text = f.read()
            except OSError: pass

        with c1:
            st.markdown("<div class='section-header'>POST PREVIEW</div>", unsafe_allow_html=True)
            if current_status == "approved":
                st.markdown("<div style='background:rgba(61, 220, 151, 0.1); border:1px solid #3DDC97; color:#3DDC97; padding:12px; border-radius:6px; text-align:center; font-weight:600; margin-bottom:16px; letter-spacing:0.1em; font-size:12px;'>● APPROVED — READY TO POST</div>", unsafe_allow_html=True)
            elif current_status == "post_ready":
                st.markdown("<div style='background:rgba(77, 163, 255, 0.1); border:1px solid #4DA3FF; color:#4DA3FF; padding:12px; border-radius:6px; text-align:center; font-weight:600; margin-bottom:16px; letter-spacing:0.1em; font-size:12px;'>● POST READY</div>", unsafe_allow_html=True)

            if has_render:
                try:
                    from PIL import Image
                    img = Image.open(render_path)
                    st.markdown("<div class='preview-stage'>", unsafe_allow_html=True)
                    st.image(img, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    st.markdown("<div style='text-align:center; font-size:11px; color:#666D78; margin-top:8px; letter-spacing:0.1em;'>1080 × 1920 PNG</div>", unsafe_allow_html=True)
                except OSError:
                    st.error("Image exists but could not be loaded.")
            else:
                st.markdown("""
                <div class='preview-stage' style='height: 400px; flex-direction: column;'>
                    <div style='color:var(--text-muted); font-size:14px; font-weight:600; text-transform:uppercase; letter-spacing:0.1em;'>Visual render not generated</div>
                    <div style='color:var(--border-color); font-size:40px; margin-top:16px;'>●</div>
                </div>
                """, unsafe_allow_html=True)

        with c2:
            st.markdown("<div class='section-header'>EDITORIAL BRIEF</div>", unsafe_allow_html=True)
            
            with st.container(border=True):
                st.markdown(f"""
                <div class='story-headline' style='font-size:24px; margin-bottom:20px;'>{story.story_title}</div>
                <div style='display:flex; justify-content:space-between; border-bottom:1px solid var(--border-color); padding-bottom:16px; margin-bottom:16px;'>
                    <div>
                        <div style='color:var(--text-muted); font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.15em; margin-bottom:4px;'>SOURCE</div>
                        <div style='font-size:14px; color:var(--text-primary); font-weight:500;'>{story.primary_source}</div>
                    </div>
                    <div>
                        <div style='color:var(--text-muted); font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.15em; margin-bottom:4px;'>CATEGORY</div>
                        <div style='font-size:14px; color:var(--text-primary); font-weight:500;'>{story.category}</div>
                    </div>
                    <div>
                        <div style='color:var(--text-muted); font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.15em; margin-bottom:4px;'>SCORE</div>
                        <div class='score-container'><span class='score-value' style='font-size:20px;'>{story.overall_story_score}</span><span class='score-max'>/100</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**AI Analysis & Reasoning**")
                primary_art = story.articles[0] if story.articles else {}
                explanation_points = generate_score_explanation(primary_art, story.num_sources)
                for point in explanation_points:
                    st.markdown(f"- {point}")

            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown("<div class='section-header'>CAPTION</div>", unsafe_allow_html=True)
            if caption_text:
                st.code(caption_text, language=None)
            else:
                st.info("No caption generated yet.")
                
            st.markdown("<br><div class='section-header'>HASHTAGS</div>", unsafe_allow_html=True)
            if hashtags_text:
                st.code(hashtags_text, language=None)
            else:
                st.info("No hashtags generated yet.")
                
            st.markdown("<hr style='border-color: #242933; margin: 32px 0;'>", unsafe_allow_html=True)
            
            st.markdown("<div class='section-header'>WORKFLOW ACTIONS</div>", unsafe_allow_html=True)
            
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            with col_a1:
                btn_label = "Re-synthesize" if has_render else "Synthesize"
                if not is_admin_authenticated():
                    st.button("🔒 " + btn_label, disabled=True, key=f"synth_btn_{story_id}_{has_render}", use_container_width=True, help="Admin access required to generate posts.")
                else:
                    if st.button(btn_label, type="primary", key=f"synth_btn_{story_id}_{has_render}", use_container_width=True):
                        st.toast("Synthesizing Post... 🔄", icon="⏳")
                        from services.queue_service import handle_generate_story_action, transition_article_status
                        updated_s, err = handle_generate_story_action(story)
                        if err:
                            st.toast(f"Generation Error: {err}", icon="❌")
                        else:
                            transition_article_status(s_dict, "post_ready")
                            st.toast("Post Synthesized Successfully! ✅", icon="✨")
                            time.sleep(1.5)
                            st.cache_data.clear()
                            st.rerun()
                            
            with col_a2:
                if not is_admin_authenticated():
                    st.button("🔒 Approve", disabled=True, use_container_width=True, help="Admin access required.")
                else:
                    if st.button("Approve", type="primary", disabled=(current_status != "post_ready" or not has_render), use_container_width=True):
                        from services.queue_service import transition_article_status
                        transition_article_status(s_dict, "approved")
                        st.toast("Post Approved and Ready! 🚀", icon="✅")
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun()
                    
            with col_a3:
                if not is_admin_authenticated():
                    st.button("🔒 Reject", disabled=True, use_container_width=True, help="Admin access required.")
                else:
                    if st.button("Reject", disabled=(current_status not in ["new", "post_ready"]), use_container_width=True):
                        from services.queue_service import transition_article_status
                        transition_article_status(s_dict, "rejected")
                        st.toast("Story Rejected.", icon="🗑️")
                        time.sleep(1)
                        st.cache_data.clear()
                        st.session_state.selected_story_id = None
                        st.rerun()
                    
            with col_a4:
                if has_render:
                    with open(render_path, "rb") as f:
                        st.download_button("Save PNG", f, file_name=f"cipherbrief_{story_id}.png", mime="image/png", use_container_width=True)
                    
                    mp4_path = render_path.replace(".png", ".mp4")
                    if os.path.exists(mp4_path):
                        with open(mp4_path, "rb") as f2:
                            st.download_button("Download MP4", f2, file_name=f"cipherbrief_{story_id}.mp4", mime="video/mp4", use_container_width=True)

    # ==========================================
    # 8. PAGE ROUTING & RENDERING
    # ==========================================

    # If a specific story is selected, show detail view (overrides page routing)
    if st.session_state.selected_story_id:
        # Find story
        selected_story = next((s for s in stories if s.story_id == st.session_state.selected_story_id), None)
        if selected_story:
            render_story_detail(selected_story)
        else:
            st.error("Story not found.")
            st.button("Back", on_click=lambda: st.session_state.update(selected_story_id=None))

    else:
        if st.session_state.active_page == "Overview":
            components.html("""
    <style>
        #ist-clock-container {
            display: flex; 
            justify-content: space-between; 
            align-items: flex-end; 
            margin-bottom: 32px; 
            font-family: 'Inter', sans-serif;
        }
        @media (max-width: 768px) {
            #ist-clock-container {
                flex-direction: column;
                align-items: flex-start;
                margin-bottom: 16px;
            }
            #ist-clock-container > div:last-child {
                text-align: left !important;
                padding-left: 0 !important;
                margin-top: 16px;
            }
            #ist-clock-time {
                font-size: 28px !important;
            }
        }
    </style>
    <div id="ist-clock-container">
        <div>
            <h2 id="ist-clock-time" style="font-size:32px; font-weight:700; color:#F5F7FA; margin-bottom:4px; font-variant-numeric: tabular-nums; line-height: 1.2; margin-top: 0;">--:--:--</h2>
            <div id="ist-clock-date" style="color:#9299A5; text-transform:uppercase; font-size:12px; letter-spacing:1px;">--</div>
        </div>
        <div style="max-width: 600px; text-align: right; color: rgba(255,255,255,0.4); font-size: 13px; font-style: italic; line-height: 1.5; padding-left: 20px;">
            “The wars will end and the leaders will shake hands, and that old woman will remain waiting for her martyred son, and that girl will wait for her beloved husband, and the children will wait for their heroic father, I do not know who sold the homeland but I know who paid the price.”<br>
            <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: rgba(255,255,255,0.25); font-style: normal; margin-top: 6px; display: inline-block;">— Mahmoud Darwish</span>
        </div>
    </div>
    <script>
        function updateClock() {
            const timeEl = document.getElementById('ist-clock-time');
            const dateEl = document.getElementById('ist-clock-date');
            if (!timeEl) return;
            
            const now = new Date();
            const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
            const ist = new Date(utc + (3600000 * 5.5));
            
            const timeStr = ist.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const dateStr = ist.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) + " (IST)";
            
            timeEl.innerText = timeStr;
            dateEl.innerText = dateStr;
        }
        setInterval(updateClock, 1000);
        updateClock();
    </script>
    """, height=120)
            
            m1, m2, m3, m4 = st.columns(4)
            active_count = len([s for s in stories if s.status not in ["rejected"]])
            posts_ready_count = len([s for s in stories if s.status == "post_ready"])
            approved_count = len([s for s in stories if s.status == "approved"])
            avg_score = f"{sum(s.overall_story_score for s in stories) / max(1, len(stories)):.1f}"
            
            m1.metric("Active Stories", active_count)
            m2.metric("Posts Ready", posts_ready_count)
            m3.metric("Approved Posts", approved_count)
            m4.metric("Avg. Story Score", avg_score)
            
            st.markdown("<br><div class='section-header'>TOP STORIES</div><div class='section-title'>Latest high-priority developments</div>", unsafe_allow_html=True)
            
            # Show top 6 stories sorted by score from the filtered subset
            top_stories = sorted(filtered_stories, key=lambda s: s.overall_story_score, reverse=True)[:6]
            if not top_stories:
                st.info("NO STORIES YET. Adjust your filters or wait for the next news cycle.")
            else:
                cols = st.columns(3)
                for i, story in enumerate(top_stories):
                    with cols[i % 3]:
                        render_story_card(story)

        else:
            # All Stories, Post Ready, or Approved Pages
            st.markdown(f"<div class='section-header'>{st.session_state.active_page.upper()}</div><div class='section-title'>Live News Cycle</div>", unsafe_allow_html=True)
            
            if not filtered_stories:
                if st.session_state.active_page == "Post Ready":
                    st.info("NO POSTS READY. Synthesize an active story to create your next CipherBrief post.")
                elif st.session_state.active_page == "Approved":
                    st.info("NO APPROVED POSTS. Approve a ready post to stage it for publishing.")
                else:
                    st.info("No active news stories match the selected filters.")
            else:
                PER_PAGE = 10
                pages = max(1, math.ceil(len(filtered_stories) / PER_PAGE))
                
                page_key = f"page_{st.session_state.active_page}"
                if page_key not in st.session_state:
                    st.session_state[page_key] = 1
                page = st.session_state[page_key]
                if page > pages:
                    page = pages
                    st.session_state[page_key] = page
                
                start_idx = (page - 1) * PER_PAGE
                end_idx = start_idx + PER_PAGE
                paged_stories = filtered_stories[start_idx:end_idx]
                
                cols = st.columns(3)
                for i, story in enumerate(paged_stories):
                    with cols[i % 3]:
                        render_story_card(story)

                if pages > 1:
                    st.markdown("<br><hr style='border-color: rgba(255,255,255,0.05); margin: 32px 0;'>", unsafe_allow_html=True)
                    
                    html_logo = "<div style='text-align: center; font-size: 42px; font-weight: 800; margin-bottom: 8px; font-family: sans-serif; letter-spacing: -2px;'>"
                    html_logo += "<span style='color: var(--text-muted)'>BriefBot</span>"
                    html_logo += "</div>"
                    st.markdown(html_logo, unsafe_allow_html=True)
                    
                    st.markdown("""
                    <style>
                    div[data-testid="stHorizontalBlock"]:has(button[kind="tertiary"]) {
                        justify-content: center !important;
                        gap: 4px !important;
                    }
                    div[data-testid="stHorizontalBlock"]:has(button[kind="tertiary"]) > div[data-testid="column"] {
                        width: auto !important;
                        flex: 0 1 auto !important;
                        min-width: 0 !important;
                    }
                    button[kind="tertiary"] {
                        color: #4DA3FF !important;
                        font-weight: 600 !important;
                        font-size: 14px !important;
                        padding: 4px 8px !important;
                        background: transparent !important;
                        border: none !important;
                    }
                    button[kind="tertiary"]:hover {
                        color: #F5F7FA !important;
                        background: transparent !important;
                        text-decoration: underline !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    btn_cols = st.columns(pages + (1 if page < pages else 0))
                    for p in range(1, pages + 1):
                        with btn_cols[p-1]:
                            if st.button(str(p), key=f"pag_btn_{p}_{page_key}", type="tertiary", disabled=(p == page)):
                                st.session_state[page_key] = p
                                st.rerun()
                    if page < pages:
                        with btn_cols[pages]:
                            if st.button("Next", key=f"pag_btn_next_{page_key}", type="tertiary"):
                                st.session_state[page_key] = page + 1
                                st.rerun()


