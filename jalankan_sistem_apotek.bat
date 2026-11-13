@echo off
title SISTEM APOTEK MULTI-CABANG - FR.IA.04A
color 0A
cls
echo ==============================================================================
echo   SISTEM INVENTORI DAN PENJUALAN APOTEK MULTI-CABANG (PT SEHAT BERSAMA FARMA)
echo   Dokumen Uji Kompetensi: FR.IA.04A (Programmer Basis Data - SKK-26/20/2024)
echo ==============================================================================
echo.

echo [1/3] Memeriksa status service MySQL / XAMPP...
netstat -ano | findstr :3306 >nul
if %errorlevel% neq 0 (
    echo [*] MySQL belum aktif. Mencoba menjalankan MySQL dari XAMPP...
    if exist "C:\xampp\mysql\bin\mysqld.exe" (
        start "" "C:\xampp\mysql\bin\mysqld.exe" --defaults-file="C:\xampp\mysql\bin\my.ini" --standalone
        timeout /t 3 /nobreak >nul
        echo [OK] MySQL berhasil dijalankan di background!
    ) else (
        echo [!] File mysqld.exe tidak ditemukan di C:\xampp\mysql.
        echo [!] Silakan buka XAMPP Control Panel dan klik 'Start' pada modul MySQL.
    )
) else (
    echo [OK] MySQL Service aktif di port 3306!
)

echo.
echo [2/3] Menginisialisasi skema basis data, tabel, view, procedure, dan seed data...
"C:\Users\M S I\AppData\Local\Programs\Python\Python314\python.exe" scripts\setup_database.py

echo.
echo [3/3] Menjalankan Web Aplikasi Streamlit...
echo Web portal akan terbuka di browser Anda (http://localhost:8501)...
echo Tekan CTRL + C di jendela ini untuk menghentikan server web.
echo.
"C:\Users\M S I\AppData\Local\Programs\Python\Python314\python.exe" -m streamlit run app.py --server.port 8501

pause
