import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import time
from core.tefas_fetcher import TefasFetcher
from core.processor import DataProcessor

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Fon Analiz Paneli", layout="wide", page_icon="📈")

st.title("📊 Gelişmiş Fon Analiz Paneli")
st.markdown("Getiri, Risk, Sharpe Oranı ve Detaylı Fiyat Listesi")

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Analiz Ayarları")

kuveyt_turk_fonlari = [
    "KZL", "KZU", "KUT", "KGM", "KSV", "KLU", "KTV", "KTN", "KTR", 
    "KDL", "KTT", "KPD", "KAV", "KCV", "KTM", "KME", "KDE", "KUD", 
    "KUA", "KPC", "KPU", "KPA", "KTS", "KTJ", "KNJ", "KSR", "KIK"
]
populer_fonlar = ["TCD", "MAC", "TI3", "IPJ", "AFT", "YAY", "YAS", "NNF", "HKH", "AES"]

secilen_fonlar = st.sidebar.multiselect(
    "İncelenecek Fonları Seçin:",
    options=kuveyt_turk_fonlari + populer_fonlar,
    default=["KZL", "KZU", "TCD"] 
)

col1, col2 = st.sidebar.columns(2)
baslangic_tarihi = col1.date_input("Başlangıç", datetime.now() - timedelta(days=180))
bitis_tarihi = col2.date_input("Bitiş", datetime.now())

