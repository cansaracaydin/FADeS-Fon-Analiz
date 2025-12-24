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

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="FADeS - Fon Analiz Paneli", layout="wide", page_icon="📈")

st.title("📊 Gelişmiş Fon Analiz ve Simülasyon Paneli")

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Analiz Ayarları")

# 1. MOD SEÇİMİ
st.sidebar.markdown("---")
calisma_modu = st.sidebar.radio(
    "Ne Yapmak İstersiniz?",
    ["📈 Detaylı Analiz", "🆚 TEFAS Karşılaştırma", "💼 Portföy Simülasyonu"]
)

# 2. BENCHMARK SEÇİMİ
benchmark_secimi = st.sidebar.selectbox(
    "Karşılaştırma Ölçütü (Benchmark):",
    ["Yok", "Dolar (USD/TRY)", "Altın (Ons/USD)"]
)
st.sidebar.markdown("---")

# 3. FON LİSTESİ
kuveyt_turk_fonlari = [
    "KZL", "KZU", "KUT", "KGM", "KSV", "KLU", "KTV", "KTN", "KTR", 
    "KDL", "KTT", "KPD", "KAV", "KCV", "KTM", "KME", "KDE", "KUD", 
    "KUA", "KPC", "KPU", "KPA", "KTS", "KTJ", "KNJ", "KSR", "KIK",
    "TCD", "MAC", "YAS", "AFT", "IPJ"
]

secilen_fonlar = st.sidebar.multiselect(
    "Fonları Seçin:",
    options=kuveyt_turk_fonlari, 
    default=["KZL", "KZU", "KUT"] 
)

# --- SİMÜLASYON AYARLARI ---
portfoy_agirliklari = {}
baslangic_sermayesi = 100000

if calisma_modu == "💼 Portföy Simülasyonu":
    st.sidebar.markdown("---")
    st.sidebar.subheader("💰 Simülasyon Ayarları")
    
    # Sermaye Girişi
    baslangic_sermayesi = st.sidebar.number_input("Başlangıç Sermayesi (TL)", value=100000, step=1000, format="%d")
    
    st.sidebar.write("### Fon Ağırlıkları (%)")
    
    # Seçilen her fon için slider oluştur
    toplam_agirlik = 0
    if secilen_fonlar:
        varsayilan_agirlik = int(100 / len(secilen_fonlar))
        
        for fon in secilen_fonlar:
            val = st.sidebar.slider(f"{fon} Ağırlığı", 0, 100, varsayilan_agirlik, key=f"slider_{fon}")
            portfoy_agirliklari[fon] = val / 100.0
            toplam_agirlik += val
        
        if toplam_agirlik != 100:
            st.sidebar.warning(f"⚠️ Toplam: %{toplam_agirlik} (100 olmalı!)")
        else:
            st.sidebar.success("✅ Toplam: %100")
    else:
        st.sidebar.info("Lütfen önce yukarıdan fon seçiniz.")

st.sidebar.markdown("---")

# Tarih Seçimi
col1, col2 = st.sidebar.columns(2)
baslangic_tarihi = col1.date_input("Başlangıç", datetime.now() - timedelta(days=365))
bitis_tarihi = col2.date_input("Bitiş", datetime.now())

# Buton Metni Ayarı
if calisma_modu == "💼 Portföy Simülasyonu":
    buton_metni = "🎰 Simülasyonu Çalıştır"
else:
    buton_metni = "🚀 Analizi Başlat"

# --- SESSION STATE (HAFIZA) KONTROLÜ ---
if 'analiz_verileri' not in st.session_state:
    st.session_state['analiz_verileri'] = None
if 'varlik_dagilimi' not in st.session_state:
    st.session_state['varlik_dagilimi'] = {} # Yeni: Varlık dağılımını sakla

