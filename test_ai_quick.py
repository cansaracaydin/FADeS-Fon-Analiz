import pandas as pd
import numpy as np
from core.ai_forecaster import AIForecaster
from datetime import datetime, timedelta

# Generate synthetic data
np.random.seed(42)
dates = pd.date_range(start=datetime.now() - timedelta(days=365), end=datetime.now(), freq='D')
price = 100
prices = [price]
for _ in range(len(dates)-1):
    change = np.random.normal(0.0002, 0.01)
    price = price * (1 + change)
    prices.append(price)

df = pd.DataFrame({'Date': dates, 'Price': prices})

# Test model
forecaster = AIForecaster()
predictions, r2_score = forecaster.train_and_predict(df, days_forward=30)

print("\n" + "="*60)
print(f"FINAL R² SCORE: {r2_score:.4f}")
print("="*60)

if r2_score < 0:
    print("❌ Still negative - model worse than baseline")
elif r2_score < 0.3:
    print("🟡 POOR - Model learning but needs more features")
elif r2_score < 0.6:
    print("🟢 FAIR - Acceptable for financial data")
else:
    print("🟢 EXCELLENT - Production ready")

print(f"\nImprovement from -22.6: {((r2_score + 22.6) / 22.6 * 100):.1f}% better")
