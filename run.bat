@echo off
chcp 65001 >nul
cls

echo ========================================
echo    Flask API - WhatsApp Bot
echo ========================================
echo.

REM التحقق من تثبيت Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ خطأ: Python غير مثبت!
    echo يرجى تثبيت Python من: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python متوفر
echo.

REM التحقق من تثبيت المكتبات
echo 📦 التحقق من المكتبات المطلوبة...
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo ⚠️  المكتبات غير مثبتة، جاري التثبيت...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ فشل تثبيت المكتبات!
        pause
        exit /b 1
    )
    echo ✅ تم تثبيت المكتبات بنجاح
) else (
    echo ✅ المكتبات مثبتة
)

echo.
echo ========================================
echo 🚀 بدء تشغيل السيرفر...
echo ========================================
echo.
echo 🌐 الواجهة: http://localhost:5000
echo 💬 الرسائل: http://localhost:5000/messages
echo 📱 QR Code: http://localhost:5000/qr
echo.
echo اضغط Ctrl+C لإيقاف السيرفر
echo ========================================
echo.

REM تشغيل السيرفر
python app.py

pause
