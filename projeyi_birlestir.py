import os

# Hangi uzantıları alalım? (Kod dosyaları)
UZANTILAR = [".py", ".md", ".txt"]

# Hangi klasörleri/dosyaları görmezden gelelim? (Gereksizler)
HARIC_TUT = ["venv", "env", ".git", "__pycache__", ".idea", ".vscode", "projeyi_birlestir.py", "requirements.txt"]

def masaustu_yolu_bul():
    """Kullanıcının Masaüstü yolunu bulur (OneDrive dahil)"""
    home = os.path.expanduser("~")
    
    # Olası masaüstü yolları
    paths = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "OneDrive", "Desktop"),
        os.path.join(home, "Masaüstü"),
        os.path.join(home, "OneDrive", "Masaüstü")
    ]
    
    for p in paths:
        if os.path.exists(p):
            return p
    return home # Bulamazsa ana kullanıcı klasörüne atar

def proje_birlestir():
    # Dosyayı Masaüstüne kaydet
    kayit_yeri = masaustu_yolu_bul()
    cikis_dosyasi = os.path.join(kayit_yeri, "FADES_TUM_KODLAR.txt")
    
    print(f"📂 Hedef Klasör: {kayit_yeri}")

    with open(cikis_dosyasi, "w", encoding="utf-8") as f_out:
        # Başlık Bilgisi
        f_out.write(f"PROJE: FADeS (Fon Analiz Sistemi)\n")
        f_out.write(f"TARIH: {os.path.basename(os.getcwd())}\n")
        f_out.write("="*60 + "\n\n")

        # Klasörleri gez (Proje klasörünün içindekileri al)
        for kok_dizin, klasorler, dosyalar in os.walk("."):
            # Gereksiz klasörleri atla
            klasorler[:] = [d for d in klasorler if d not in HARIC_TUT]
            
            for dosya in dosyalar:
                # Dosya uzantısı uygun mu?
                if any(dosya.endswith(ext) for ext in UZANTILAR) and dosya not in HARIC_TUT:
                    dosya_yolu = os.path.join(kok_dizin, dosya)
                    
                    # Başlık ekle (Claude dosya ayrımını anlasın diye)
                    f_out.write(f"\n{'='*50}\n")
                    f_out.write(f"DOSYA ADI: {dosya_yolu}\n")
                    f_out.write(f"{'='*50}\n\n")
                    
                    # İçeriği oku ve yaz
                    try:
                        with open(dosya_yolu, "r", encoding="utf-8") as f_in:
                            f_out.write(f_in.read())
                            f_out.write("\n")
                    except Exception as e:
                        f_out.write(f"--- Okuma Hatası: {e} ---\n")

    print(f"\n✅ BAŞARILI! Dosya Masaüstüne oluşturuldu:")
    print(f"📄 {cikis_dosyasi}")

if __name__ == "__main__":
    proje_birlestir()