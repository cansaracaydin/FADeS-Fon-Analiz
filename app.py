import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import time
from core.tefas_fetcher import TefasFetcher
from core.processor import DataProcessor
from core.market_fetcher import MarketFetcher # <-- YENİ EKLENDİ

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Fon Analiz Paneli", layout="wide", page_icon="📈")

st.title("📊 Gelişmiş Fon Analiz Paneli")

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Analiz Ayarları")

# 1. MOD SEÇİMİ
st.sidebar.markdown("---")
calisma_modu = st.sidebar.radio(
    "Ne Yapmak İstersiniz?",
    ["📈 Detaylı Analiz", "🆚 TEFAS Karşılaştırma"]
)

# 2. BENCHMARK SEÇİMİ (YENİ ÖZELLİK ✅)
# Fonlarınızı ne ile kıyaslamak istersiniz?
benchmark_secimi = st.sidebar.selectbox(
    "Karşılaştırma Ölçütü (Benchmark):",
    ["Yok", "Dolar (USD/TRY)", "Altın (Ons/USD)"]
)
st.sidebar.markdown("---")

# 3. FON LİSTESİ
kuveyt_turk_fonlari = [
    "KZL", "KZU", "KUT", "KGM", "KSV", "KLU", "KTV", "KTN", "KTR", 
    "KDL", "KTT", "KPD", "KAV", "KCV", "KTM", "KME", "KDE", "KUD", 
    "KUA", "KPC", "KPU", "KPA", "KTS", "KTJ", "KNJ", "KSR", "KIK"
]

secilen_fonlar = st.sidebar.multiselect(
    "Fonları Seçin:",
    options=kuveyt_turk_fonlari, 
    default=["KZL", "KZU", "KUT"] 
)

col1, col2 = st.sidebar.columns(2)
baslangic_tarihi = col1.date_input("Başlangıç", datetime.now() - timedelta(days=365))
bitis_tarihi = col2.date_input("Bitiş", datetime.now())

# Buton metnini moda göre değiştir
buton_metni = "🚀 Analizi Başlat" if calisma_modu == "📈 Detaylı Analiz" else "🚀 Karşılaştırmayı Başlat"

