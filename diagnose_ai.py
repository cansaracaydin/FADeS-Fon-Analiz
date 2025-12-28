# -*- coding: utf-8 -*-
"""
AI Model Diagnostic Script
Identifies the root cause of poor R² performance
"""
import pandas as pd
import numpy as np
from core.ai_forecaster import AIForecaster
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

print("=" * 60)
print("AI MODEL DIAGNOSTIC - ROOT CAUSE ANALYSIS")
print("=" * 60)

# 1. Generate Synthetic Data (Avoid TefasFetcher/Selenium)
print("\n[1/7] Generating Synthetic Fund Data...")
np.random.seed(42)
dates = pd.date_range(start=datetime.now() - timedelta(days=365), end=datetime.now(), freq='D')
# Simulate realistic fund price movement
price = 100
prices = [price]
for _ in range(len(dates)-1):
    change = np.random.normal(0.0002, 0.01)  # Small daily drift, 1% volatility
    price = price * (1 + change)
    prices.append(price)

df = pd.DataFrame({
    'Date': dates,
    'Price': prices
})

print(f"✅ Generated {len(df)} rows of synthetic data")

# 2. Data Quality Check
print("\n[2/7] Checking Data Quality...")
print(f"Missing values: {df.isnull().sum().sum()}")
print(f"Duplicates: {df.duplicated().sum()}")
print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
print(f"Price range: {df['Price'].min():.2f} - {df['Price'].max():.2f}")

# Check for outliers
price_std = df['Price'].std()
price_mean = df['Price'].mean()
outliers = df[(df['Price'] < price_mean - 3*price_std) | (df['Price'] > price_mean + 3*price_std)]
print(f"Outliers (3σ): {len(outliers)}")

# 3. Feature Engineering Check
print("\n[3/7] Testing Feature Engineering...")
forecaster = AIForecaster()
feature_df = forecaster.prepare_features(df, lags=5)

if feature_df.empty:
    print("❌ ERROR: Feature engineering failed!")
    exit()

print(f"✅ Features created: {feature_df.shape[1]} columns, {feature_df.shape[0]} rows")
print(f"Features: {list(feature_df.columns)}")

# Check for NaN in features
nan_count = feature_df.isnull().sum().sum()
if nan_count > 0:
    print(f"⚠️ WARNING: {nan_count} NaN values in features!")
    print(feature_df.isnull().sum())

# 4. Data Distribution Check
print("\n[4/7] Checking Data Distributions...")
returns = df['Price'].pct_change().dropna()
print(f"Returns - Mean: {returns.mean():.6f}, Std: {returns.std():.6f}")
print(f"Returns - Skewness: {returns.skew():.3f}, Kurtosis: {returns.kurtosis():.3f}")

# Extreme returns
extreme_up = (returns > 0.05).sum()
extreme_down = (returns < -0.05).sum()
print(f"Extreme returns (>5% or <-5%): Up={extreme_up}, Down={extreme_down}")

# 5. Model Training Test
print("\n[5/7] Testing Model Training...")
predictions, r2_score = forecaster.train_and_predict(df, days_forward=30)

print(f"\n{'='*60}")
print(f"MODEL PERFORMANCE: R² = {r2_score:.3f}")
print(f"{'='*60}")

if r2_score < 0:
    print("\n🔴 CRITICAL ISSUE: Negative R² Score!")
    print("Possible causes:")
    print("  1. Model worse than simple mean baseline")
    print("  2. Overfitting to training data")
    print("  3. Feature leakage or lookahead bias")
    print("  4. Train/test split issue")
    print("  5. Target variable (Return) has wrong sign or scale")

# 6. Manual Validation
print("\n[6/7] Manual Validation Test...")
# Simple baseline: Use last known price
baseline_pred = df['Price'].iloc[-10:].mean()
actual_last = df['Price'].iloc[-1]
baseline_error = abs(baseline_pred - actual_last) / actual_last
print(f"Baseline (mean) prediction error: {baseline_error:.2%}")

# 7. Visual Diagnostic
print("\n[7/7] Creating Diagnostic Plots...")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Price history
axes[0, 0].plot(df['Date'], df['Price'])
axes[0, 0].set_title('Synthetic Fund Price History')
axes[0, 0].set_xlabel('Date')
axes[0, 0].set_ylabel('Price')

# Returns distribution
axes[0, 1].hist(returns, bins=50, edgecolor='black')
axes[0, 1].set_title('Returns Distribution')
axes[0, 1].set_xlabel('Return')
axes[0, 1].set_ylabel('Frequency')

# Predictions vs Actual (if available)
if predictions is not None and not predictions.empty:
    axes[1, 0].plot(df['Date'].iloc[-30:], df['Price'].iloc[-30:], label='Historical')
    axes[1, 0].plot(predictions['Date'], predictions['Predicted_Price'], label='Predicted', linestyle='--')
    axes[1, 0].fill_between(
        predictions['Date'],
        predictions['Lower_Bound'],
        predictions['Upper_Bound'],
        alpha=0.2
    )
    axes[1, 0].set_title('Predictions vs Historical')
    axes[1, 0].legend()

# Feature correlation
if not feature_df.empty:
    corr_matrix = feature_df[['Return', 'RSI_Lag1', 'BB_Percent_Lag1', 'MACD_Lag1']].corr()
    im = axes[1, 1].imshow(corr_matrix, cmap='coolwarm', aspect='auto')
    axes[1, 1].set_xticks(range(len(corr_matrix.columns)))
    axes[1, 1].set_yticks(range(len(corr_matrix.columns)))
    axes[1, 1].set_xticklabels(corr_matrix.columns, rotation=45)
    axes[1, 1].set_yticklabels(corr_matrix.columns)
    axes[1, 1].set_title('Feature Correlation')
    plt.colorbar(im, ax=axes[1, 1])

plt.tight_layout()
plt.savefig('ai_diagnostic.png', dpi=150)
print("✅ Diagnostic plot saved to ai_diagnostic.png")

print("\n" + "="*60)
print("DIAGNOSTIC COMPLETE")
print("="*60)
print("\nRECOMMENDATIONS:")
if r2_score < -10:
    print("  🔴 CRITICAL: Model is completely broken")
    print("     → Check for data leakage or target variable errors")
elif r2_score < 0:
    print("  🟡 WARNING: Model worse than baseline")
    print("     → Try simpler model, check train/test split")
elif r2_score < 0.3:
    print("  🟡 POOR: Model needs improvement")
    print("     → Add more features, tune hyperparameters")
elif r2_score < 0.6:
    print("  🟢 FAIR: Model is acceptable for financial data")
    print("     → Consider ensemble methods")
else:
    print("  🟢 GOOD: Model performs well")
    print("     → Consider production deployment")
