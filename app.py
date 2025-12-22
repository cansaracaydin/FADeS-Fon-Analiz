import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import time
from core.tefas_fetcher import TefasFetcher
from core.processor import DataProcessor

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Fon Analiz Paneli", layout="wide", page_icon="📊")

# Başlık (Sadeleştirildi)
st.title("📊 Fon Analiz ve Takip Paneli")
st.markdown("""
Bu sistem, TEFAS üzerinden güncel verileri çeker ve seçilen fonların saf getiri performansını karşılaştırır.
""")

# --- YAN MENÜ (AYARLAR) ---
st.sidebar.header("⚙️ Analiz Ayarları")

# Kuveyt Türk Fon Listesi
kuveyt_turk_fonlari = [
    "KZL", "KZU", "KUT", "KGM", "KSV", "KLU", "KTV", "KTN", "KTR", 
    "KDL", "KTT", "KPD", "KAV", "KCV", "KTM", "KME", "KDE", "KUD", 
    "KUA", "KPC", "KPU", "KPA", "KTS", "KTJ", "KNJ", "KSR", "KIK"
]

# Popüler Fonlar
populer_fonlar = ["TCD", "MAC", "TI3", "IPJ", "AFT", "YAY"]

# Kullanıcı Seçimi
secilen_fonlar = st.sidebar.multiselect(
    "İncelenecek Fonları Seçin:",
    options=kuveyt_turk_fonlari + populer_fonlar,
    default=["KZL", "KZU", "KUT"] 
)

# Tarih Seçimi
col1, col2 = st.sidebar.columns(2)
baslangic_tarihi = col1.date_input("Başlangıç Tarihi", datetime.now() - timedelta(days=90))
bitis_tarihi = col2.date_input("Bitiş Tarihi", datetime.now())

# Çalıştırma Butonu
if st.sidebar.button("🚀 Verileri Getir ve Analiz Et", type="primary"):
    
    if not secilen_fonlar:
        st.warning("Lütfen listeden en az bir fon seçiniz.")
    else:
        st.info("Veriler TEFAS üzerinden çekiliyor, lütfen bekleyiniz...")
        
        # Görsel Öğeler
        bar = st.progress(0)
        durum_yazisi = st.empty()
        
        # Motorları Başlat
        fetcher = TefasFetcher()
        processor = DataProcessor()
        
        tum_veriler = []
        
        try:
            for i, fon in enumerate(secilen_fonlar):
                durum_yazisi.text(f"⏳ İşleniyor: {fon} ({i+1}/{len(secilen_fonlar)})")
                
                # 1. Çek
                raw_df = fetcher.fetch_data(fon, str(baslangic_tarihi), str(bitis_tarihi))
                
                if not raw_df.empty:
                    # 2. İşle
                    clean_df = processor.clean_data(raw_df)
                    final_df = processor.add_financial_metrics(clean_df)
                    
                    if not final_df.empty:
                        tum_veriler.append(final_df)
                
                # Barı güncelle
                bar.progress((i + 1) / len(secilen_fonlar))
                
            durum_yazisi.text("✅ Analiz tamamlandı! Grafikler oluşturuluyor...")
            time.sleep(0.5)
            durum_yazisi.empty()
            bar.empty()

            # --- SONUÇ EKRANI ---
            if tum_veriler:
                full_df = pd.concat(tum_veriler, ignore_index=True)
                
                # 1. GRAFİK (Daha sade başlık)
                st.subheader("📈 Getiri Performans Grafiği")
                fig = px.line(
                    full_df, 
                    x="Date", 
                    y="Cumulative_Return", 
                    color="FundCode",
                    hover_data=["FundName", "Price"],
                    markers=True
                )
                # Y eksenini % formatına çevir
                fig.layout.yaxis.tickformat = ',.0%' 
                st.plotly_chart(fig, use_container_width=True)
                
                # 2. TABLO
                st.subheader("📋 Detaylı Veri Tablosu")
                st.dataframe(full_df)
                
                # 3. EXCEL İNDİRME (İsim düzeltildi)
                import io
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    full_df.to_excel(writer, index=False, sheet_name='Veriler')
                    
                st.download_button(
                    label="📥 Excel Raporunu İndir",
                    data=buffer.getvalue(),
                    file_name=f"Analiz_Raporu_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.ms-excel"
                )
                
            else:
                st.error("❌ Veri alınamadı. Lütfen tarih aralığını kontrol edin.")

        except Exception as e:
            st.error(f"Hata oluştu: {e}")
        
        finally:
            fetcher.close()

else:
    st.info("👈 Analize başlamak için sol menüden fon seçimi yapın.")