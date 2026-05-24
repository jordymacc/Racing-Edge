DARK_CSS = """
<style>
    .stApp { background-color: #0A0A0F; }
    [data-testid="stSidebar"] {
        background-color: #0D0D14;
        border-right: 1px solid #1E1E2E;
    }
    [data-testid="stSidebar"] .stMarkdown p { color: #888; font-size: 0.85rem; }
    section[data-testid="stSidebar"] > div > div > div > ul li a {
        color: #ccc !important;
        font-size: 0.9rem !important;
    }
    [data-testid="metric-container"] {
        background-color: #12121A;
        border: 1px solid #1E1E2E;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="metric-container"] label {
        color: #666 !important;
        font-size: 0.7rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #00FF88 !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }
    h1 {
        color: #00FF88 !important;
        font-weight: 800 !important;
        font-size: 1.8rem !important;
        border-bottom: 2px solid #00FF8833;
        padding-bottom: 0.4rem;
    }
    h2 { color: #ffffff !important; font-weight: 600 !important; font-size: 1.3rem !important; }
    h3 { color: #cccccc !important; font-weight: 600 !important; font-size: 1.1rem !important; }
    .stButton > button {
        background-color: #00FF88 !important;
        color: #0A0A0F !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
    }
    hr { border-color: #1E1E2E !important; margin: 0.8rem 0 !important; }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #12121A;
        border-radius: 8px;
        padding: 3px;
        gap: 3px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #666 !important;
        border-radius: 6px !important;
        font-size: 0.8rem !important;
        padding: 4px 10px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00FF88 !important;
        color: #0A0A0F !important;
        font-weight: 700 !important;
    }
    [data-testid="stSelectbox"] > div > div {
        background-color: #12121A !important;
        border: 1px solid #1E1E2E !important;
        border-radius: 6px !important;
        color: #fff !important;
    }
    .stSpinner > div { border-top-color: #00FF88 !important; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #0A0A0F; }
    ::-webkit-scrollbar-thumb { background: #1E1E2E; border-radius: 2px; }
    @media (max-width: 768px) {
        .main .block-container { padding: 0.5rem !important; }
        h1 { font-size: 1.3rem !important; }
        h2 { font-size: 1.1rem !important; }
        [data-testid="metric-container"] [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    }
</style>
"""

def inject_css():
    import streamlit as st
    st.markdown(DARK_CSS, unsafe_allow_html=True)

def page_header(title, subtitle=None):
    import streamlit as st
    inject_css()
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f"<p style='color:#666;margin-top:-0.8rem;font-size:0.85rem;'>{subtitle}</p>",
                   unsafe_allow_html=True)
