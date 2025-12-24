import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import time
from core.tefas_fetcher import TefasFetcher
from core.processor import DataProcessor
from core.market_fetcher import MarketFetcher
from core.inflation_fetcher import InflationFetcher

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="FADeS - Fon Analiz Paneli", layout="wide", page_icon="📈")

# CSS: Görsel İyileştirmeler
st.markdown("""
    <style>
    /* Başlık rengini zorla BEYAZ yap (Koyu modda görünmesi için) */
    h1 { color: white !important; }
    
    /* Metrik değerlerini (Rakamları) mavi yap */
    div[data-testid="stMetricValue"] { font-size: 24px; color: #007bff; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Gelişmiş Fon Analiz ve Simülasyon Paneli")

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Analiz Ayarları")

# 1. MOD SEÇİMİ
st.sidebar.markdown("---")
calisma_modu = st.sidebar.radio(
    "Ne Yapmak İstersiniz?",
    ["📈 Detaylı Analiz", "🆚 TEFAS Karşılaştırma", "💼 Portföy Simülasyonu"]
)

# 2. TARİH SEÇİMİ (ENFLASYON İÇİN YUKARI TAŞINDI)
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Tarih Aralığı")
col_t1, col_t2 = st.sidebar.columns(2)
baslangic_tarihi = col_t1.date_input("Başlangıç", datetime.now() - timedelta(days=365))
bitis_tarihi = col_t2.date_input("Bitiş", datetime.now())

# 3. BENCHMARK SEÇİMİ
benchmark_secimi = st.sidebar.selectbox(
    "Karşılaştırma Ölçütü (Benchmark):",
    ["Yok", "Dolar (USD/TRY)", "Altın (Ons/USD)"]
)

# --- DİNAMİK ENFLASYON YÖNETİMİ (TAM KARNE MODU) ---
st.sidebar.markdown("---")
with st.sidebar.expander("💸 Enflasyon Verileri (TCMB/TÜİK Karnesi)", expanded=False):
    st.caption(f"TCMB formatında tüm göstergeler ({baslangic_tarihi} - {bitis_tarihi})")
    
    evds_api_key = st.text_input("TCMB API Anahtarı (Opsiyonel)", type="password")
    
    col_api, col_manual = st.columns(2)
    
    # 1. API İLE ÇEK
    if evds_api_key:
        if col_api.button("🔄 TCMB'den Çek", key="btn_tcmb_cek"):
            with st.spinner("TCMB'den detaylı veriler alınıyor..."):
                inf_fetcher = InflationFetcher(evds_api_key)
                
                # Fetcher artık 4 farklı hesaplama yapıyor ve NaN temizliyor
                api_data = inf_fetcher.fetch_inflation_data(
                    start_date_obj=baslangic_tarihi,
                    end_date_obj=bitis_tarihi
                )
                
                if not api_data.empty:
                    st.success("Veriler Alındı!")
                    st.session_state['enflasyon_verisi'] = api_data
                else:
                    st.error("Veri alınamadı!")

    # 2. MANUEL ŞABLON OLUŞTURMA
    if col_manual.button("📅 Şablon Oluştur", key="btn_sablon_olustur"):
        dates = pd.date_range(start=baslangic_tarihi, end=bitis_tarihi, freq='MS') 
        template_data = {
            "Tarih": dates, 
            "Aylık Enflasyon": [3.0] * len(dates),
            "Yıllık Enflasyon": [45.0] * len(dates),
            "Yılbaşına Göre": [25.0] * len(dates),
            "12 Aylık Ort. Değ.": [50.0] * len(dates),
            "Oran": [3.0] * len(dates) # Hesaplama için aylık kullanılır
        }
        st.session_state['enflasyon_verisi'] = pd.DataFrame(template_data)
        st.toast("Şablon oluşturuldu.")

    # 3. TABLO GÖSTERİMİ
    if 'enflasyon_verisi' not in st.session_state or st.session_state['enflasyon_verisi'] is None:
        st.session_state['enflasyon_verisi'] = pd.DataFrame(columns=["Tarih", "Oran"])

    inf_df = st.session_state['enflasyon_verisi'].copy()
    
    if not inf_df.empty:
        # Tarih formatı düzenlemesi (Görsel tablo için sadece Tarih)
        if "Tarih" in inf_df.columns:
             inf_df["Tarih"] = pd.to_datetime(inf_df["Tarih"])

        st.write("📊 **Enflasyon Göstergeleri (%)**")
        
        # Formatlı Tablo Gösterimi
        st.dataframe(
            inf_df, 
            hide_index=True,
            column_config={
                "Tarih": st.column_config.DateColumn("Dönem", format="YYYY-MM-DD"),
                "Aylık Enflasyon": st.column_config.NumberColumn("Aylık (MoM)", format="%.2f%%"),
                "Yıllık Enflasyon": st.column_config.NumberColumn("Yıllık (YoY)", format="%.2f%%"),
                "Yılbaşına Göre": st.column_config.NumberColumn("Yılbaşına Göre (YTD)", format="%.2f%%"),
                "12 Aylık Ort. Değ.": st.column_config.NumberColumn("12 Ay Ort.", format="%.2f%%"),
                "Oran": None # Bunu gizle (Hesaplama sütunu)
            }
        )
        
        # Grafik Seçeneği
        gosterim_tipi = st.selectbox(
            "Grafikte Göster:", 
            ["Aylık Enflasyon", "Yıllık Enflasyon", "12 Aylık Ort. Değ."], 
            index=1 # Varsayılan Yıllık
        )
        
        if gosterim_tipi in inf_df.columns:
            st.line_chart(inf_df, x="Tarih", y=gosterim_tipi, color="#FF4B4B")
            
        st.info("ℹ️ Not: Portföy simülasyonunda 'Reel Getiri' hesaplanırken **Aylık Enflasyon** verisi kullanılır.")

# 4. FON LİSTESİ
st.sidebar.markdown("---")
kuveyt_turk_fonlari = [
    "KZL", "KZU", "KUT", "KGM", "KSV", "KLU", "KTV", "KTN", "KTR", 
    "KDL", "KTT", "KPD", "KAV", "KCV", "KTM", "KME", "KDE", "KUD", 
    "KUA", "KPC", "KPU", "KPA", "KTS", "KTJ", "KNJ", "KSR", "KIK",
    "TCD", "MAC", "YAS", "AFT", "IPJ", "PUR", "HBF"
]

secilen_fonlar = st.sidebar.multiselect(
    "Fonları Seçin:",
    options=kuveyt_turk_fonlari, 
    default=["KZL", "KZU", "KUT"] 
)

# --- SİMÜLASYON AYARLARI ---
portfoy_agirliklari = {}
baslangic_sermayesi = 100000
simulasyon_sayisi = 50

if calisma_modu == "💼 Portföy Simülasyonu":
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 Portföy Yapılandırma")
    
    # 1. SERMAYE GİRİŞİ
    baslangic_sermayesi = st.sidebar.number_input(
        "Yatırım Sermayesi (TL)", 
        min_value=1000, 
        max_value=100000000, 
        value=100000, 
        step=1000,
        format="%d", 
        help="Başlangıç bakiyenizi buraya yazabilirsiniz."
    )
    
    # 2. SİMÜLASYON SAYISI
    simulasyon_sayisi = st.sidebar.number_input(
        "Monte Carlo Senaryo Sayısı", 
        min_value=10, max_value=5000, value=50, step=10,
        help="Daha yüksek sayı = Daha hassas tahmin."
    )
    
    st.sidebar.write("### ⚖️ Fon Ağırlıkları (%)")
    
    # 3. AĞIRLIKLAR
    toplam_agirlik = 0
    if secilen_fonlar:
        varsayilan = int(100 / len(secilen_fonlar))
        
        for fon in secilen_fonlar:
            c1, c2 = st.sidebar.columns([3, 1])
            with c1:
                slider_val = st.slider(f"{fon}", 0, 100, varsayilan, key=f"slide_{fon}", label_visibility="collapsed")
            with c2:
                input_val = st.number_input(f"val_{fon}", 0.0, 100.0, float(slider_val), step=0.5, key=f"num_{fon}", label_visibility="collapsed")
            
            st.sidebar.caption(f"**{fon}:** %{input_val}")
            portfoy_agirliklari[fon] = input_val / 100.0
            toplam_agirlik += input_val
        
        if abs(toplam_agirlik - 100) > 0.1:
            st.sidebar.error(f"⚠️ Toplam: %{toplam_agirlik:.1f} (100 olmalı!)")
        else:
            st.sidebar.success("✅ Dağılım Dengeli (%100)")
    else:
        st.sidebar.info("Fon seçiniz.")

# Buton Metni Ayarı
if calisma_modu == "💼 Portföy Simülasyonu":
    buton_metni = "🎰 Simülasyonu Çalıştır"
else:
    buton_metni = "🚀 Analizi Başlat"

# --- SESSION STATE KONTROLÜ ---
if 'analiz_verileri' not in st.session_state:
    st.session_state['analiz_verileri'] = None
if 'varlik_dagilimi' not in st.session_state:
    st.session_state['varlik_dagilimi'] = {} 

# --- VERİ ÇEKME İŞLEMİ ---
if st.sidebar.button(buton_metni, type="primary"):
    
    if not secilen_fonlar:
        st.warning("Lütfen listeden en az bir fon seçiniz.")
    else:
        st.info(f"Mod: {calisma_modu} | Veriler işleniyor... (Lütfen bekleyiniz)")
        durum = st.empty()
        bar = st.progress(0)
        
        fetcher = TefasFetcher()
        processor = DataProcessor()
        market_fetcher = MarketFetcher()
        
        tum_veriler = []
        varlik_dagilimlari = {}

        try:
            # 1. FON VERİLERİNİ ÇEK
            for i, fon in enumerate(secilen_fonlar):
                durum.text(f"⏳ Çekiliyor: {fon} ({i+1}/{len(secilen_fonlar)})...")
                try:
                    # Tarihsel Fiyat Çek
                    raw_df = fetcher.fetch_data(fon, str(baslangic_tarihi), str(bitis_tarihi))
                    if not raw_df.empty:
                        clean_df = processor.clean_data(raw_df)
                        final_df = processor.add_financial_metrics(clean_df)
                        if not final_df.empty:
                            final_df["FundCode"] = fon 
                            final_df["Date"] = pd.to_datetime(final_df["Date"])
                            tum_veriler.append(final_df)
                    
                    # Varlık Dağılımını Çek
                    asset_df = fetcher.fetch_asset_allocation(fon, str(bitis_tarihi))
                    if not asset_df.empty:
                        varlik_dagilimlari[fon] = asset_df

                    time.sleep(0.5) 
                except Exception as e:
                    st.error(f"⚠️ {fon} hatası: {e}")
                bar.progress((i + 1) / len(secilen_fonlar))

            # 2. BENCHMARK EKLE
            if benchmark_secimi != "Yok":
                durum.text(f"🌍 Benchmark ekleniyor: {benchmark_secimi}...")
                sembol = "USDTRY=X" if "Dolar" in benchmark_secimi else "GC=F"
                isim_kisa = "USD/TRY" if "Dolar" in benchmark_secimi else "ALTIN"
                
                bench_df = market_fetcher.fetch_benchmark(sembol, str(baslangic_tarihi), str(bitis_tarihi))
                if not bench_df.empty:
                    bench_df = processor.add_financial_metrics(bench_df)
                    bench_df["FundCode"] = isim_kisa
                    bench_df["FundName"] = f"Piyasa: {benchmark_secimi}"
                    tum_veriler.append(bench_df)

            # --- VERİYİ HAFIZAYA KAYDET ---
            if tum_veriler:
                st.session_state['analiz_verileri'] = tum_veriler
                st.session_state['varlik_dagilimi'] = varlik_dagilimlari 
                st.success("Veriler başarıyla alındı!")
            else:
                st.error("Hiçbir veri alınamadı.")

        except Exception as e:
            st.error(f"Beklenmedik bir hata: {e}")
        finally:
            durum.empty()
            bar.empty()
            fetcher.close()

# --- EKRANA BASMA (Hafızadan Okur) ---
if st.session_state['analiz_verileri']:
    
    ham_veriler = st.session_state['analiz_verileri']
    varlik_dagilimi = st.session_state.get('varlik_dagilimi', {})
    processor = DataProcessor()
    
    ozet_rapor = []
    
    for df in ham_veriler:
        metrics = processor.calculate_risk_metrics(df)
        if metrics:
            metrics["Fon Kodu"] = df.iloc[0]["FundCode"]
            metrics["Fon Adı"] = df.iloc[0]["FundName"]
            ozet_rapor.append(metrics)

    # Simülasyon Hesabı
    tum_veriler_gosterim = ham_veriler.copy()
    
    if calisma_modu == "💼 Portföy Simülasyonu":
        temp_full_df = pd.concat(ham_veriler, ignore_index=True)
        sim_df = processor.calculate_portfolio_simulation(temp_full_df, portfoy_agirliklari, baslangic_sermayesi)
        
        if not sim_df.empty:
            tum_veriler_gosterim.append(sim_df)
            p_metrics = processor.calculate_risk_metrics(sim_df)
            if p_metrics:
                p_metrics["Fon Kodu"] = "PORTFOY"
                p_metrics["Fon Adı"] = "🔴 BENİM PORTFÖYÜM"
                ozet_rapor.append(p_metrics)

    full_df = pd.concat(tum_veriler_gosterim, ignore_index=True)
    ozet_df = pd.DataFrame(ozet_rapor)

    # --- SİMÜLASYON MODU GÖRÜNÜMÜ ---
    if calisma_modu == "💼 Portföy Simülasyonu":
        st.success("✅ Simülasyon Aktif")
        
        portfoy_data = full_df[full_df["FundCode"] == "PORTFOY"]
        if not portfoy_data.empty:
            son_bakiye = portfoy_data.iloc[-1]["Price"]
            kar_zarar = son_bakiye - baslangic_sermayesi
            kar_orani = (kar_zarar / baslangic_sermayesi) * 100
            
            # 1. SKOR KARTLARI (inf Kontrolü Ekli)
            col1, col2, col3 = st.columns(3)
            col1.metric("Başlangıç Sermayesi", f"{baslangic_sermayesi:,.0f} TL")
            
            if np.isinf(son_bakiye) or np.isnan(son_bakiye):
                st.error("⚠️ Veri Hatası: Bakiye hesaplanamadı (Sonsuz veya Tanımsız).")
            else:
                col2.metric("Güncel Bakiye (Son)", f"{son_bakiye:,.0f} TL", f"{kar_orani:.2f}%")
                col3.metric("Net Kar/Zarar", f"{kar_zarar:,.0f} TL")
            
            # --- VaR (RİSK ANALİZİ) ---
            st.markdown("---")
            st.subheader("🛡️ Risk Analizi: Value at Risk (VaR)")
            
            guven_araligi = st.radio("Güven Aralığı Seçiniz:", ["%95 (Standart)", "%99 (Kriz Senaryosu)"], horizontal=True)
            conf_level = 0.99 if "99" in guven_araligi else 0.95
            
            var_sonuc = processor.calculate_value_at_risk(temp_full_df, portfoy_agirliklari, baslangic_sermayesi, conf_level)
            
            if var_sonuc:
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.error(f"⚠️ Maksimum Günlük Kayıp Riski")
                    st.metric(label="VaR Tutarı (Riskteki Para)", value=f"-{var_sonuc['VaR_Amount']:,.2f} TL")
                with c2:
                    st.info(f"ℹ️ **Ne Anlama Geliyor?**\n\nİstatistiksel olarak **{guven_araligi}** ihtimalle, portföyünüzün **yarınki** kaybı bu tutarı geçmeyecektir.")
            
            st.markdown("---")
            
            # 2. GRAFİK (MEVCUT DURUM + REEL GETİRİ)
            st.markdown("### 📈 Portföy Büyüme ve Reel Getiri Analizi")
            
            # Reel Getiri Hesabı (Aylık Enflasyona Göre)
            # Burada 'enflasyon_verisi' içindeki 'Oran' (Aylık Enflasyon) sütunu kullanılır.
            edited_inf_df = st.session_state.get('enflasyon_verisi', pd.DataFrame())
            if not edited_inf_df.empty and 'Oran' in edited_inf_df.columns:
                try:
                    # Enflasyon NaN ise 0 kabul et, yoksa hata veriyor
                    edited_inf_df["Oran"] = edited_inf_df["Oran"].fillna(0)
                    portfoy_data = processor.calculate_real_returns(portfoy_data, edited_inf_df)
                except Exception as e:
                    st.warning(f"Reel getiri hesaplanırken hata oluştu: {e}")
            
            fig_sim = go.Figure()
            
            # Nominal Çizgi
            fig_sim.add_trace(go.Scatter(
                x=portfoy_data["Date"], y=portfoy_data["Cumulative_Return"], 
                name="Nominal Getiri (Görünen)", 
                line=dict(color='red', width=3)
            ))
            
            # Reel Çizgi (Enflasyonun üstünde misin?)
            if 'Real_Return' in portfoy_data.columns:
                fig_sim.add_trace(go.Scatter(
                    x=portfoy_data["Date"], y=portfoy_data["Real_Return"], 
                    name="Reel Getiri (Enflasyon Arındırılmış)", 
                    line=dict(color='blue', width=2, dash='dash'),
                    fill='tonexty' 
                ))
            
            fig_sim.update_layout(title="Nominal vs Reel Getiri (Alım Gücü)", yaxis_tickformat='.1%')
            st.plotly_chart(fig_sim, use_container_width=True)
            
            # --- 3. MARKOWITZ OPTİMİZASYONU ---
            st.markdown("---")
            st.subheader("🧠 Yapay Zeka Optimizasyonu (Markowitz)")
            
            col_opt1, col_opt2 = st.columns([1, 2])
            with col_opt1:
                st.info("2.000 farklı senaryo deneniyor...")
                if st.button("⚡ En İyi Portföyü Bul", type="secondary"):
                    with st.spinner("Hesaplanıyor..."):
                        saf_fonlar = [f for f in secilen_fonlar if f in full_df['FundCode'].unique()]
                        ef_df, best_stats = processor.calculate_efficient_frontier(full_df, saf_fonlar)
                        
                        if not ef_df.empty:
                            st.success("✅ Optimum Dağılım Bulundu!")
                            st.write("### 🏆 Önerilen Dağılım")
                            for fon_kodu, agirlik in best_stats['Weights'].items():
                                st.progress(agirlik)
                                st.write(f"**{fon_kodu}:** %{agirlik*100:.0f}")
                            
                            with col_opt2:
                                fig_ef = px.scatter(
                                    ef_df, x="Volatility", y="Return", color="Sharpe",
                                    title="Etkin Sınır (Efficient Frontier)",
                                    color_continuous_scale="Viridis"
                                )
                                fig_ef.add_scatter(x=[best_stats['Volatility']], y=[best_stats['Return']], mode='markers', marker=dict(color='red', size=20, symbol='star'), name='En İyi Portföy')
                                st.plotly_chart(fig_ef, use_container_width=True)
                        else:
                            st.warning("Yeterli veri yok.")

            # --- 4. MONTE CARLO SİMÜLASYONU ---
            st.markdown("---")
            st.subheader("🎲 Gelecek Tahmini: Monte Carlo Simülasyonu")
            
            mc_col1, mc_col2 = st.columns([1, 3])
            
            with mc_col1:
                st.write(f"Geleceğe yönelik **{simulasyon_sayisi}** farklı senaryo üretilir.")
                gun_sayisi = st.slider("Kaç Gün İleriye Gitmek İstersiniz?", 30, 365, 180)
                
                if st.button("🔮 Geleceği Simüle Et", type="primary"):
                    with st.spinner("Olasılıklar hesaplanıyor..."):
                        mc_df = processor.run_monte_carlo_simulation(
                            temp_full_df, 
                            portfoy_agirliklari, 
                            son_bakiye, 
                            days_forward=gun_sayisi, 
                            num_simulations=simulasyon_sayisi
                        )
                        
                        if not mc_df.empty:
                            with mc_col2:
                                fig_mc = px.line(mc_df, x='Date', y=mc_df.columns[1:], 
                                                 title=f"Gelecek {gun_sayisi} Gün İçin Olası Senaryolar",
                                                 labels={"value": "Portföy Değeri (TL)", "Date": "Tarih"})
                                fig_mc.update_traces(line=dict(width=1), opacity=0.3)
                                fig_mc.update_layout(showlegend=False) 
                                st.plotly_chart(fig_mc, use_container_width=True)
                                
                                # İstatistikler
                                son_gun_degerleri = mc_df.iloc[-1, 1:]
                                ortalama_senaryo = son_gun_degerleri.mean()
                                kotu_senaryo = son_gun_degerleri.quantile(0.10) 
                                iyi_senaryo = son_gun_degerleri.quantile(0.90) 
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Kötü Senaryo (Taban)", f"{kotu_senaryo:,.0f} TL")
                                c2.metric("Beklenen Senaryo (Ort)", f"{ortalama_senaryo:,.0f} TL")
                                c3.metric("İyi Senaryo (Tavan)", f"{iyi_senaryo:,.0f} TL")

    # --- DİĞER MODLAR ---
    else:
        st.subheader("📈 Analiz Sonuçları")
        tab1, tab2, tab3 = st.tabs(["Grafik", "Özet Tablo", "🥧 Varlık Dağılımı"]) 
        
        with tab1:
            fig = px.line(full_df, x="Date", y="Cumulative_Return", color="FundCode")
            fig.layout.yaxis.tickformat = ',.0%'
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            if not ozet_df.empty: st.dataframe(ozet_df)
        
        with tab3:
            if varlik_dagilimi:
                st.info("Bu grafikler fonların en son açıklanan portföy dağılımını gösterir.")
                cols = st.columns(2) 
                
                for i, (fon_kodu, df_asset) in enumerate(varlik_dagilimi.items()):
                    if not df_asset.empty:
                        with cols[i % 2]: 
                            fig_pie = px.pie(
                                df_asset, 
                                values='Oran', 
                                names='Varlık Türü', 
                                title=f"{fon_kodu} - Varlık Dağılımı"
                            )
                            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("Varlık dağılım verisi çekilemedi veya fon seçilmedi.")

    # Excel İndir
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        full_df.to_excel(writer, index=False, sheet_name='Veriler')
        if not ozet_df.empty: ozet_df.to_excel(writer, index=False, sheet_name='Ozet')
    st.download_button("📥 Excel Raporunu İndir", data=buffer.getvalue(), file_name="Analiz.xlsx")