import streamlit as st

def apply_custom_styles(page_title="Metrio", page_icon="📊"):
    st.set_page_config(page_title=page_title, page_icon=page_icon, layout="wide")
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            background-color: #0B0E14;
        }
        [data-testid="stSidebar"] * {
            color: #E5E7EB !important;
        }
        .main {
            background-color: #F8F9FA;
        }
        .stMetric {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid #E5E7EB;
        }
        h1, h2, h3 {
            color: #1F2937;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
        }
        .stDivider {
            border-color: #E5E7EB;
        }
        /* Dashboard sidebar styling */
        .sidebar-content {
            padding: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.image("https://img.icons8.com/isometric/100/null/radar.png", width=60)
        st.title("Metrio")
        st.caption("Premium Rakip İstihbarat")
        st.divider()
