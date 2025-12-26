# -*- coding: utf-8 -*-
import streamlit as st

def apply_custom_css():
    """
    Applies professional, dark-mode friendly custom CSS to the Streamlit app.
    """
    st.markdown("""
    <style>
        /* --- GLOBAL VARIABLES --- */
        :root {
            --primary-color: #145f56;
            --secondary-color: #48c9b0;
            --background-dark: #0e1117;
            --sidebar-bg: #1a1c24;
            --text-color: #fafafa;
            --text-muted: #d0d0d0;
            --card-bg: #262730;
            --border-color: #41424C;
            --accent-gold: #bfa15f;
        }

        /* --- GLOBAL TEXT & BACKGROUND --- */
        .main {
            background-color: var(--background-dark);
            color: var(--text-color);
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3 { 
            color: var(--secondary-color) !important; 
            font-weight: 600;
        }
        
        p, label, span {
            color: var(--text-muted);
        }

        /* --- SIDEBAR STYLING --- */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg);
            border-right: 1px solid #333;
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
            color: #ffffff !important;
        }
        
        [data-testid="stSidebar"] .stMarkdown p {
            color: #e0e0e0 !important;
            font-size: 0.95rem;
        }

        /* --- METRIC CARDS --- */
        div[data-testid="stMetric"] {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid var(--accent-gold);
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
        }
        
        div[data-testid="stMetricValue"] { 
            color: #5dade2; 
            font-size: 28px; 
            font-weight: 700; 
        }
        
        div[data-testid="stMetricLabel"] { 
            color: var(--text-muted); 
            font-size: 15px; 
            font-weight: 500;
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] { 
            gap: 8px; 
            margin-bottom: 20px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: var(--card-bg);
            border-radius: 6px;
            color: var(--text-muted);
            border: 1px solid var(--border-color);
            padding: 10px 20px;
            font-weight: 500;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: var(--primary-color) !important;
            color: white !important;
            border-color: var(--primary-color) !important;
            box-shadow: 0 0 10px rgba(20, 95, 86, 0.4);
        }

        /* --- SUBHEADERS & DIVIDERS --- */
        .stDivider {
            border-bottom-color: var(--border-color) !important;
        }

        /* --- DATAFRAME --- */
        [data-testid="stDataFrame"] { 
            border: 1px solid var(--border-color); 
            border-radius: 5px;
        }

        /* --- BUTTONS --- */
        .stButton > button {
            background-color: var(--primary-color);
            color: white;
            font-weight: 600;
            border-radius: 6px;
            border: none;
            padding: 0.5rem 1rem;
            transition: all 0.2s ease;
        }
        
        .stButton > button:hover {
            background-color: #104a43;
            box-shadow: 0 4px 12px rgba(20, 95, 86, 0.3);
        }

        /* --- TOAST --- */
        div[data-testid="stToast"] {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)
