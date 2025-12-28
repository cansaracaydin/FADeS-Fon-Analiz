
import requests
import os

# Create assets dir
if not os.path.exists("assets"):
    os.makedirs("assets")

# URL with actual characters
url = "https://upload.wikimedia.org/wikipedia/commons/e/e0/Kuveyt_Türk_Logo.png"

try:
    print(f"Downloading from {url}...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    with open("assets/logo.png", "wb") as f:
        f.write(response.content)
    print("✅ Download successful!")
except Exception as e:
    print(f"❌ Error: {e}")
