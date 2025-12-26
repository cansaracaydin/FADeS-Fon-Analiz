# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

# --- CUSTOM MODULES ---
from core.tefas_fetcher import TefasFetcher
from core.processor import DataProcessor
from core.market_fetcher import MarketFetcher
from core.inflation_fetcher import InflationFetcher
from core.ai_forecaster import AIForecaster

# --- NEW UI MODULES ---
from core.style_config import apply_custom_css
import core.views as views

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Kuveyt Türk Portföy Akademisi | Pro Terminal",
    layout="wide",
    page_icon="🦅",
    initial_sidebar_state="expanded"
)

# Apply Professional CSS
apply_custom_css()

# --- HEADER ---
col_logo, col_title = st.columns([0.4, 4.6])
with col_logo:
    st.markdown("## 🦅")
with col_title:
    st.title("Kuveyt Türk Portföy Akademisi")
    st.caption("Finansal Analiz | Simülasyon | Yapay Zeka | Risk Yönetimi Terminali (v5.1 - Pro Refactor)")

# --- INITIALIZATION ---
processor = DataProcessor()
market_fetcher = MarketFetcher()
ai_forecaster = AIForecaster()

# --- SIDEBAR: KONTROL MERKEZİ ---
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    # 1. MOD SEÇİMİ
    calisma_modu = st.radio(
        "Mod Seçiniz:",
        ["📈 Detaylı Analiz & Kıyaslama", "💼 Portföy Simülasyonu", "🤖 Yapay Zeka Tahmini"],
        index=0
    )
    st.divider()
    
    # 2. TARİH SEÇİMİ
    st.subheader("📅 Tarih Aralığı")
    col_t1, col_t2 = st.columns(2)
    start_date = col_t1.date_input("Başlangıç", datetime.now() - timedelta(days=365))
    end_date = col_t2.date_input("Bitiş", datetime.now())
    
    # 3. BENCHMARK
    benchmark = st.selectbox("Benchmark (Kıyas)", ["Yok", "Dolar (USD/TRY)", "Altın (Gram)", "BIST 100", "Enflasyon (TÜFE)"])
    
    st.divider()

    # --- SIDEBAR: Market Summary ---
    st.sidebar.markdown("### 🌍 Piyasa Özeti")
    
    # Fetch Live Data (Cached in Session State to avoid re-fetching on every interaction)
    if 'market_data' not in st.session_state:
        with st.spinner("Piyasa verileri alınıyor..."):
            st.session_state['market_data'] = market_fetcher.fetch_live_data()
    
    m_data = st.session_state.get('market_data', {})
    
    if m_data:
        # Row 1: BIST & Gold
        mc1, mc2 = st.sidebar.columns(2)
        mc1.metric("BIST 100", f"{m_data.get('BIST 100', 0):,.0f}", delta=None)
        mc2.metric("Gram Altın", f"{m_data.get('Gram Altın', 0):.0f} ₺", delta=None)
        
        # Row 2: USD & EUR
        mc3, mc4 = st.sidebar.columns(2)
        mc3.metric("Dolar/TL", f"{m_data.get('Dolar/TL', 0):.2f} ₺", delta=None)
        mc4.metric("Euro/TL", f"{m_data.get('Euro/TL', 0):.2f} ₺", delta=None)
        
    st.sidebar.divider()
    
    # --- ENFLASYON YÖNETİMİ ---
    with st.expander("💸 Enflasyon (TCMB/EVDS)", expanded=False):
        st.info("Reel Getiri Analizi için gereklidir.")
        evds_key_input = st.text_input("EVDS API Anahtarı (Opsiyonel):", type="password")
        
        c_api, c_man = st.columns(2)
        if c_api.button("🔄 API'den Çek"):
            if evds_key_input:
                try:
                    inf_f = InflationFetcher(evds_key_input)
                    api_data = inf_f.fetch_inflation_data(start_date, end_date)
                    if not api_data.empty:
                        st.session_state['inf_data'] = api_data
                        st.success(f"{len(api_data)} ay veri alındı!")
                    else: st.error("Veri boş döndü.")
                except Exception as e: st.error(f"Hata: {e}")
            else: st.warning("Anahtar giriniz.")
            
        if c_man.button("📝 Şablon"):
            dates = pd.date_range(start_date, end_date, freq='MS')
            dummy_inf = pd.DataFrame({
                "Date": dates,
                "Aylık Enflasyon": [3.0]*len(dates),
                "Yıllık Enflasyon": [45.0]*len(dates),
                "Oran": [3.0]*len(dates),
                "Tarih": dates 
            })
            st.session_state['inf_data'] = dummy_inf
            st.success("Varsayılan şablon yüklendi.")
            
        # Display Data if Available
        if 'inf_data' in st.session_state and st.session_state['inf_data'] is not None:
            inf_show = st.session_state['inf_data'].copy()
            st.caption("📥 Çekilen Enflasyon Verisi:")
            
            # Table Logic
            # Table Logic
            if 'Date' in inf_show.columns: 
                inf_show['Date'] = inf_show['Date'].dt.date
            
            # Avoid duplicate 'Tarih' column if it already exists from fetcher
            if 'Tarih' in inf_show.columns:
                inf_show = inf_show.drop(columns=['Tarih'])
            
            # Calculate Trend & Change
            if 'Aylık Enflasyon' in inf_show.columns:
                inf_show['Diff'] = inf_show['Aylık Enflasyon'].diff()
                
                def get_trend_icon(val):
                    if pd.isna(val) or val == 0: return "➖"
                    return "🔺" if val > 0 else "🔻"
                
                inf_show['Trend'] = inf_show['Diff'].apply(get_trend_icon)
                inf_show['Değişim'] = inf_show['Diff'].apply(lambda x: f"{x:+.2f}" if pd.notnull(x) else "-")
            
            # Rename for display
            display_map = {
                'Aylık Enflasyon': 'Aylık %',
                'Yıllık Enflasyon': 'Yıllık %',
                'Yılbaşına Göre': 'YTD %',
                'Date': 'Tarih'
            }
            inf_show = inf_show.rename(columns=display_map)
            
            # Select Final Columns
            target_cols = ['Tarih', 'Aylık %', 'Değişim', 'Trend', 'Yıllık %', 'YTD %']
            final_cols = [c for c in target_cols if c in inf_show.columns]
            
            if final_cols:
                inf_show = inf_show[final_cols]

            st.dataframe(inf_show, use_container_width=True, hide_index=True, height=300)
            
            # Chart
            st.divider()
            st.caption("📉 Enflasyon Trendi")
            
            # User Selection
            inf_mode = st.radio("Veri Türü:", ["Aylık Enflasyon", "Yıllık Enflasyon"], horizontal=True, label_visibility="collapsed")
            
            # Map selection to new column names
            col_map = {
                "Aylık Enflasyon": "Aylık %",
                "Yıllık Enflasyon": "Yıllık %"
            }
            y_col = col_map.get(inf_mode)
            
            if y_col in inf_show.columns and 'Tarih' in inf_show.columns:
                # Use Line Chart for "Trend"
                st.line_chart(inf_show.set_index('Tarih')[y_col], color="#bfa15f" if "Aylık" in inf_mode else "#ef5350")
    
    if 'inf_data' in st.session_state and st.session_state['inf_data'] is not None:
        st.caption("✅ Enflasyon Verisi Aktif")
        
    st.divider()

    # 4. FON SEÇİMİ
    st.subheader("📊 Fon Havuzu")

    # Initialize custom funds in session state
    if 'custom_funds' not in st.session_state:
        st.session_state['custom_funds'] = []

    # Custom Fund Input
    c_add1, c_add2 = st.columns([3, 1])
    with c_add1:
        new_fund = st.text_input("Fon Kodu Ekle (Örn: TTE)", key="new_fund_input", label_visibility="collapsed", placeholder="Fon Kodu (Örn: TTE)").upper()
    with c_add2:
        if st.button("➕", help="Listeye Ekle"):
            if new_fund and len(new_fund) == 3:
                if new_fund not in st.session_state['custom_funds']:
                    st.session_state['custom_funds'].append(new_fund)
                    st.success(f"{new_fund} Eklendi!")
                else:
                    st.warning("Zaten listede.")
            else:
                st.error("3 Harfli Kod Girin")

    kt_funds = [
        "KZL", "KZU", "KUT", "KGM", "KSV", "KLU", "KTV", "KTN", "KTR", 
        "KDL", "KTT", "KPD", "KAV", "KCV", "KTM", "KME", "KDE", "KUD", 
        "KUA", "KPC", "KPU", "KPA", "KTS", "KTJ", "KNJ", "KSR", "KIK"
    ]
    popular_funds = ["MAC", "YAS", "AFT", "TCD", "NNF", "TI2", "IPB", "GMR"]
    
    # Combine User Custom Funds with Default Lists
    all_funds = list(set(kt_funds + popular_funds + st.session_state['custom_funds']))
    all_funds.sort()
    
    # Pinned funds at top
    kt_priority = [f for f in all_funds if f in kt_funds]
    others = [f for f in all_funds if f not in kt_funds]
    final_list = kt_priority + others 
    
    selected_funds = st.multiselect("Fonları Seçin:", final_list, default=["KUT", "KPC", "KCV"])
    
    # 5. SİMÜLASYON AYARLARI
    sim_weights = {}
    budget = 100000
    
    with st.expander("💰 Portföy Ayarları", expanded=True):
        budget = st.number_input("Bütçe (TL)", value=100000, step=1000)
        
        st.write("Fon Ağırlıkları (%)")
        total_w = 0
        if selected_funds:
            # Default equal weight if not set
            eq = 100 // len(selected_funds)
            
            # Callback functions
            def update_slider_cb(s_k, n_k):
                st.session_state[n_k] = st.session_state[s_k]
                
            def update_num_cb(s_k, n_k):
                st.session_state[s_k] = st.session_state[n_k]

            for f in selected_funds:
                slider_key = f"slider_{f}"
                num_key = f"num_{f}"
                
                # Initialize Session State if not Present
                if slider_key not in st.session_state: st.session_state[slider_key] = eq
                if num_key not in st.session_state: st.session_state[num_key] = eq
                
                c_slide, c_num = st.columns([3, 1])
                
                # SLIDER
                with c_slide:
                    st.slider(
                        label=f"{f}",
                        min_value=0, max_value=100,
                        key=slider_key,
                        on_change=update_slider_cb,
                        args=(slider_key, num_key) 
                    )
                
                # NUMBER INPUT
                with c_num:
                    st.number_input(
                        label="%",
                        min_value=0, max_value=100,
                        key=num_key,
                        step=1,
                        label_visibility="collapsed",
                        on_change=update_num_cb,
                        args=(slider_key, num_key)
                    )
                
                # Use value from one of them (they are synced)
                current_val = st.session_state[slider_key]
                sim_weights[f] = current_val / 100
                total_w += current_val
            
            if total_w != 100: st.error(f"Toplam: %{total_w} (Hedef: %100)")
            else: st.success("Dağılım Tamam")
            
    # ACTION BUTTON
    btn_label = "🎰 Simülasyonu Başlat" if calisma_modu == "💼 Portföy Simülasyonu" else "🚀 Analizi Çalıştır"
    start_btn = st.button(btn_label, type="primary", use_container_width=True)

