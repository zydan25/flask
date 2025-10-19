# 🚀 دليل البدء السريع

## خطوات التشغيل (5 دقائق)

### 1️⃣ تثبيت المكتبات
```bash
cd flask_api
pip install -r requirements.txt
```

### 2️⃣ تشغيل السيرفر
**Windows:**
```bash
run.bat
```

**Linux/Mac:**
```bash
python app.py
```

### 3️⃣ فتح المتصفح
انتقل إلى: http://localhost:5000

## ✅ اختبار النظام

### اختبار 1: إرسال QR Code
```bash
curl -X POST http://localhost:5000/webhook/qr \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test",
    "qrCode": "test-qr-code",
    "qrImage": "data:image/png;base64,iVBORw0KGgo...",
    "timestamp": "2025-01-18T00:00:00Z"
  }'
```

### اختبار 2: إرسال حالة
```bash
curl -X POST http://localhost:5000/webhook/status \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test",
    "status": "ready",
    "isReady": true,
    "clientInfo": {
      "phoneNumber": "967123456789",
      "pushname": "اختبار",
      "platform": "android"
    }
  }'
```

### اختبار 3: إرسال رسالة
```bash
curl -X POST http://localhost:5000/webhook/message \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test",
    "messageId": "msg-123",
    "from": "+967123456789",
    "body": "مرحباً! هذه رسالة تجريبية",
    "type": "chat",
    "timestamp": 1705536000,
    "contactName": "أحمد",
    "isGroup": false,
    "hasMedia": false
  }'
```

## 🔗 ربط مع بوت Node.js

### في ملف `.env` للبوت:
```env
API_BASE_URL=http://localhost:5000
```

### تشغيل البوت:
```bash
cd ..
npm start
```

## 📊 الصفحات المتاحة

| الصفحة | الرابط | الوصف |
|--------|--------|-------|
| 🏠 الرئيسية | http://localhost:5000 | لوحة التحكم |
| 💬 الرسائل | http://localhost:5000/messages | عرض الرسائل |
| 📱 QR Code | http://localhost:5000/qr | مسح الرمز |

## 🐛 حل المشاكل

### السيرفر لا يبدأ
```bash
# تحقق من Python
python --version

# أعد تثبيت المكتبات
pip install -r requirements.txt --force-reinstall
```

### المنفذ 5000 مشغول
عدّل في `app.py` السطر الأخير:
```python
socketio.run(app, host='0.0.0.0', port=5001, debug=True)
```

### الواجهة لا تتحدث
- تأكد من تشغيل السيرفر
- افتح console في المتصفح (F12)
- تحقق من اتصال WebSocket

## 💡 نصائح

1. **للتطوير:** استخدم `debug=True` (مفعّل افتراضياً)
2. **للإنتاج:** استخدم Gunicorn:
   ```bash
   gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
   ```
3. **للمراقبة:** افتح عدة نوافذ لرؤية التحديثات الفورية

## 📞 دعم

راجع `README.md` للتوثيق الكامل!

---

**جاهز للاستخدام! 🎉**
