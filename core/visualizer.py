import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os

class Visualizer:
    def __init__(self):
        pass

    def create_performance_chart(self, df):
        """
        Tüm fonların kümülatif getirilerini karşılaştırmalı çizgi grafik yapar.
        Çıktıyı HTML dosyası olarak kaydeder.
        """
        if df.empty:
            print("  [GRAFİK] Veri yok, grafik çizilemedi.")
            return

        # Tarihe göre sıralayalım ki çizgiler düzgün olsun
        df = df.sort_values('Date')

        # Grafik Başlığı ve Ayarları
        fig = px.line(
            df, 
            x="Date", 
            y="Cumulative_Return", 
            color="FundCode",
            title="Fon Performans Karşılaştırması (Kümülatif Getiri)",
            labels={
                "Date": "Tarih",
                "Cumulative_Return": "Getiri Oranı",
                "FundCode": "Fon Kodu"
            },
            template="plotly_dark" # Şık, koyu tema
        )

        # Y eksenini Yüzde (%) formatına çevirelim
        fig.layout.yaxis.tickformat = ',.0%'

        # Mouse ile üzerine gelince detaylı bilgi çıksın
        fig.update_traces(mode="lines", hovertemplate='%{y:.2%}')

        # Klasör kontrolü
        if not os.path.exists('reports'):
            os.makedirs('reports')

        # Kaydet
        output_path = "reports/Performans_Grafigi.html"
        fig.write_html(output_path)
        
        print(f"📈 GRAFİK OLUŞTURULDU: {output_path}")
        print("   (Bu dosyayı tarayıcınızda açabilirsiniz.)")