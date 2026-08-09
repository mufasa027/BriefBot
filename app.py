import streamlit as st
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
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* CSS Variables for Premium Dark Theme */
    :root {
        --bg-main: #0B0E14;
        --bg-surface: #151A22;
        --bg-secondary: #151922;
        --border-color: #242933;
        --text-primary: #F5F7FA;
        --text-secondary: #9299A5;
        --text-muted: #666D78;
        --accent-blue: #4DA3FF;
        --accent-success: #3DDC97;
        --accent-warning: #F4C95D;
        --accent-danger: #FF5C5C;
    }

    /* Base Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        background-color: var(--bg-main) !important;
        color: var(--text-primary) !important;
    }

    /* Hide Streamlit Chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Block container adjustments */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }

    /* Streamlit sidebar */
    [data-testid="stSidebar"] {
        background-color: var(--bg-surface) !important;
        border-right: 1px solid var(--border-color);
    }
    
    /* Metric Cards */
    [data-testid="metric-container"] {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-color);
        border-radius: 4px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    [data-testid="metric-container"] label {
        color: var(--text-secondary) !important;
        font-size: 13px !important;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    [data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-weight: 600;
    }

    /* Custom Containers & Borders */
    div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
        padding: 1rem;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 4px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        border-color: var(--accent-blue) !important;
        background-color: var(--bg-surface) !important;
    }
    /* Primary Button override */
    .stButton > button[kind="primary"] {
        background-color: var(--accent-blue) !important;
        color: #000 !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-new { background-color: #242933; color: #F5F7FA; border: 1px solid #3b4252; }
    .badge-post_ready { background-color: rgba(77, 163, 255, 0.15); color: #4DA3FF; border: 1px solid rgba(77, 163, 255, 0.3); }
    .badge-approved { background-color: rgba(61, 220, 151, 0.15); color: #3DDC97; border: 1px solid rgba(61, 220, 151, 0.3); }
    .badge-rejected { background-color: rgba(255, 92, 92, 0.15); color: #FF5C5C; border: 1px solid rgba(255, 92, 92, 0.3); }

    /* Story Card Typography */
    .story-headline {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .story-meta {
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 12px;
    }
    .story-summary {
        font-size: 14px;
        color: var(--text-muted);
        line-height: 1.5;
        margin-bottom: 12px;
    }
    
    /* Top Header */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 16px;
        margin-bottom: 24px;
    }
    .app-title {
        font-size: 24px;
        font-weight: 700;
        letter-spacing: 1px;
        margin: 0;
        line-height: 1;
    }
    .app-subtitle {
        font-size: 12px;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 6px;
    }
    .system-status {
        font-size: 12px;
        color: var(--accent-success);
        font-weight: 500;
    }
    
</style>
""", unsafe_allow_html=True)


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
if 'active_page' not in st.session_state:
    st.session_state.active_page = 'Overview'
if 'selected_story_id' not in st.session_state:
    st.session_state.selected_story_id = None


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
    st.markdown("<h3 style='font-size:14px; color:#9299A5; text-transform:uppercase; margin-bottom:12px;'>Navigation</h3>", unsafe_allow_html=True)
    
    # Custom Navigation
    page_options = {
        "Overview": "",
        "All Stories": "",
        "Post Ready": "",
        "Approved": ""
    }
    
    for page, icon in page_options.items():
        if st.button(f"{page}", key=f"nav_{page}", use_container_width=True, type="primary" if st.session_state.active_page == page else "secondary"):
            st.session_state.active_page = page
            st.session_state.selected_story_id = None
            st.rerun()

    st.markdown("<br><hr style='border-color: #242933;'><br>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='font-size:14px; color:#9299A5; text-transform:uppercase; margin-bottom:12px;'>Actions</h3>", unsafe_allow_html=True)
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
            time.sleep(2)
            st.cache_data.clear()
            st.rerun()

    st.markdown("<br><hr style='border-color: #242933;'><br>", unsafe_allow_html=True)
    
    st.markdown("<h3 style='font-size:14px; color:#9299A5; text-transform:uppercase; margin-bottom:12px;'>Filters</h3>", unsafe_allow_html=True)
    
    with st.form("filter_form"):
        search = st.text_input("Search", placeholder="Search stories...")
        
        categories = ["All"] + sorted(list(set([s.category for s in stories if s.category]))) if stories else ["All"]
        category = st.selectbox("Category", categories)
        
        sources_list = ["All"] + sorted(list(set([s.primary_source for s in stories if s.primary_source]))) if stories else ["All"]
        source_filter = st.selectbox("Source", sources_list)
        
        min_score = st.slider("Min Score", 0, 100, 0, 5)
        
        st.form_submit_button("Apply Filters", use_container_width=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.expander("System Diagnostics"):
        if st.button("Run Health Check"):
            diag = run_database_diagnostics()
            st.json(diag)

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
    sort_by = st.selectbox("Sort By", ["Latest", "Score: High to Low", "Score: Low to High"])
    if sort_by == "Latest":
        def get_ts(s):
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(s.first_published).timestamp()
            except:
                return 0
        filtered_stories = sorted(filtered_stories, key=get_ts, reverse=True)
    elif sort_by == "Score: High to Low":
        filtered_stories = sorted(filtered_stories, key=lambda s: s.overall_story_score, reverse=True)
    elif sort_by == "Score: Low to High":
        filtered_stories = sorted(filtered_stories, key=lambda s: s.overall_story_score)


# ==========================================
# 7. RENDER HELPER FUNCTIONS
# ==========================================
def render_story_card(story):
    """Renders a compact, editorial story card."""
    s_dict = story.to_dict()
    current_status = str(story.status or "new").lower()
    
    badge_class = f"badge-{current_status}" if current_status in ["new", "post_ready", "approved", "rejected"] else "badge-new"
    
    primary_art = story.articles[0] if story.articles else {}
    summary = primary_art.get('summary', '')
    if len(summary) > 150:
        summary = summary[:147] + "..."
        
    with st.container(border=True):
        st.markdown(f"""
        <div style='display:flex; justify-content:space-between; align-items:flex-start;'>
            <div>
                <div class='story-headline'>{story.story_title}</div>
                <div class='story-meta'>{story.primary_source} &nbsp;·&nbsp; {story.first_published[:16] if story.first_published else ''}</div>
            </div>
            <div style='text-align:right;'>
                <div style='font-size:24px; font-weight:700; color:var(--accent-blue); line-height:1;'>{story.overall_story_score}</div>
                <div style='font-size:10px; color:var(--text-muted); margin-bottom:8px;'>SCORE</div>
            </div>
        </div>
        <div class='story-summary'>{summary}</div>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
                <span class='badge {badge_class}'>{current_status.upper().replace('_', ' ')}</span>
                <span style='margin-left:12px; font-size:12px; color:var(--text-secondary); text-transform:uppercase;'>{story.category}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Add a button underneath the HTML rendering
        if st.button("Review Story", key=f"btn_review_{story.story_id}"):
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
    
    # Check assets
    render_path = story.rendered_image_path or get_render_path_for_uuid(story_id)
    has_render = bool(render_path and os.path.exists(render_path) and os.path.getsize(render_path) > 100)
    
    cap_p = os.path.join(CAPTIONS_DIR, f"caption_{story_id}.txt")
    has_caption_file = os.path.exists(cap_p) and os.path.getsize(cap_p) > 10
    
    hash_p = os.path.join(HASHTAGS_DIR, f"hashtags_{story_id}.txt")
    has_hashtags_file = os.path.exists(hash_p) and os.path.getsize(hash_p) > 10

    # Load missing texts from files
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
        st.markdown("<h3 style='font-size:14px; color:#9299A5; margin-bottom:16px;'>POST PREVIEW</h3>", unsafe_allow_html=True)
        if current_status == "approved":
            st.markdown("<div style='background:rgba(61, 220, 151, 0.1); border:1px solid #3DDC97; color:#3DDC97; padding:12px; border-radius:6px; text-align:center; font-weight:600; margin-bottom:16px;'>✓ APPROVED — READY TO POST</div>", unsafe_allow_html=True)
        elif current_status == "post_ready":
            st.markdown("<div style='background:rgba(77, 163, 255, 0.1); border:1px solid #4DA3FF; color:#4DA3FF; padding:12px; border-radius:6px; text-align:center; font-weight:600; margin-bottom:16px;'>POST READY</div>", unsafe_allow_html=True)

        if has_render:
            try:
                from PIL import Image
                img = Image.open(render_path)
                st.image(img, use_container_width=True)
                st.markdown("<div style='text-align:center; font-size:11px; color:#666D78; margin-top:8px;'>1080 × 1920 · PNG</div>", unsafe_allow_html=True)
            except OSError:
                st.error("Image exists but could not be loaded.")
        else:
            st.info("Visual render not yet generated. Synthesize post to create.")

    with c2:
        st.markdown("<h3 style='font-size:14px; color:#9299A5; margin-bottom:16px;'>EDITORIAL BRIEF</h3>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown(f"""
            <div style='font-size:22px; font-weight:600; margin-bottom:12px;'>{story.story_title}</div>
            <div style='display:flex; justify-content:space-between; border-bottom:1px solid #242933; padding-bottom:12px; margin-bottom:12px;'>
                <div><span style='color:#9299A5; font-size:12px;'>SOURCE</span><br>{story.primary_source}</div>
                <div><span style='color:#9299A5; font-size:12px;'>CATEGORY</span><br>{story.category}</div>
                <div><span style='color:#9299A5; font-size:12px;'>SCORE</span><br><span style='color:#4DA3FF; font-weight:700;'>{story.overall_story_score}/100</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**AI Analysis & Reasoning**")
            primary_art = story.articles[0] if story.articles else {}
            explanation_points = generate_score_explanation(primary_art, story.num_sources)
            for point in explanation_points:
                st.markdown(f"- {point}")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Caption section
        st.markdown("<h3 style='font-size:14px; color:#9299A5; margin-bottom:8px;'>CAPTION</h3>", unsafe_allow_html=True)
        if caption_text:
            st.code(caption_text, language="text")
        else:
            st.info("No caption generated yet.")
            
        # Hashtags section
        st.markdown("<h3 style='font-size:14px; color:#9299A5; margin-top:24px; margin-bottom:8px;'>HASHTAGS</h3>", unsafe_allow_html=True)
        if hashtags_text:
            # Display as a code block for easy copying
            st.code(hashtags_text, language="text")
        else:
            st.info("No hashtags generated yet.")
            
        st.markdown("<hr style='border-color: #242933;'>", unsafe_allow_html=True)
        
        # Action Buttons
        st.markdown("<h3 style='font-size:14px; color:#9299A5; margin-bottom:16px;'>WORKFLOW ACTIONS</h3>", unsafe_allow_html=True)
        
        col_a1, col_a2, col_a3, col_a4 = st.columns(4)
        
        with col_a1:
            btn_label = "Re-synthesize" if has_render else "Synthesize"
            if st.button(btn_label, key=f"synth_btn_{story_id}_{has_render}", disabled=(current_status in ["approved", "rejected"]), use_container_width=True):
                with st.status("Synthesizing Post...", expanded=True) as status:
                    st.write("Analyzing story metrics...")
                    st.write("Generating editorial copy...")
                    st.write("Rendering 1080x1920 layout...")
                    updated_s, err = handle_generate_story_action(story)
                    if err:
                        status.update(label=f"Generation Error: {err}", state="error")
                    else:
                        transition_article_status(s_dict, "post_ready")
                        status.update(label="Post Synthesized Successfully", state="complete")
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun()
                        
        with col_a2:
            if st.button("Approve", disabled=(current_status != "post_ready" or not has_render), use_container_width=True):
                transition_article_status(s_dict, "approved")
                st.cache_data.clear()
                st.rerun()
                
        with col_a3:
            if st.button("Reject", disabled=(current_status not in ["new", "post_ready"]), use_container_width=True):
                transition_article_status(s_dict, "rejected")
                st.cache_data.clear()
                st.session_state.selected_story_id = None
                st.rerun()
                
        with col_a4:
            if has_render:
                with open(render_path, "rb") as f:
                    st.download_button("Download Image", f, file_name=f"cipherbrief_{story_id}.png", mime="image/png", use_container_width=True)
                
                mp4_path = render_path.replace(".png", ".mp4")
                if os.path.exists(mp4_path):
                    with open(mp4_path, "rb") as f2:
                        st.download_button("Download MP4 Reel", f2, file_name=f"cipherbrief_{story_id}.mp4", mime="video/mp4", use_container_width=True)



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
<div id="ist-clock-container" style="margin-bottom:32px; font-family: 'Inter', sans-serif;">
    <h2 id="ist-clock-time" style="font-size:32px; font-weight:700; color:#F5F7FA; margin-bottom:4px; font-variant-numeric: tabular-nums; line-height: 1.2; margin-top: 0;">--:--:--</h2>
    <div id="ist-clock-date" style="color:#9299A5; text-transform:uppercase; font-size:12px; letter-spacing:1px;">--</div>
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
""", height=100)
        
        m1, m2, m3, m4 = st.columns(4)
        active_count = len([s for s in stories if s.status not in ["rejected"]])
        posts_ready_count = len([s for s in stories if s.status == "post_ready"])
        approved_count = len([s for s in stories if s.status == "approved"])
        avg_score = f"{sum(s.overall_story_score for s in stories) / max(1, len(stories)):.1f}"
        
        m1.metric("Active Stories", active_count)
        m2.metric("Posts Ready", posts_ready_count)
        m3.metric("Approved Posts", approved_count)
        m4.metric("Avg. Story Score", avg_score)
        
        st.markdown("<br><h3 style='font-size:20px; font-weight:600; margin-bottom:16px;'>Top Stories</h3>", unsafe_allow_html=True)
        
        # Show top 6 stories sorted by score from the filtered subset
        top_stories = sorted(filtered_stories, key=lambda s: s.overall_story_score, reverse=True)[:6]
        if not top_stories:
            st.info("NO STORIES YET. Adjust your filters or wait for the next news cycle.")
        else:
            r1, r2 = st.columns(2)
            for i, story in enumerate(top_stories):
                with (r1 if i % 2 == 0 else r2):
                    render_story_card(story)

    else:
        # All Stories, Post Ready, or Approved Pages
        st.markdown(f"<h2 style='font-size:24px; font-weight:600; margin-bottom:24px;'>{st.session_state.active_page}</h2>", unsafe_allow_html=True)
        
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
            page = st.number_input("Page Number", min_value=1, max_value=pages, value=1, step=1)
            
            start_idx = (page - 1) * PER_PAGE
            end_idx = start_idx + PER_PAGE
            paged_stories = filtered_stories[start_idx:end_idx]
            
            c1, c2 = st.columns(2)
            for i, story in enumerate(paged_stories):
                with (c1 if i % 2 == 0 else c2):
                    render_story_card(story)