# --- VERİ ÇEKME İŞLEMİ (Sadece butona basınca çalışır) ---
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
                    
                    # --- YENİ: VARLIK DAĞILIMINI ÇEK (Sadece son tarih için) ---
                    # Bitiş tarihine en yakın veriyi almak için bitiş tarihini gönderiyoruz
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
                st.session_state['varlik_dagilimi'] = varlik_dagilimlari # Kaydet
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
            
            # 1. SKOR KARTLARI
            col1, col2, col3 = st.columns(3)
            col1.metric("Başlangıç Sermayesi", f"{baslangic_sermayesi:,.0f} TL")
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
            
            # 2. GRAFİK (MEVCUT DURUM)
            st.markdown("### 📈 Portföy Büyüme Grafiği (Geçmiş)")
            fig_sim = px.line(full_df, x="Date", y="Cumulative_Return", color="FundCode",
                              title="Portföy vs Diğer Fonlar",
                              color_discrete_map={"PORTFOY": "red", "USD/TRY": "green"})
            fig_sim.layout.yaxis.tickformat = ',.0%'
            fig_sim.update_traces(patch={"line": {"width": 4}}, selector={"legendgroup": "PORTFOY"})
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

            # --- 4. YENİ ÖZELLİK: MONTE CARLO SİMÜLASYONU ---
            st.markdown("---")
            st.subheader("🎲 Gelecek Tahmini: Monte Carlo Simülasyonu")
            
            mc_col1, mc_col2 = st.columns([1, 3])
            
            with mc_col1:
                st.write("Geleceğe yönelik 50 farklı senaryo üretilir.")
                gun_sayisi = st.slider("Kaç Gün İleriye Gitmek İstersiniz?", 30, 365, 180)
                
                if st.button("🔮 Geleceği Simüle Et", type="primary"):
                    with st.spinner("Olasılıklar hesaplanıyor..."):
                        # Sadece fonları gönder (Benchmark vs karışmasın)
                        mc_df = processor.run_monte_carlo_simulation(temp_full_df, portfoy_agirliklari, son_bakiye, days_forward=gun_sayisi)
                        
                        if not mc_df.empty:
                            # Grafiği Çiz (Spagetti Grafik)
                            with mc_col2:
                                fig_mc = px.line(mc_df, x='Date', y=mc_df.columns[1:], 
                                                 title=f"Gelecek {gun_sayisi} Gün İçin Olası Senaryolar",
                                                 labels={"value": "Portföy Değeri (TL)", "Date": "Tarih"})
                                
                                # Çizgileri biraz şeffaf yapalım ki yoğunluk belli olsun
                                fig_mc.update_traces(line=dict(width=1), opacity=0.3)
                                fig_mc.update_layout(showlegend=False) # Efsaneyi gizle (50 tane isim olmasın)
                                
                                st.plotly_chart(fig_mc, use_container_width=True)
                                
                                # İstatistikler
                                son_gun_degerleri = mc_df.iloc[-1, 1:]
                                ortalama_senaryo = son_gun_degerleri.mean()
                                kotu_senaryo = son_gun_degerleri.quantile(0.10) # En kötü %10
                                iyi_senaryo = son_gun_degerleri.quantile(0.90)  # En iyi %10
                                
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Kötü Senaryo (Taban)", f"{kotu_senaryo:,.0f} TL")
                                c2.metric("Beklenen Senaryo (Ort)", f"{ortalama_senaryo:,.0f} TL")
                                c3.metric("İyi Senaryo (Tavan)", f"{iyi_senaryo:,.0f} TL")

    # --- DİĞER MODLAR ---
    else:
        st.subheader("📈 Analiz Sonuçları")
        tab1, tab2, tab3 = st.tabs(["Grafik", "Özet Tablo", "🥧 Varlık Dağılımı"]) # Yeni Tab
        
        with tab1:
            fig = px.line(full_df, x="Date", y="Cumulative_Return", color="FundCode")
            fig.layout.yaxis.tickformat = ',.0%'
            st.plotly_chart(fig, use_container_width=True)
        with tab2:
            if not ozet_df.empty: st.dataframe(ozet_df)
        
        # --- YENİ TAB: VARLIK DAĞILIMI ---
        with tab3:
            if varlik_dagilimi:
                st.info("Bu grafikler fonların en son açıklanan portföy dağılımını gösterir.")
                cols = st.columns(2) # Yan yana 2 pasta grafik göster
                
                for i, (fon_kodu, df_asset) in enumerate(varlik_dagilimi.items()):
                    if not df_asset.empty:
                        with cols[i % 2]: # Sırayla sol/sağ kolona yerleştir
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