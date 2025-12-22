from core.tefas_fetcher import TefasFetcher
from core.processor import DataProcessor
from core.visualizer import Visualizer
from datetime import datetime, timedelta
import pandas as pd
import os

def main():
    # --- AYARLAR ---
    fon_kodlari = ["TCD", "MAC", "TI3", "IPJ"] 
    gun_sayisi = 90
    
    bugun = datetime.now()
    baslangic = bugun - timedelta(days=gun_sayisi)
    
    str_bugun = bugun.strftime("%Y-%m-%d")
    str_baslangic = baslangic.strftime("%Y-%m-%d")

    print(f"--- FADeS Analiz Sistemi ({str_baslangic} - {str_bugun}) ---")

    # Motorları Başlat
    fetcher = TefasFetcher() # Tarayıcı açılacak
    processor = DataProcessor()
    visualizer = Visualizer()
    
    tum_fonlar = []

    try:
        # --- VERİ İŞLEME DÖNGÜSÜ ---
        for kod in fon_kodlari:
            print(f"> {kod} işleniyor...")
            
            # 1. ÇEK (Browser üzerinden)
            raw_df = fetcher.fetch_data(kod, str_baslangic, str_bugun)
            
            if raw_df.empty: continue

            # 2. TEMİZLE
            clean_df = processor.clean_data(raw_df)
            
            # 3. HESAPLA
            final_df = processor.add_financial_metrics(clean_df)
            
            if final_df.empty:
                print(f"  ⚠️ {kod} verisi işlenemedi.")
                continue
            
            tum_fonlar.append(final_df)
            
            son_getiri = final_df['Cumulative_Return'].iloc[-1] * 100
            print(f"  + Getiri: %{son_getiri:.2f}")

    finally:
        # Hata olsa bile tarayıcıyı kapat
        print("\n🛑 Tarayıcı kapatılıyor...")
        fetcher.close()

    # --- RAPORLAMA ---
    if tum_fonlar:
        full_report = pd.concat(tum_fonlar, ignore_index=True)
        
        if not os.path.exists('reports'): os.makedirs('reports')
        excel_path = f"reports/Analiz_Raporu_{bugun.strftime('%Y%m%d')}.xlsx"
        full_report.to_excel(excel_path, index=False)
        print(f"\n✅ EXCEL HAZIR: {excel_path}")

        visualizer.create_performance_chart(full_report)
    else:
        print("\n❌ Hiçbir veri elde edilemedi.")

if __name__ == "__main__":
    main()