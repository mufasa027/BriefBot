import streamlit as st
import pandas as pd
import math
import os

from database.crud import get_all_stories
from services.queue_service import handle_generate_story_action, transition_article_status
from services.publishing_service import publish_approved_story_as_reel
from services import logging_service
import importlib
importlib.reload(logging_service)
from services.storage_service import get_render_path_for_uuid, CAPTIONS_DIR, HASHTAGS_DIR, ARTICLES_DIR
from database.diagnostics import run_database_diagnostics
from ai.ranker import generate_score_explanation
from database.migrations import create_database

# Initialize database to prevent "no such table" errors on first run
create_database()

st.set_page_config(
    page_title="CipherBrief Newsroom",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    max-width: 1450px;
}
</style>
""", unsafe_allow_html=True)

st.title("📰 CipherBrief AI Newsroom")
st.caption("Autonomous Story Clustering, Multi-Source Synthesis & Multi-Platform Publisher")

# -----------------------
# DATA LOAD & AUTO CLUSTER
# -----------------------
@st.cache_data(ttl=30)
def load_story_data():
    return get_all_stories(limit=100)

stories = load_story_data()

# -----------------------
# SIDEBAR CONTROLS
# -----------------------
st.sidebar.title("⚡ CipherBrief Control Panel")

if st.sidebar.button("📥 Fetch & Process Latest News", use_container_width=True):
    from settings import OPENROUTER_API_KEY
    if not OPENROUTER_API_KEY:
        st.sidebar.error("❌ OPENROUTER_API_KEY is not set in Streamlit Secrets!")
    else:
        with st.spinner("Fetching and clustering news (this may take a few minutes)..."):
            try:
                import main
                import sys
                from io import StringIO
                
                # Capture output to avoid spamming the console and to count success
                original_stdout = sys.stdout
                sys.stdout = StringIO()
                try:
                    main.main()
                finally:
                    output = sys.stdout.getvalue()
                    sys.stdout = original_stdout
                
                st.sidebar.success("✅ News fetched & processed successfully!")
                with st.sidebar.expander("View Logs"):
                    st.text(output)
            except Exception as e:
                st.sidebar.error(f"❌ Error fetching news: {e}")
            
            # Delay rerun slightly so the user can read the success message
            import time
            time.sleep(3)
            st.cache_data.clear()
            st.rerun()

if st.sidebar.button("🔄 Refresh View", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

search = st.sidebar.text_input("🔍 Search News Stories", placeholder="Search title or topics...")

status_filter = st.sidebar.selectbox(
    "Workflow Status",
    ["All", "new", "generated", "approved", "rejected", "queued", "published", "failed"]
)

categories = ["All"] + sorted(list(set([s.category for s in stories if s.category]))) if stories else ["All"]
category = st.sidebar.selectbox("Category", categories)

min_score = st.sidebar.slider("Minimum Story Score", 0, 100, 0, 5)

# -----------------------
# FILTER LOGIC & SEARCH
# -----------------------
filtered_stories = stories
if filtered_stories:
    if search:
        s_lower = search.lower()
        filtered_stories = [s for s in filtered_stories if (
            s_lower in s.story_title.lower() or 
            (s.caption and s_lower in s.caption.lower()) or 
            (s.hashtags and s_lower in s.hashtags.lower()) or 
            s_lower in s.category.lower() or 
            s_lower in s.primary_source.lower() or 
            s_lower in s.story_id.lower() or
            any(s_lower in art.get('summary', '').lower() for art in s.articles)
        )]

    if status_filter != "All":
        filtered_stories = [s for s in filtered_stories if s.status == status_filter]

    if category != "All":
        filtered_stories = [s for s in filtered_stories if s.category == category]

    filtered_stories = [s for s in filtered_stories if s.overall_story_score >= min_score]

# -----------------------
# MAIN TABS
# -----------------------
tab_newsroom, tab_queue, tab_analytics = st.tabs(["📰 Newsroom", "🚀 Publishing Queue", "📈 Analytics"])

with tab_newsroom:
    # -----------------------
        # METRICS KPI DASHBOARD
        # -----------------------
    m1, m2, m3, m4, m5 = st.columns(5)
    total_stories = len(filtered_stories)
    approved_count = len([s for s in stories if s.status == "approved"])
    rejected_count = len([s for s in stories if s.status == "rejected"])
    published_count = len([s for s in stories if s.status == "published"])
    avg_score = f"{sum([s.overall_story_score for s in stories]) / max(1, len(stories)):.1f}/100" if stories else "N/A"

    m1.metric("Active Stories", total_stories)
    m2.metric("Approved Stories", approved_count)
    m3.metric("Rejected Stories", rejected_count)
    m4.metric("Published Stories", published_count)
    m5.metric("Avg Story Score", avg_score)

    st.divider()

    # -----------------------
    # PAGINATION
    # -----------------------
    PER_PAGE = 10
    pages = max(1, math.ceil(len(filtered_stories) / PER_PAGE))
    page = st.number_input("Page Number", min_value=1, max_value=pages, value=1, step=1)

    start_idx = (page - 1) * PER_PAGE
    end_idx = start_idx + PER_PAGE
    paged_stories = filtered_stories[start_idx:end_idx] if filtered_stories else []

    # -----------------------
    # STORY NEWSROOM CARDS
    # -----------------------
    if not paged_stories:
        st.info("No active news stories match the selected filters.")
    else:
        for story in paged_stories:
            s_dict = story.to_dict()
            story_id = story.story_id
            articles = story.articles
            current_status = str(story.status or "new").lower()

            # Asset Checks
            render_path = story.rendered_image_path or get_render_path_for_uuid(story_id)
            has_render = bool(render_path and os.path.exists(render_path) and os.path.getsize(render_path) > 100)

            cap_p = os.path.join(CAPTIONS_DIR, f"caption_{story_id}.txt")
            has_caption_file = os.path.exists(cap_p) and os.path.getsize(cap_p) > 10

            hash_p = os.path.join(HASHTAGS_DIR, f"hashtags_{story_id}.txt")
            has_hashtags_file = os.path.exists(hash_p) and os.path.getsize(hash_p) > 10

            meta_p = os.path.join(ARTICLES_DIR, current_status, f"article_{story_id}.json")
            has_meta_file = os.path.exists(meta_p) and os.path.getsize(meta_p) > 0

            primary_art = articles[0] if articles else {}
            primary_img_url = primary_art.get("image_url", "")
            has_img_url = bool(primary_img_url and str(primary_img_url) != "nan" and str(primary_img_url).startswith("http"))

            with st.container(border=True):
                header_col1, header_col2 = st.columns([4, 1])

                with header_col1:
                    st.subheader(story.story_title)
                    # Feature 3: Multi-Source Story Card Chips
                    sources_html = f"<span style='background-color:#1E88E5; padding:2px 8px; border-radius:12px; font-size:12px; margin-right:5px;'>{story.primary_source}</span>"
                    for src in story.supporting_sources:
                        sources_html += f"<span style='background-color:#424242; padding:2px 8px; border-radius:12px; font-size:12px; margin-right:5px;'>{src}</span>"
                    st.markdown(sources_html, unsafe_allow_html=True)
                    st.caption(f"🏷️ Category: {story.category} | ⏰ First published: {story.first_published}")

                with header_col2:
                    st.markdown(f"### 🔥 **{story.overall_story_score}**/100")
                    st.caption(f"Status: `{current_status.upper()}`")
                    if current_status == "failed" and getattr(story, "publish_error", None):
                        st.error(story.publish_error)

                # Feature 1 & 2: Editorial Review Panel & Explainability
                with st.expander(f"🔍 Editorial Review Panel (View Details & AI Analysis)"):
                    er_col1, er_col2 = st.columns(2)
                    
                    with er_col1:
                        st.markdown("#### 📝 Story Content")
                        st.write(f"**Original Headline:** {primary_art.get('title')}")
                        st.write(f"**AI Rewritten Headline:** {story.story_title}")
                        st.write(f"**Summary:** {primary_art.get('summary')}")
                        st.write(f"**Source:** {story.primary_source}")
                        st.write(f"**Published Time:** {story.first_published}")
                        
                        st.markdown("#### 📷 Generation Assets")
                        st.write(f"**Caption:** {story.caption or 'Not generated yet'}")
                        st.write(f"**Hashtags:** {story.hashtags or 'Not generated yet'}")
                        
                        st.markdown("#### 🔗 Coverage Links")
                        for idx, art in enumerate(articles, 1):
                            st.caption(f"{idx}. [{art.get('source')}] {art.get('title')} ({art.get('published')})")
                            if art.get("url") and pd.notna(art.get("url")):
                                st.markdown(f"[Read on {art.get('source')}]({art.get('url')})")
                                
                    with er_col2:
                        st.markdown("#### 🧠 AI Score Explainability")
                        st.markdown(f"**Overall Score: {story.overall_story_score}/100**")
                        st.markdown("*Why?*")
                        explanation_points = generate_score_explanation(primary_art, story.num_sources)
                        for point in explanation_points:
                            st.markdown(f"• {point}")
                            
                        st.markdown("#### 📊 Sub-Scores")
                        st.write(f"- Importance: {primary_art.get('importance', 0)*10}/100")
                        st.write(f"- Virality Potential: {primary_art.get('virality_score', 0)}/100")
                        st.write(f"- Growth Potential: {primary_art.get('growth_score', 0)}/100")
                        st.write(f"- Freshness: {primary_art.get('freshness_score', 0)}/100")
                        
                        st.markdown("#### 🗄️ Database Records")
                        st.write(f"**Story UUID:** `{story_id}`")
                        st.write(f"**Primary Article ID:** `{story.primary_article_id}`")
                        if story.instagram_media_id:
                            st.write(f"**Instagram Media ID:** `{story.instagram_media_id}`")
                            st.write(f"**Reel Path:** `{story.reel_video_path}`")
                            
                        # Feature 7: Audit Log
                        st.markdown("#### 📜 Audit Log Timeline")
                        audit_logs = logging_service.get_audit_log_for_story(story_id)
                        audit_text = "\\n".join(audit_logs)
                        st.code(audit_text, language="text")

                # Actions Row
                a1, a2, a3, a4, a5 = st.columns(5)

                # 1. GENERATE / SYNTHESIZE STORY POST
                if a1.button("⚡ Synthesize Post", key=f"gen_s_{story_id}"):
                    with st.spinner("Synthesizing multi-source copy & rendering post..."):
                        updated_s, err = handle_generate_story_action(story)
                        if err:
                            st.error(f"Generation Error: {err}")
                        else:
                            st.success("✓ Multi-source story post synthesized!")
                            st.cache_data.clear()
                            st.rerun()

                # 2. PREVIEW (Bug #1 Fix)
                with a2.popover("👁️ Live Preview"):
                    st.markdown("### 📱 Instagram Story Render Preview")

                    if has_render:
                        try:
                            from PIL import Image
                            st.image(Image.open(render_path), use_container_width=True)
                        except OSError as e:
                            st.error(f"⚠️ Live Preview Error: Could not render image ({e})")
                    else:
                        st.warning("⚠️ Render PNG missing or invalid. Please click 'Synthesize Post' first.")

                    # Load caption from file if missing from memory
                    caption_text = story.caption
                    if (not caption_text or pd.isna(caption_text)) and os.path.exists(cap_p):
                        try:
                            with open(cap_p, "r", encoding="utf-8") as f:
                                caption_text = f.read()
                        except OSError:
                            pass

                    # Load hashtags from file if missing from memory
                    hashtags_text = story.hashtags
                    if (not hashtags_text or pd.isna(hashtags_text)) and os.path.exists(hash_p):
                        try:
                            with open(hash_p, "r", encoding="utf-8") as f:
                                hashtags_text = f.read()
                        except OSError:
                            pass

                    st.markdown("**Synthesized Caption:**")
                    if caption_text:
                        st.text_area("Caption", caption_text, height=120, key=f"cap_area_s_{story_id}")
                    else:
                        st.error("⚠️ Caption missing or failed generation.")

                    st.markdown("**Hashtags (Exactly 10 Tags):**")
                    if hashtags_text:
                        st.code(hashtags_text, language="text")
                    else:
                        st.error("⚠️ Hashtags missing or failed generation.")

                    st.markdown("**Metadata:**")
                    st.caption(f"⭐ Primary Source: `{story.primary_source}`")
                    st.caption(f"📁 Image Path: `{render_path}`")
                    st.caption(f"⏰ Generated Time: `{story.generated_time or 'N/A'}`")

                # 3. APPROVE
                if a3.button("✅ Approve Story", key=f"app_s_{story_id}"):
                    if not has_render or not has_caption_file:
                        st.error("Cannot approve: Required assets (render PNG, caption.txt) missing. Click 'Synthesize Post' first.")
                    else:
                        transition_article_status(s_dict, "approved")
                        st.success("Story Approved!")
                        st.cache_data.clear()
                        st.rerun()

                # 4. REJECT
                if a4.button("❌ Reject Story", key=f"rej_s_{story_id}"):
                    transition_article_status(s_dict, "rejected")
                    st.warning("Story Rejected.")
                    st.cache_data.clear()
                    st.rerun()

                # 5. PUBLISH STORY (Reels)
                if a5.button("🚀 Publish Reel", key=f"pub_s_{story_id}", disabled=(current_status != "approved")):
                    with st.spinner("Generating MP4 & Publishing Reel to Instagram..."):
                        success, res_msg = publish_approved_story_as_reel(s_dict)
                        if success:
                            st.balloons()
                            st.success(f"✓ Published as Reel! IG Media ID: {res_msg}")
                        else:
                            st.error(f"Publish Failed: {res_msg}")
                        st.cache_data.clear()
                        st.rerun()

    # -----------------------
    # SYSTEM LOGS & DIAGNOSTICS
    # -----------------------
    with st.expander("🩺 System Diagnostics & Health Check (Bug #6)"):
        diag = run_database_diagnostics()
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Total Articles in DB", diag["total_articles"])
        d2.metric("Total Stories Clustered", diag["total_stories"])
        d3.metric("Duplicate URLs", diag["duplicate_urls_count"])
        d4.metric("Broken File Paths", diag["broken_file_paths_count"])

        if diag["is_healthy"]:
            st.success("✓ Database Health Check Passed: No orphan records or broken assets detected.")
        else:
            st.warning(f"⚠️ Health Notice: Missing Captions={diag['missing_captions_count']}, Missing Images={diag['missing_images_count']}")

    with st.expander("📋 System Activity Logs"):
        logs = logging_service.get_recent_logs(30)
        st.code("".join(logs) if logs else "No system logs recorded yet.", language="text")

with tab_queue:
    st.subheader("🚀 Publishing Queue")
    st.markdown("Track the status of approved and publishing stories.")
    
    queued = [s for s in stories if s.status == "queued"]
    publishing = [s for s in stories if s.status == "publishing"]
    published = [s for s in stories if s.status == "published"]
    failed = [s for s in stories if s.status == "failed"]
    
    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    q_col1.metric("Queued", len(queued))
    q_col2.metric("Publishing", len(publishing))
    q_col3.metric("Published", len(published))
    q_col4.metric("Failed", len(failed))
    
    st.divider()
    
    # Render queue rows
    all_queue_stories = queued + publishing + published + failed
    all_queue_stories = sorted(all_queue_stories, key=lambda s: s.latest_update, reverse=True)
    
    if not all_queue_stories:
        st.info("No stories in the publishing pipeline currently.")
    else:
        for sq in all_queue_stories:
            with st.container(border=True):
                qc1, qc2, qc3 = st.columns([3, 1, 1])
                qc1.markdown(f"**{sq.story_title}**")
                
                status_color = {"queued": "🔵", "publishing": "🟡", "published": "🟢", "failed": "🔴"}
                icon = status_color.get(sq.status, "⚪")
                qc2.markdown(f"{icon} **{str(sq.status).upper()}**")
                
                # timestamps
                if sq.status == "published":
                    qc3.caption(f"Published: {sq.posted_time}")
                elif sq.status == "failed":
                    qc3.caption(f"Failed: {sq.rejected_time or sq.latest_update}")
                    if getattr(sq, "publish_error", None):
                        st.error(sq.publish_error)
                else:
                    qc3.caption(f"Approved: {sq.approved_time or sq.latest_update}")


with tab_analytics:
    st.subheader("📈 Newsroom Analytics")
    st.markdown("Performance metrics and global dashboard.")
    
    # Calculate Analytics
    today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
    articles_collected_today = sum(1 for s in stories if today_str in (s.first_published or ""))
    
    # Images downloaded - approx based on images available
    images_downloaded = sum(1 for s in stories if s.articles and s.articles[0].get("image_url"))
    
    generated_stories = [s for s in stories if s.status in ["generated", "approved", "queued", "publishing", "published"]]
    gen_success_rate = f"{(len(generated_stories) / max(1, len(stories))) * 100:.1f}%"
    
    published_total = len([s for s in stories if s.status == "published"])
    failed_total = len([s for s in stories if s.status == "failed"])
    pub_success_rate = "N/A"
    if (published_total + failed_total) > 0:
        pub_success_rate = f"{(published_total / (published_total + failed_total)) * 100:.1f}%"
        
    avg_score_num = sum(s.overall_story_score for s in stories) / max(1, len(stories))
    
    # Layout
    a1, a2, a3 = st.columns(3)
    with a1:
        st.metric("Articles Collected Today", articles_collected_today)
        st.metric("Total Stories Clustered", len(stories))
        st.metric("Images Downloaded", images_downloaded)
    with a2:
        st.metric("Generation Success Rate", gen_success_rate)
        st.metric("Publishing Success Rate", pub_success_rate)
        st.metric("Average AI Score", f"{avg_score_num:.1f}/100")
    with a3:
        st.markdown("**Top Categories**")
        cat_counts = {}
        for s in stories:
            cat_counts[s.category] = cat_counts.get(s.category, 0) + 1
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
            st.caption(f"{cat}: {cnt} stories")
            
        st.markdown("**Top News Sources**")
        src_counts = {}
        for s in stories:
            src_counts[s.primary_source] = src_counts.get(s.primary_source, 0) + 1
        for src, cnt in sorted(src_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
            st.caption(f"{src}: {cnt} stories")
