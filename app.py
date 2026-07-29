import streamlit as st
import pandas as pd
import sqlite3
import math

st.set_page_config(
    page_title="BriefBot",
    page_icon="📰",
    layout="wide",
)

st.markdown("""
<style>
.block-container{
    padding-top:1.5rem;
    max-width:1400px;
}
</style>
""", unsafe_allow_html=True)

st.title("📰 BriefBot")
st.caption("AI Powered News Dashboard")

# -----------------------
# DATABASE
# -----------------------

@st.cache_data
def load_data():
    conn = sqlite3.connect("briefbot.db")

    df = pd.read_sql_query(
        "SELECT * FROM news",
        conn,
    )

    conn.close()

    return df

df = load_data()
st.write("Rows:", len(df))
st.write("Columns:", list(df.columns))
st.dataframe(df.head())
st.write(df["source"].unique())
st.write(df["importance"].head(10))

# -----------------------
# SIDEBAR
# -----------------------

st.sidebar.title("BriefBot")

if st.sidebar.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

search = st.sidebar.text_input("Search")

category = st.sidebar.selectbox(
    "Category",
    ["All"] + sorted(df.category.unique())
)

source = st.sidebar.multiselect(
    "Sources",
    sorted(df.source.unique()),
    default=sorted(df.source.unique())
)

importance = st.sidebar.slider(
    "Minimum Importance",
    1,
    10,
    1,
)

sort = st.sidebar.selectbox(
    "Sort",
    [
        "Importance",
        "Confidence",
        "Latest"
    ]
)

# -----------------------
# FILTERS
# -----------------------

# -----------------------
# FILTERS
# -----------------------

st.write("Initial:", len(df))

if search:
    df = df[
        df.title.str.contains(search, case=False, na=False)
        |
        df.summary.str.contains(search, case=False, na=False)
    ]
st.write("After search:", len(df))

if category != "All":
    df = df[df.category == category]
st.write("After category:", len(df))

df = df[df.source.isin(source)]
st.write("After source:", len(df))

df = df[df.importance >= importance]
st.write("After importance:", len(df))
# -----------------------
# METRICS
# -----------------------

m1, m2, m3, m4 = st.columns(4)

m1.metric("Articles", len(df))
m2.metric("Sources", df.source.nunique())
m3.metric("Categories", df.category.nunique())
m4.metric(
    "Average Importance",
    f"{df.importance.mean():.1f}/10"
)

st.divider()

# -----------------------
# DOWNLOAD
# -----------------------

st.download_button(
    "⬇ Download CSV",
    df.to_csv(index=False),
    "briefbot.csv",
    "text/csv",
)

st.write(f"### {len(df)} Articles")

# -----------------------
# PAGINATION
# -----------------------

PER_PAGE = 20

pages = max(
    1,
    math.ceil(len(df) / PER_PAGE)
)

page = st.number_input(
    "Page",
    min_value=1,
    max_value=pages,
    value=1,
)

start = (page - 1) * PER_PAGE
end = start + PER_PAGE

df = df.iloc[start:end]

# -----------------------
# ARTICLES
# -----------------------

for _, row in df.iterrows():

    with st.container(border=True):

        st.subheader(row.title)

        c1, c2, c3 = st.columns(3)

        c1.metric("Importance", f"{row.importance}/10")
        c2.metric("Confidence", f"{row.confidence}%")
        c3.metric("Category", row.category)

        st.caption(
            f"🌍 {row.source} • 📅 {row.published}"
        )

        st.write(row.summary)

        st.success(row.keywords)

        if row.url:
            st.link_button(
                "Read Original Article",
                row.url
            )