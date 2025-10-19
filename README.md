# 🐍 Flask API لبوت واتساب

واجهة ويب متقدمة لاستقبال وعرض بيانات بوت واتساب في الوقت الفعلي.

## 🌟 المميزات

- ✅ **واجهة ويب جميلة** - تصميم عصري ومتجاوب
- 🔄 **تحديثات فورية** - باستخدام WebSocket (Socket.IO)
- 📱 **عرض QR Code** - مباشرة في المتصفح
- 💬 **إدارة الرسائل** - عرض وفلترة وبحث
- 📊 **إحصائيات** - متابعة نشاط البوت
- 🎨 **تصميم عربي** - واجهة RTL كاملة

## 📋 المتطلبات

- Python 3.8 أو أحدث
- pip (مدير حزم Python)

## 🚀 التثبيت

### 1. تثبيت المكتبات
```bash
cd flask_api
pip install -r requirements.txt
```

### 2. تشغيل السيرفر
```bash
python app.py
```

السيرفر سيعمل على: `http://localhost:5000`

## 📡 الصفحات المتاحة

### الصفحة الرئيسية
```
http://localhost:5000/
```
- عرض حالة البوت
- معلومات الحساب المتصل
- إحصائيات سريعة
- آخر الرسائل

### صفحة الرسائل
```
http://localhost:5000/messages
```
- عرض جميع الرسائل
- بحث وفلترة متقدمة
- عرض تفاصيل كل رسالة
- دعم الملفات المرفقة

### صفحة QR Code
```
http://localhost:5000/qr
```
- عرض QR Code الحالي
- تحديثات فورية
- إرشادات الاتصال

## 🔌 Webhook Endpoints

هذه هي نقاط الاستقبال التي يرسل إليها البوت البيانات:

### 1. استقبال QR Code
```http
POST /webhook/qr
Content-Type: application/json

{
  "sessionId": "main_whatsapp_bot",
  "qrCode": "string",
  "qrImage": "data:image/png;base64,...",
  "timestamp": "2025-01-18T00:00:00.000Z"
}
```

### 2. استقبال حالة البوت
```http
POST /webhook/status
Content-Type: application/json

{
  "sessionId": "main_whatsapp_bot",
  "status": "ready",
  "isReady": true,
  "hasQR": false,
  "clientInfo": {
    "phoneNumber": "967xxxxxxxxx",
    "pushname": "اسم المستخدم",
    "platform": "android"
  },
  "reconnectAttempts": 0,
  "timestamp": "2025-01-18T00:00:00.000Z"
}
```

### 3. استقبال الرسائل
```http
POST /webhook/message
Content-Type: application/json

{
  "sessionId": "main_whatsapp_bot",
  "messageId": "...",
  "from": "+967xxxxxxxxx",
  "to": "...",
  "body": "نص الرسالة",
  "type": "chat",
  "timestamp": 1234567890,
  "isGroup": false,
  "contactName": "اسم المرسل",
  "hasMedia": false,
  "mediaType": "image/jpeg",
  "mediaData": "base64..."
}
```

## 📊 API Endpoints للواجهة

### الحصول على حالة البوت
```http
GET /api/status

Response:
{
  "success": true,
  "data": {
    "status": "ready",
    "isReady": true,
    "hasQR": false,
    "clientInfo": {...},
    "lastUpdate": "2025-01-18T00:00:00.000Z"
  }
}
```

### الحصول على QR Code
```http
GET /api/qr

Response:
{
  "success": true,
  "data": {
    "qrCode": "string",
    "qrImage": "data:image/png;base64,...",
    "timestamp": "2025-01-18T00:00:00.000Z"
  }
}
```

### الحصول على الرسائل
```http
GET /api/messages?limit=50

Response:
{
  "success": true,
  "data": [...],
  "count": 50
}
```

### الحصول على الإحصائيات
```http
GET /api/stats

Response:
{
  "success": true,
  "data": {
    "total_messages": 100,
    "messages_today": 50,
    "qr_scans": 5,
    "status_updates": 200
  }
}
```

### حذف جميع الرسائل
```http
POST /api/clear-messages

Response:
{
  "success": true,
  "message": "تم حذف جميع الرسائل"
}
```

## 🔄 WebSocket Events

الواجهة تستخدم Socket.IO للتحديثات الفورية:

### Events المُرسلة للعملاء
- `status_update` - تحديث حالة البوت
- `qr_update` - QR Code جديد
- `new_message` - رسالة جديدة
- `stats_update` - تحديث الإحصائيات
- `messages_cleared` - تم حذف الرسائل

### Events المستقبلة من العملاء
- `connect` - عند الاتصال
- `disconnect` - عند قطع الاتصال
- `request_messages` - طلب الرسائل

## 🎨 التخصيص

### تغيير المنفذ
في ملف `app.py`:
```python
socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

### تغيير الألوان
عدّل في ملف `templates/base.html` في قسم `<style>`:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### إضافة مصادقة
```python
from functools import wraps
from flask import request, jsonify

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != 'your-secret-key':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/webhook/message', methods=['POST'])
@require_api_key
def receive_message():
    # ...
```

## 📦 البنية

```
flask_api/
├── app.py              # الملف الرئيسي
├── requirements.txt    # المكتبات المطلوبة
├── templates/          # قوالب HTML
│   ├── base.html      # القالب الأساسي
│   ├── index.html     # الصفحة الرئيسية
│   ├── messages.html  # صفحة الرسائل
│   └── qr.html        # صفحة QR
└── qr_images/         # مجلد حفظ QR (يُنشأ تلقائياً)
```

## 🔗 ربط مع بوت Node.js

تأكد من تحديث ملف `.env` في بوت Node.js:

```env
API_BASE_URL=http://localhost:5000
API_WEBHOOK_QR=/webhook/qr
API_WEBHOOK_STATUS=/webhook/status
API_WEBHOOK_MESSAGE=/webhook/message
```

## 🌐 نشر على الإنترنت

### استخدام Gunicorn (للإنتاج)
```bash
pip install gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

### استخدام Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

## 🛠️ استكشاف الأخطاء

### خطأ في تشغيل السيرفر
```bash
# تأكد من تثبيت المكتبات
pip install -r requirements.txt

# جرب منفذ مختلف
python app.py  # وعدّل المنفذ في الكود
```

### WebSocket لا يعمل
- تأكد من أن المنفذ 5000 غير محجوب
- تحقق من إعدادات CORS
- راجع console في المتصفح

### الرسائل لا تظهر
- تأكد من تشغيل بوت Node.js
- تحقق من `API_BASE_URL` في بوت Node.js
- راجع logs السيرفر Flask

## 📝 ملاحظات

- البيانات محفوظة في الذاكرة (RAM) - ستُفقد عند إعادة التشغيل
- لحفظ دائم، استخدم قاعدة بيانات (MongoDB, SQLite, PostgreSQL)
- الواجهة تدعم حتى 100 رسالة في الذاكرة
- يمكنك تعديل الحد الأقصى في `app.py`: `messages = deque(maxlen=100)`

## 🔐 الأمان

للإنتاج، يُنصح بـ:
- إضافة مصادقة للـ webhooks
- استخدام HTTPS
- تشفير البيانات الحساسة
- إضافة rate limiting
- استخدام firewall

## 📄 الترخيص

MIT License

---

**المطور:** HASRIAN TOPTECH  
**التاريخ:** 2025