if st.sidebar.button(buton_metni, type="primary"):
    
    if not secilen_fonlar:
        st.warning("Lütfen listeden en az bir fon seçiniz.")
    else:
        # --- HAZIRLIK ---
        st.info(f"Mod: {calisma_modu} | Veriler çekiliyor... (Lütfen bekleyiniz)")
        bar = st.progress(0)
        durum = st.empty()
        
        fetcher = TefasFetcher()
        processor = DataProcessor()
        market_fetcher = MarketFetcher() # <-- PİYASA VERİSİ İÇİN
        
        tum_veriler = []
        ozet_rapor = [] 
        kiyaslama_rapor = []

        try:
            # 1. ÖNCE FONLARI ÇEK
            for i, fon in enumerate(secilen_fonlar):
                durum.text(f"⏳ İşleniyor: {fon} ({i+1}/{len(secilen_fonlar)})...")
                
                try:
                    raw_df = fetcher.fetch_data(fon, str(baslangic_tarihi), str(bitis_tarihi))
                    
                    if not raw_df.empty:
                        clean_df = processor.clean_data(raw_df)
                        final_df = processor.add_financial_metrics(clean_df)
                        
                        if not final_df.empty:
                            final_df["FundCode"] = fon 
                            final_df["Date"] = pd.to_datetime(final_df["Date"])
                            tum_veriler.append(final_df)

                            # Risk Metrikleri
                            metrics = processor.calculate_risk_metrics(final_df)
                            if metrics:
                                metrics["Fon Kodu"] = fon
                                metrics["Fon Adı"] = final_df.iloc[0]["FundName"]
                                ozet_rapor.append(metrics)
                            
                            # Dönemsel Getiriler
                            period_rets = processor.calculate_period_returns(final_df)
                            if period_rets:
                                period_rets["Fon Kodu"] = fon
                                period_rets["Fon Adı"] = final_df.iloc[0]["FundName"]
                                kiyaslama_rapor.append(period_rets)
                    
                    time.sleep(1.5) # Kısa mola

                except Exception as e:
                    st.error(f"⚠️ {fon} hatası: {e}")
                    continue

                bar.progress((i + 1) / len(secilen_fonlar))

            # 2. BENCHMARK (DOLAR/ALTIN) VERİSİNİ ÇEK VE EKLE (YENİ ✅)
            if benchmark_secimi != "Yok":
                durum.text(f"🌍 Piyasa verisi çekiliyor: {benchmark_secimi}...")
                
                # Yahoo Finance Sembolleri
                sembol = "USDTRY=X" if "Dolar" in benchmark_secimi else "GC=F"
                isim_kisa = "USD/TRY" if "Dolar" in benchmark_secimi else "ALTIN (ONS)"
                
                try:
                    bench_df = market_fetcher.fetch_benchmark(sembol, str(baslangic_tarihi), str(bitis_tarihi))
                    
                    if not bench_df.empty:
                        # Doları da bir fon gibi işliyoruz (Kümülatif getiri hesabı için)
                        bench_df = processor.add_financial_metrics(bench_df)
                        
                        # Sisteme "Sahte Fon" olarak ekliyoruz
                        bench_df["FundCode"] = isim_kisa
                        bench_df["FundName"] = f"Piyasa: {benchmark_secimi}"
                        
                        tum_veriler.append(bench_df) # <-- Listeye ekledik, artık grafikte çıkacak!
                        
                        # Benchmark'ın da karnesini çıkaralım
                        b_metrics = processor.calculate_risk_metrics(bench_df)
                        if b_metrics:
                            b_metrics["Fon Kodu"] = isim_kisa
                            b_metrics["Fon Adı"] = "Piyasa Referansı"
                            ozet_rapor.append(b_metrics)
                            
                        # Benchmark'ın dönemsel getirisini de ekle
                        b_periods = processor.calculate_period_returns(bench_df)
                        if b_periods:
                            b_periods["Fon Kodu"] = isim_kisa
                            b_periods["Fon Adı"] = "Piyasa Referansı"
                            kiyaslama_rapor.append(b_periods)
                            
                except Exception as e:
                    st.warning(f"Benchmark verisi alınamadı: {e}")

            durum.empty()
            bar.empty()

            # --- SONUÇ EKRANI ---
            if tum_veriler:
                full_df = pd.concat(tum_veriler, ignore_index=True)
                full_df = full_df.drop_duplicates(subset=['Date', 'FundCode'])
                
                ozet_df = pd.DataFrame(ozet_rapor)
                kiyaslama_df = pd.DataFrame(kiyaslama_rapor)

                # ==========================================
                # MOD 1: DETAYLI ANALİZ
                # ==========================================
                if calisma_modu == "📈 Detaylı Analiz":
                    st.subheader("📈 Detaylı Fon Analiz Raporu")
                    
                    tab1, tab2, tab3, tab4, tab5 = st.tabs([
                        "📈 Getiri Grafiği", 
                        "🏆 Performans Karnesi", 
                        "🎲 Risk Analizi",
                        "📄 Geçmiş Fiyatlar",
                        "🤝 Korelasyon"
                    ])

                    with tab1:
                        # Benchmark seçildiyse başlığı güncelle
                        title_add = f" (vs {benchmark_secimi})" if benchmark_secimi != "Yok" else ""
                        st.markdown(f"**Kümülatif Getiri Karşılaştırması{title_add}**")
                        
                        fig = px.line(
                            full_df, x="Date", y="Cumulative_Return", color="FundCode",
                            hover_data=["FundName", "Price"], markers=True
                        )
                        fig.layout.yaxis.tickformat = ',.0%' 
                        st.plotly_chart(fig, use_container_width=True)

                    with tab2:
                        if not ozet_df.empty:
                            gosterim_df = ozet_df.set_index("Fon Kodu")[["Toplam Getiri", "Sharpe Oranı", "Yıllık Volatilite (Risk)", "Max Drawdown (En Büyük Kayıp)"]].sort_values("Sharpe Oranı", ascending=False)
                            st.dataframe(gosterim_df.style.format("{:.2%}", subset=["Toplam Getiri", "Yıllık Volatilite (Risk)", "Max Drawdown (En Büyük Kayıp)"]).format("{:.2f}", subset=["Sharpe Oranı"]).background_gradient(cmap="RdYlGn", subset=["Toplam Getiri", "Sharpe Oranı"]), use_container_width=True)

                    with tab3:
                         if not ozet_df.empty:
                            s_data = ozet_df.copy()
                            s_data["Size"] = s_data["Sharpe Oranı"].apply(lambda x: max(x, 0.01))
                            fig_s = px.scatter(s_data, x="Yıllık Volatilite (Risk)", y="Toplam Getiri", color="Fon Kodu", size="Size", hover_name="Fon Adı", text="Fon Kodu")
                            fig_s.layout.xaxis.tickformat, fig_s.layout.yaxis.tickformat = ',.0%', ',.0%'
                            st.plotly_chart(fig_s, use_container_width=True)

                    with tab4:
                        st.dataframe(full_df[["Date", "FundCode", "Price", "Daily_Return"]].sort_values(by=["FundCode", "Date"], ascending=[True, False]).style.format({"Date": lambda t: t.strftime("%d.%m.%Y"), "Price": "{:.4f}", "Daily_Return": "{:.2%}"}), use_container_width=True)
                    
                    with tab5:
                        st.subheader("🔗 Korelasyon Matrisi")
                        if hasattr(processor, 'calculate_correlation_matrix'):
                            corr = processor.calculate_correlation_matrix(full_df)
                            if not corr.empty:
                                fig_c = px.imshow(corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r", origin="lower")
                                st.plotly_chart(fig_c, use_container_width=True)
                            else: st.warning("Veri yetersiz.")

                # ==========================================
                # MOD 2: TEFAS KARŞILAŞTIRMA
                # ==========================================
                else:
                    st.subheader("🆚 Kapsamlı Karşılaştırma")
                    
                    tab1, tab2 = st.tabs(["🏆 Getiri Sıralaması", "📊 Fiyatlar (Pivot)"])
                    
                    with tab1:
                        if not kiyaslama_df.empty:
                            cols = [c for c in ["1 Ay", "3 Ay", "6 Ay", "YTD (Yılbaşı)", "1 Yıl"] if c in kiyaslama_df.columns]
                            col_sel1, _ = st.columns([1, 3])
                            donem = col_sel1.selectbox("Dönem Seçiniz:", cols)
                            
                            chart_df = kiyaslama_df.sort_values(donem, ascending=False)
                            fig_bar = px.bar(chart_df, x="Fon Kodu", y=donem, color="Fon Kodu", title=f"{donem} Getiri Liderleri", text_auto='.1%', hover_data=["Fon Adı"])
                            fig_bar.layout.yaxis.tickformat = ',.0%'
                            st.plotly_chart(fig_bar, use_container_width=True)
                            
                            st.dataframe(kiyaslama_df[["Fon Kodu"]+cols].set_index("Fon Kodu").sort_values(donem, ascending=False).style.format("{:.2%}", na_rep="-").background_gradient(cmap="RdYlGn", axis=0), use_container_width=True)
                    
                    with tab2:
                        try:
                            piv = full_df.pivot_table(index="Date", columns="FundCode", values="Price", aggfunc='mean').sort_index(ascending=False)
                            piv.index = piv.index.strftime('%d.%m.%Y')
                            st.dataframe(piv, use_container_width=True)
                        except: pass

                # EXCEL İNDİRME
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    full_df.to_excel(writer, index=False, sheet_name='Tum Veriler')
                    if not ozet_df.empty: ozet_df.to_excel(writer, index=False, sheet_name='Ozet Karne')
                    if not kiyaslama_df.empty: kiyaslama_df.to_excel(writer, index=False, sheet_name='Kiyaslama')
                
                st.download_button(label="📥 Raporu İndir (Excel)", data=buffer.getvalue(), file_name="FADeS_Analiz.xlsx", mime="application/vnd.ms-excel")

            else:
                st.error("Veri alınamadı.")

        except Exception as e:
            st.error(f"Hata: {e}")
        finally:
            fetcher.close()