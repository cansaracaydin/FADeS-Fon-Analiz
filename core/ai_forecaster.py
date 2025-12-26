# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import RandomizedSearchCV
from sklearn.preprocessing import MinMaxScaler, PolynomialFeatures
from datetime import timedelta

class AIForecaster:
    def __init__(self):
        pass

    def calculate_technical_indicators(self, df):
        """
        Gelişmiş Teknik İndikatörler
        """
        data = df.copy()
        
        # RSI
        delta = data['Price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        sma20 = data['Price'].rolling(window=20).mean()
        std20 = data['Price'].rolling(window=20).std()
        data['BB_Upper'] = sma20 + (2 * std20)
        data['BB_Lower'] = sma20 - (2 * std20)
        data['BB_Percent'] = (data['Price'] - data['BB_Lower']) / (data['BB_Upper'] - data['BB_Lower'])
        
        # MACD
        ema12 = data['Price'].ewm(span=12, adjust=False).mean()
        ema26 = data['Price'].ewm(span=26, adjust=False).mean()
        data['MACD'] = ema12 - ema26
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        
        # ATR Proxy
        data['Volatility_ATR_Proxy'] = data['Price'].rolling(window=14).std()

        return data

    def prepare_features(self, df, lags=5):
        if df.empty or 'Price' not in df.columns:
            return pd.DataFrame()
            
        data = df[['Date', 'Price']].copy()
        data = data.sort_values('Date')
        
        # --- 1. LOG RETURN (Daha Normal Dağılım İçin) ---
        # Logaritmik Getiri: ln(P_t / P_{t-1})
        data['Return'] = np.log(data['Price'] / data['Price'].shift(1))
        
        data = self.calculate_technical_indicators(data)
        
        # --- 2. Lags ---
        cols_to_shift = ['Return', 'RSI', 'BB_Percent', 'MACD', 'MACD_Signal', 'Volatility_ATR_Proxy']
        for col in cols_to_shift:
            for i in range(1, lags + 1):
                if col == 'Return':
                    data[f'Return_Lag{i}'] = data['Return'].shift(i)
                else:
                    if i == 1: 
                        data[f'{col}_Lag1'] = data[col].shift(1)

        data = data.dropna()
        return data

    def train_and_predict(self, df, days_forward=30):
        if df.empty or len(df) < 90: return None, 0

        # Feature Prep
        lags = 5
        model_data = self.prepare_features(df, lags=lags)
        if model_data.empty: return None, 0

        features = [f'Return_Lag{i}' for i in range(1, lags + 1)] + \
                   ['RSI_Lag1', 'BB_Percent_Lag1', 'MACD_Lag1', 'MACD_Signal_Lag1', 'Volatility_ATR_Proxy_Lag1']
        
        X = model_data[features]
        y = model_data['Return']

        # Train-Test Split
        split = int(len(X) * 0.9)
        X_train, y_train = X.iloc[:split], y.iloc[:split]
        X_test, y_test = X.iloc[split:], y.iloc[split:]
        
        if len(X_train) < 10: return None, 0

        # --- OUTLIER REMOVAL (Hampel Filter / Z-Score) ---
        # Sadece Eğitim Setinde aykırı değerleri (black swan) temizle
        mean_y = y_train.mean()
        std_y = y_train.std()
        # 3 Standart sapma dışındakileri at
        mask = (np.abs(y_train - mean_y) <= 3 * std_y)
        X_train = X_train[mask]
        y_train = y_train[mask]

        # --- POLYNOMIAL FEATURES (INTERACTIONS) ---
        # İndikatörlerin birbiriyle etkileşimini (Volatilite Yüksek VE RSI Düşük gibi) yakala
        poly = PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)
        X_train_poly = poly.fit_transform(X_train)
        X_test_poly = poly.transform(X_test)
        
        # Scaling
        scaler_X = MinMaxScaler()
        X_train_scaled = scaler_X.fit_transform(X_train_poly)
        X_test_scaled = scaler_X.transform(X_test_poly)
        
        # --- EXPANDED HYPERPARAMETER TUNING ---
        param_dist = {
            'n_estimators': [100, 200, 300, 500],
            'learning_rate': [0.01, 0.03, 0.05, 0.1],
            'max_depth': [3, 4, 5, 6],
            'subsample': [0.7, 0.8, 0.9, 1.0],
            'min_samples_leaf': [1, 2, 4]
        }
        
        gbm = GradientBoostingRegressor(random_state=42)
        random_search = RandomizedSearchCV(gbm, param_distributions=param_dist, n_iter=15, cv=3, n_jobs=-1, random_state=42)
        
        if len(X_train) > 1000:
            sample_X = X_train_scaled[-1000:]
            sample_y = y_train[-1000:]
            random_search.fit(sample_X, sample_y)
        else:
            random_search.fit(X_train_scaled, y_train)
            
        best_model = random_search.best_estimator_
        
        # Score
        best_model.fit(X_train_scaled, y_train)
        r2_score = best_model.score(X_test_scaled, y_test)
        
        preds_test = best_model.predict(X_test_scaled)
        std_error = (y_test - preds_test).std()

        # RECURSIVE FORECAST
        future_predictions = []
        sim_df = df.iloc[-150:].copy() 
        current_price = df['Price'].iloc[-1]
        
        cum_std = 0
        
        for i in range(days_forward):
            current_feats_df = self.prepare_features(sim_df, lags=lags)
            if current_feats_df.empty: break
                
            last_row_vals = current_feats_df.iloc[-1][features].values.reshape(1, -1)
            # Apply Poly -> Apply Scaler -> Predict
            last_row_poly = poly.transform(last_row_vals)
            last_row_scaled = scaler_X.transform(last_row_poly)
            
            # Predict Log Return
            pred_log_return = best_model.predict(last_row_scaled)[0]
            
            # Convert back to Price: P_new = P_old * exp(log_ret)
            # Log Return dönüşümü: exp(r) - 1 değil, direkt exp(r) çarpımıdır.
            # ln(P_t/P_{t-1}) = r  => P_t = P_{t-1} * e^r
            new_price = current_price * np.exp(pred_log_return)
            
            new_date = df['Date'].max() + timedelta(days=i+1)
            
            cum_std += std_error
            # Log return hatasını fiyata yansıtmak yaklaşık olarak:
            # P_up = P * exp(r + 1.96*sigma)
            lower_bound = new_price * np.exp(-1.96 * cum_std)
            upper_bound = new_price * np.exp(1.96 * cum_std)

            future_predictions.append({
                'Date': new_date,
                'Predicted_Price': new_price,
                'Lower_Bound': lower_bound,
                'Upper_Bound': upper_bound
            })
            
            new_row = pd.DataFrame({'Date': [new_date], 'Price': [new_price]})
            sim_df = pd.concat([sim_df, new_row], ignore_index=True)
            current_price = new_price 
            
        return pd.DataFrame(future_predictions), r2_score