# --- DATA FETCHING & STATE MANAGEMENT ---
if 'main_df' not in st.session_state: st.session_state.main_df = None
if 'assets_map' not in st.session_state: st.session_state.assets_map = {}

if start_btn:
    if not selected_funds:
        st.warning("Lütfen fon seçiniz.")
    else:
        with st.status("Veriler Toplanıyor...", expanded=True) as status:
            tf = TefasFetcher()
            raw_data = []
            asset_allocs = {}
            
            # 1. FUNDS
            total_items = len(selected_funds)
            for i, f in enumerate(selected_funds):
                status.write(f"📥 {f} verisi çekiliyor...")
                try:
                    # Price
                    df = tf.fetch_data(f, str(start_date), str(end_date))
                    if not df.empty:
                        clean = processor.clean_data(df)
                        clean = processor.add_financial_metrics(clean)
                        clean['FundCode'] = f
                        raw_data.append(clean)
                    
                except Exception as e:
                    st.toast(f"{f} Hatası: {str(e)}")
                    
            tf.close()
            
            # 2. BENCHMARK
            if benchmark != "Yok" and benchmark != "Enflasyon (TÜFE)":
                status.write(f"📥 Benchmark ({benchmark}) ekleniyor...")
                sym = "USDTRY=X" if "Dolar" in benchmark else "GC=F" if "Altın" in benchmark else "XU100.IS"
                b_df = market_fetcher.fetch_benchmark(sym, str(start_date), str(end_date))
                
                if not b_df.empty:
                    b_df = processor.add_financial_metrics(b_df)
                    b_df['FundCode'] = benchmark.split(" ")[0]
                    raw_data.append(b_df)
                    st.toast(f"✅ {benchmark} verisi başarıyla eklendi.")
                else:
                    st.error(f"⚠️ {benchmark} verisi çekilemedi! (Yahoo Finance erişim sorunu veya sembol hatası)")
                    st.toast(f"❌ {benchmark} çekilemedi.")
                    
            if raw_data:
                st.session_state.main_df = pd.concat(raw_data, ignore_index=True)
                # st.session_state.assets_map -> Removed as per user request
                status.update(label="✅ Veri toplama tamamlandı!", state="complete", expanded=False)
            else:
                status.update(label="❌ Veri çekilemedi!", state="error")

