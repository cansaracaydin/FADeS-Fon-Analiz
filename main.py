from core.tefas_fetcher import TefasFetcher
from core.processor import DataProcessor
from core.visualizer import Visualizer
from core.market_fetcher import MarketFetcher # <-- YENİ: Dolar için eklendi
from datetime import datetime, timedelta
import pandas as pd
import os

def main():
    # --- AYARLAR ---
    fon_kodlari = ["TCD", "MAC", "TI3", "IPJ"] 
    benchmark_sembol = "USDTRY=X" # Dolar: USDTRY=X, Altın: GC=F
    gun_sayisi = 90
    
    bugun = datetime.now()
    baslangic = bugun - timedelta(days=gun_sayisi)
    
    str_bugun = bugun.strftime("%Y-%m-%d")
    str_baslangic = baslangic.strftime("%Y-%m-%d")

    print(f"--- FADeS Analiz Sistemi ({str_baslangic} - {str_bugun}) ---")

    # Motorları Başlat
    fetcher = TefasFetcher()      # Fon verisi için (Chrome)
    market_fetcher = MarketFetcher() # Piyasa verisi için (Yahoo) <-- YENİ
    processor = DataProcessor()   # Hesaplamalar
    visualizer = Visualizer()     # Grafik
    
    tum_fonlar = []

    try:
        # 1. FONLARI ÇEK
        # -------------------------------------------------
        print(f"\n📊 FONLAR İŞLENİYOR...")
        for kod in fon_kodlari:
            print(f"> {kod} verisi alınıyor...")
            
            # Browser üzerinden çek
            raw_df = fetcher.fetch_data(kod, str_baslangic, str_bugun)
            
            if raw_df.empty: continue

            # Temizle ve Hesapla
            clean_df = processor.clean_data(raw_df)
            final_df = processor.add_financial_metrics(clean_df)
            
            if final_df.empty:
                print(f"  ⚠️ {kod} verisi işlenemedi.")
                continue
            
            tum_fonlar.append(final_df)
            
            son_getiri = final_df['Cumulative_Return'].iloc[-1] * 100
            print(f"  + {kod} Getiri: %{son_getiri:.2f}")

        # 2. BENCHMARK (DOLAR) VERİSİNİ ÇEK VE EKLE
        # -------------------------------------------------
        print(f"\n🌍 PİYASA VERİSİ (BENCHMARK) EKLENİYOR...")
        bench_df = market_fetcher.fetch_benchmark(benchmark_sembol, str_baslangic, str_bugun)

        if not bench_df.empty:
            # Doları da fon formatına sokuyoruz (Getiri hesabı için)
            bench_df = processor.add_financial_metrics(bench_df)
            
            # Sisteme tanıtalım
            bench_df["FundCode"] = "USD/TRY"
            bench_df["FundName"] = "Dolar Kuru"
            
            tum_fonlar.append(bench_df) # <-- Listeye ekledik!
            
            dolar_getiri = bench_df['Cumulative_Return'].iloc[-1] * 100
            print(f"  + USD/TRY Getiri: %{dolar_getiri:.2f}")
        else:
            print("  ⚠️ Piyasa verisi çekilemedi.")

    finally:
        print("\n🛑 Tarayıcı kapatılıyor...")
        fetcher.close()

    # --- RAPORLAMA ---
    if tum_fonlar:
        full_report = pd.concat(tum_fonlar, ignore_index=True)
        
        # Klasör kontrolü
        if not os.path.exists('reports'): os.makedirs('reports')
        
        # Excel Kaydet
        excel_path = f"reports/Analiz_Raporu_{bugun.strftime('%Y%m%d')}.xlsx"
        full_report.to_excel(excel_path, index=False)
        print(f"\n✅ EXCEL HAZIR: {excel_path}")

        # Grafik Çiz (Artık içinde Dolar da var)
        visualizer.create_performance_chart(full_report)
    else:
        print("\n❌ Hiçbir veri elde edilemedi.")

if __name__ == "__main__":
    main()