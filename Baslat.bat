@echo off
echo ==========================================
echo   FADeS Fon Analiz Sistemi Baslatiliyor...
echo ==========================================
echo.
echo Lutfen bekleyiniz, tarayici otomatik acilacak...

cd /d "%~dp0"
call venv\Scripts\activate
streamlit run app.py
pause