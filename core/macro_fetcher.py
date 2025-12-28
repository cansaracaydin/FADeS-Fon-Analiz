# -*- coding: utf-8 -*-
import pandas as pd
import requests
import urllib3
import yfinance as yf
from datetime import datetime, timedelta

# TCMB EVDS API Key
SABIT_API_KEY = "5bWXZH7oXM"
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MacroFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key if api_key else SABIT_API_KEY

    def fetch_evds_data(self):
        """
        TCMB EVDS Sisteminden Makro Verileri Çeker (Ayrı Ayrı).
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*2)
        
        # Helper: Fetch Single Series
        def get_series(series_code, rename_to, frequency=None):
            try:
                url = (
                    f"https://evds2.tcmb.gov.tr/service/evds/"
                    f"series={series_code}"
                    f"&startDate={start_date.strftime('%d-%m-%Y')}"
                    f"&endDate={end_date.strftime('%d-%m-%Y')}"
                    f"&type=json"
                )
                if frequency: url += f"&frequency={frequency}"
                
                headers = {"key": self.api_key, "User-Agent": "Mozilla/5.0"}
                res = requests.get(url, headers=headers, verify=False, timeout=10)
                data = res.json()
                
                if 'items' not in data: return pd.DataFrame()
                
                df = pd.DataFrame(data['items'])
                df['Date'] = pd.to_datetime(df['Tarih'], format="%d-%m-%Y", errors='coerce')
                
                # Column name cleaning (EVDS returns TP_KTF10 for TP.KTF10)
                api_col = series_code.replace('.', '_')
                if api_col in df.columns:
                     df[rename_to] = pd.to_numeric(df[api_col], errors='coerce')
                
                return df[['Date', rename_to]].dropna().set_index('Date')
            except Exception as e:
                print(f"Error fetching {series_code}: {e}")
                return pd.DataFrame()

        # 1. Faiz (Günlük)
        df_faiz = get_series("TP.KTF10", "Faiz (%)")
        
        # 2. Rezerv (Haftalık - Frequency=3 genelde Cuma'dır ama raw çekmek daha güvenli)
        df_rezerv = get_series("TP.AB.C2", "Rezerv (Milyar $)")
        if not df_rezerv.empty:
            # Milyon -> Milyar
            df_rezerv["Rezerv (Milyar $)"] = df_rezerv["Rezerv (Milyar $)"] / 1000

        # 3. Güven Endeksi (Aylık)
        df_guven = get_series("TP.RKGE.K1", "Güven Endeksi")

        # Merge All
        # Base is daily range
        full_idx = pd.date_range(start_date, end_date, freq='D')
        df_base = pd.DataFrame(index=full_idx)
        
        # Join and Fill
        df_final = df_base.join(df_faiz).join(df_rezerv).join(df_guven)
        
        # Ensure Logic: Add missing columns if fetch failed
        expected_cols = ['Faiz (%)', 'Rezerv (Milyar $)', 'Güven Endeksi']
        for col in expected_cols:
            if col not in df_final.columns:
                df_final[col] = None 
        
        # Forward Fill (Critical for mixing Daily/Weekly/Monthly)
        df_final = df_final.ffill()
        
        # Valid Cols check
        valid_cols = [c for c in expected_cols if c in df_final.columns]
        
        return df_final.reset_index().rename(columns={'index': 'Date'}).dropna(how='all', subset=valid_cols)



    def fetch_global_data(self):
        from core.utils import fetch_symbol_robust
        
        symbols = ['^TNX', 'DX-Y.NYB', '^VIX']
        rename_map = {
            '^TNX': 'ABD 10Y Faiz',
            'DX-Y.NYB': 'Dolar Endeksi (DXY)',
            '^VIX': 'VIX (Korku Endeksi)'
        }
        
        data_dict = {}
        try:
            for sym in symbols:
                df_sym = fetch_symbol_robust(sym, period="2y")
                
                if df_sym.empty:
                    print(f"⚠️ {sym} Makro veri boş (Robust).")
                    continue
                
                col = 'Adj Close' if 'Adj Close' in df_sym.columns else 'Close'
                if col in df_sym.columns:
                     friendly = rename_map.get(sym, sym)
                     data_dict[friendly] = df_sym[col]
            
            if not data_dict:
                return pd.DataFrame()

            combined = pd.DataFrame(data_dict)
            combined = combined.ffill().reset_index()
            
            # Timezone removal
            if 'Date' in combined.columns:
                 combined['Date'] = pd.to_datetime(combined['Date']).dt.tz_localize(None)
            
            return combined

        except Exception as e:
            print(f"Global Data Error: {e}")
            return pd.DataFrame()

    def get_combined_macro_data(self):
        """
        EVDS ve Global verileri birleştirir.
        """
        df_evds = self.fetch_evds_data()
        df_global = self.fetch_global_data()
        
        if df_evds.empty and df_global.empty:
            return pd.DataFrame()
            
        if df_evds.empty: return df_global
        if df_global.empty: return df_evds
        
        # Merge on Date (Nearest matching date)
        # Önce ikisini de günlük frekansa çekelim (resample)
        df_evds = df_evds.set_index('Date').resample('D').ffill()
        df_global = df_global.set_index('Date').resample('D').ffill()
        
        merged = pd.merge(df_evds, df_global, left_index=True, right_index=True, how='inner').reset_index()
        return merged