# --- MAIN RENDER LOGIC ---
df = st.session_state.main_df
# assets = st.session_state.assets_map -> Removed
inf_df = st.session_state.get('inf_data', pd.DataFrame())

if df is not None and not df.empty:
    st.markdown("---")
    
    # Route to Views
    if calisma_modu == "📈 Detaylı Analiz & Kıyaslama":
        views.render_analysis_view(df, selected_funds, inf_df, benchmark)
        
    elif calisma_modu == "💼 Portföy Simülasyonu":
        views.render_simulation_view(df, selected_funds, sim_weights, budget, processor)
        
    elif calisma_modu == "🤖 Yapay Zeka Tahmini":
        views.render_ai_view(df, ai_forecaster)
        
else:
    # Empty State
    st.info("👈 Analize başlamak için sol menüden fonları seçip 'Analizi Çalıştır' butonuna basınız.")
    
    # Welcome / Intro graphics could go here
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 50px;'>
        <h3>🦅 Hoş Geldiniz</h3>
        <p>Kuveyt Türk Portföy Akademisi terminali ile profesyonel fon analizi yapın.</p>
    </div>
    """, unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("---")
st.markdown("<center style='color: #666;'>Kuveyt Türk Portföy Akademisi - 2025 | Developed with ❤️ and Python</center>", unsafe_allow_html=True)