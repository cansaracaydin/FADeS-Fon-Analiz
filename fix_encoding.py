import os
import codecs
from pathlib import Path

# Proje root dizini
PROJECT_ROOT = Path(__file__).parent

# Düzeltilmesi gereken dosyalar
PYTHON_FILES = [
    "app.py",
    "main.py",
    "test_api.py",
    "core/inflation_fetcher.py",
    "core/market_fetcher.py", 
    "core/processor.py",
    "core/tefas_fetcher.py",
    "core/visualizer.py"
]

def fix_encoding(file_path):
    """
    Dosya encoding'ini UTF-8'e çevirir ve başına declaration ekler.
    """
    try:
        # Dosyayı oku (farklı encoding'leri dene)
        content = None
        for encoding in ['utf-8', 'cp1254', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"✅ {file_path}: {encoding} ile okundu")
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            print(f"❌ {file_path}: Okunamadı!")
            return False
        
        # UTF-8 BOM kaldır (varsa)
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # Encoding declaration kontrolü
        if not content.startswith('# -*- coding: utf-8 -*-'):
            content = '# -*- coding: utf-8 -*-\n' + content
        
        # UTF-8 olarak yaz
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        
        print(f"✅ {file_path}: UTF-8'e dönüştürüldü")
        return True
        
    except Exception as e:
        print(f"❌ {file_path}: Hata - {e}")
        return False


def main():
    """Ana düzeltme fonksiyonu"""
    print("=" * 60)
    print("FADeS Encoding Fix Script")
    print("=" * 60)
    print()
    
    fixed_count = 0
    failed_count = 0
    
    for file_path in PYTHON_FILES:
        full_path = PROJECT_ROOT / file_path
        
        if full_path.exists():
            if fix_encoding(full_path):
                fixed_count += 1
            else:
                failed_count += 1
        else:
            print(f"⚠️ {file_path}: Dosya bulunamadı!")
            failed_count += 1
    
    print()
    print("=" * 60)
    print(f"✅ Düzeltilen: {fixed_count}")
    print(f"❌ Başarısız: {failed_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()


# ============================================
# ALTERNATIF: VSCode settings.json
# ============================================
"""
Projenizin kök dizinine .vscode/settings.json ekleyin:

{
    "files.encoding": "utf8",
    "files.autoGuessEncoding": false,
    "files.eol": "\\n",
    "[python]": {
        "editor.defaultFormatter": "ms-python.black-formatter",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    },
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black"
}
"""

# ============================================
# GIT için .gitattributes dosyası
# ============================================
"""
Proje root'una .gitattributes ekleyin:

# Python dosyaları UTF-8 olmalı
*.py text eol=lf encoding=utf-8

# Config dosyaları
*.yaml text eol=lf
*.yml text eol=lf
*.json text eol=lf
*.toml text eol=lf

# Requirements
requirements*.txt text eol=lf

# Markdown ve dokümantasyon
*.md text eol=lf
"""