# -*- coding: utf-8 -*-
from core.inflation_fetcher import InflationFetcher

# Sınıfı çağır (Anahtar zaten dosyanın içinde gömülü)
fetcher = InflationFetcher() 

print("--- TEST BAŞLIYOR ---")
veri = fetcher.fetch_inflation_data()

if not veri.empty:
    print("\n🎉 SONUÇ BAŞARILI! İşte ilk 5 satır:")
    print(veri.head())
else:
    print("\n💀 TEST BAŞARISIZ OLDU.")