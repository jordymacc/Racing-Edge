DARK_CSS = """
<style>
    /* Main background */
    .stApp {
        background-color: #0A0A0F;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #12121A;
        border-right: 1px solid #00FF88;
    }

    /* Sidebar title */
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #00FF88 !important;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: #12121A;
        border: 1px solid #1E1E2E;
        border-radius: 8px;
        padding: 12px;
    }

    [data-testid="metric-container"] label {
        color: #888888 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #00FF88 !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }

    /* Page title */
    h1 { 
        color: #00FF88 !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        border-bottom: 2px solid #00FF88;
        padding-bottom: 0.5rem;
    }

    h2, h3 { 
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    /* Dataframe */
    [data-testid="stDataFrame"] {
        border: 1px solid #1E1E2E;
        border-radius: 8px;
        overflow: hidden;
    }

    /* Buttons */
    .stButton > button {
        background-color: #00FF88 !important;
        color: #0A0A0F !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        background-color: #00CC6A !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.3) !important;
    }

    /* Success/Info/Warning boxes */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        border-left: 4px solid !important;
    }

    /* Divider */
    hr {
        border-color: #1E1E2E !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #12121A;
        border-radius: 8px;
        padding: 4px;
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        color: #888888 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: #00FF88 !important;
        color: #0A0A0F !important;
    }

    /* Select boxes */
    [data-testid="stSelectbox"] > div {
        background-color: #12121A !important;
        border: 1px solid #1E1E2E !important;
        border-radius: 6px !important;
    }

    /* Input fields */
    .stTextInput > div > div {
        background-color: #12121A !important;
        border: 1px solid #1E1E2E !important;
        border-radius: 6px !important;
        color: #E0E0E0 !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0A0A0F; }
    ::-webkit-scrollbar-thumb { 
        background: #00FF88; 
        border-radius: 3px;
    }

    /* ── MOBILE RESPONSIVE ── */
    @media (max-width: 768px) {
        /* Hide Streamlit sidebar toggle on mobile */
        .stApp > header { display: none; }
        
        /* Full width content */
        .main .block-container {
            padding: 0.5rem 0.5rem !important;
            max-width: 100% !important;
        }

        /* Bigger tap targets */
        .stButton > button {
            min-height: 48px !important;
            font-size: 1rem !important;
            width: 100% !important;
        }

        /* Stack metrics vertically */
        [data-testid="column"] {
            min-width: 45% !important;
        }

        /* Smaller headings */
        h1 { font-size: 1.4rem !important; }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 1rem !important; }

        /* Full width dataframes */
        [data-testid="stDataFrame"] {
            width: 100% !important;
        }

        /* Sidebar hidden by default on mobile */
        [data-testid="stSidebar"] {
            min-width: 0 !important;
            width: 0 !important;
        }
    }

    /* HIGH confidence badge */
    .high-conf {
        background-color: rgba(0, 255, 136, 0.15);
        color: #00FF88;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* MEDIUM confidence badge */
    .med-conf {
        background-color: rgba(255, 200, 0, 0.15);
        color: #FFC800;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
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
        st.markdown(f"<p style='color:#888888;margin-top:-1rem;'>{subtitle}</p>", 
                   unsafe_allow_html=True)