if st.sidebar.button("🚀 Analizi Başlat", type="primary"):
    
    if not secilen_fonlar:
        st.warning("Lütfen listeden en az bir fon seçiniz.")
    else:
        # --- HAZIRLIK ---
        st.info("Veriler çekiliyor... (Çok fon seçtiyseniz lütfen sabırlı olun, TEFAS'ı yormamak için yavaş ilerliyoruz)")
        bar = st.progress(0)
        durum = st.empty()
        
        fetcher = TefasFetcher()
        processor = DataProcessor()
        
        tum_veriler = []
        ozet_rapor = [] 

        try:
            for i, fon in enumerate(secilen_fonlar):
                durum.text(f"⏳ İşleniyor: {fon} ({i+1}/{len(secilen_fonlar)})...")
                
                # --- HATA KORUMASI ---
                try:
                    # 1. Veriyi Çek
                    raw_df = fetcher.fetch_data(fon, str(baslangic_tarihi), str(bitis_tarihi))
                    
                    if not raw_df.empty:
                        # 2. İşle
                        clean_df = processor.clean_data(raw_df)
                        final_df = processor.add_financial_metrics(clean_df)
                        
                        if not final_df.empty:
                            final_df["FundCode"] = fon 
                            # Tarihi datetime formatına zorla (Sıralama hatasını önler)
                            final_df["Date"] = pd.to_datetime(final_df["Date"])
                            tum_veriler.append(final_df)

                            # 3. Risk Hesapla
                            metrics = processor.calculate_risk_metrics(final_df)
                            if metrics:
                                metrics["Fon Kodu"] = fon
                                metrics["Fon Adı"] = final_df.iloc[0]["FundName"]
                                ozet_rapor.append(metrics)
                    
                    # ÖNEMLİ: Her fon arasında 2 saniye bekle (Hata almamak için)
                    time.sleep(2.0)

                except Exception as e:
                    st.error(f"⚠️ {fon} verisi alınırken hata: {e}")
                    time.sleep(1) # Hata olsa bile bekle
                    continue

                # İlerleme Çubuğu
                bar.progress((i + 1) / len(secilen_fonlar))

            durum.empty()
            bar.empty()

            # --- SONUÇ EKRANI ---
            if tum_veriler:
                full_df = pd.concat(tum_veriler, ignore_index=True)
                
                # Çift kayıtları temizle
                full_df = full_df.drop_duplicates(subset=['Date', 'FundCode'])
                
                ozet_df = pd.DataFrame(ozet_rapor)

                # 4 SEKME
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📈 Getiri Grafiği", 
                    "🏆 Performans Karnesi", 
                    "🎲 Risk Analizi (Scatter)",
                    "📄 Geçmiş Fiyatlar"
                ])

                # 1. GRAFİK
                with tab1:
                    st.subheader("Kümülatif Getiri Karşılaştırması")
                    fig = px.line(
                        full_df, x="Date", y="Cumulative_Return", color="FundCode",
                        hover_data=["FundName", "Price"], markers=True
                    )
                    fig.layout.yaxis.tickformat = ',.0%' 
                    st.plotly_chart(fig, use_container_width=True)

                # 2. KARNE
                with tab2:
                    st.subheader("📊 Fon Performans ve Risk Karnesi")
                    if not ozet_df.empty:
                        gosterim_df = ozet_df.copy()
                        gosterim_df = gosterim_df.set_index("Fon Kodu")
                        gosterim_df = gosterim_df[["Toplam Getiri", "Sharpe Oranı", "Yıllık Volatilite (Risk)", "Max Drawdown (En Büyük Kayıp)"]]
                        gosterim_df = gosterim_df.sort_values("Sharpe Oranı", ascending=False)
                        
                        st.dataframe(
                            gosterim_df.style.format("{:.2%}", subset=["Toplam Getiri", "Yıllık Volatilite (Risk)", "Max Drawdown (En Büyük Kayıp)"])
                                             .format("{:.2f}", subset=["Sharpe Oranı"])
                                             .background_gradient(cmap="RdYlGn", subset=["Toplam Getiri", "Sharpe Oranı"])
                                             .background_gradient(cmap="RdYlGn_r", subset=["Yıllık Volatilite (Risk)", "Max Drawdown (En Büyük Kayıp)"]),
                            use_container_width=True
                        )

                # 3. SCATTER
                with tab3:
                    st.subheader("Risk vs Getiri Haritası")
                    if not ozet_df.empty:
                        scatter_data = ozet_df.copy()
                        # Negatif Sharpe hatasını önle
                        scatter_data["Grafik_Boyutu"] = scatter_data["Sharpe Oranı"].apply(lambda x: max(x, 0.01))
                        
                        fig_scatter = px.scatter(
                            scatter_data,
                            x="Yıllık Volatilite (Risk)",
                            y="Toplam Getiri",
                            color="Fon Kodu",
                            size="Grafik_Boyutu", 
                            hover_name="Fon Adı",
                            hover_data=["Sharpe Oranı"],
                            text="Fon Kodu"
                        )
                        fig_scatter.update_traces(textposition='top center')
                        fig_scatter.layout.xaxis.tickformat = ',.0%'
                        fig_scatter.layout.yaxis.tickformat = ',.0%'
                        st.plotly_chart(fig_scatter, use_container_width=True)

                # 4. GEÇMİŞ FİYATLAR (DÜZELTİLDİ ✅)
                with tab4:
                    st.subheader("🗓️ Geçmiş Fiyat Listesi")
                    
                    gorunum_tipi = st.radio(
                        "Görünüm:", 
                        ["📂 Fona Göre Grupla", "📊 Yan Yana (Pivot)"], 
                        horizontal=True
                    )
                    
                    if gorunum_tipi == "📂 Fona Göre Grupla":
                        # SIRALAMA MANTIĞI BURADA:
                        # 1. Önce Fon Koduna Göre (A'dan Z'ye)
                        # 2. Sonra Tarihe Göre (En YENİ en üstte)
                        display_df = full_df[["Date", "FundCode", "FundName", "Price", "Daily_Return", "Cumulative_Return"]].copy()
                        
                        # Tarih olduğundan emin ol
                        display_df["Date"] = pd.to_datetime(display_df["Date"])
                        
                        # SIRALAMA KOMUTU:
                        display_df = display_df.sort_values(by=["FundCode", "Date"], ascending=[True, False]).reset_index(drop=True)
                        
                        st.dataframe(
                            display_df.style.format({
                                "Date": lambda t: t.strftime("%d.%m.%Y"), # Gösterirken gün.ay.yıl yap
                                "Price": "{:.4f}",
                                "Daily_Return": "{:.2%}",
                                "Cumulative_Return": "{:.2%}"
                            }),
                            use_container_width=True,
                            height=500
                        )
                    else:
                        # PIVOT GÖRÜNÜM
                        try:
                            pivot_df = full_df.pivot_table(index="Date", columns="FundCode", values="Price", aggfunc='mean')
                            pivot_df = pivot_df.sort_index(ascending=False) # En yeni tarih en üstte
                            
                            # İndeksi tarih formatına çevir
                            pivot_df.index = pivot_df.index.strftime('%d.%m.%Y')
                            
                            st.dataframe(pivot_df, use_container_width=True)
                        except Exception as e:
                            st.warning("Veriler pivot tablo için uygun değil.")

                # EXCEL İNDİRME
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    full_df.to_excel(writer, index=False, sheet_name='Tum Veriler')
                    if not ozet_df.empty:
                        ozet_df.to_excel(writer, index=False, sheet_name='Ozet Karne')
                
                st.download_button(
                    label="📥 Raporu İndir",
                    data=buffer.getvalue(),
                    file_name=f"FADeS_Analiz_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.ms-excel"
                )

            else:
                st.error("Veri alınamadı. İnternet bağlantınızı kontrol edip tekrar deneyin.")

        except Exception as e:
            st.error(f"Uygulama hatası: {e}")
        finally:
            fetcher.close()