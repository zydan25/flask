# Flask Server-Driven Runtime Control Plane

هذا الخادم هو Control Plane لتطبيق Flutter Server-Driven Runtime.

## ماذا يدير؟
- تطبيقات وإصدارات Runtime.
- شاشات STAC كاملة كـJSON.
- Resources وcache policy.
- Actions وWorkflows.
- API Profiles وEndpoint definitions.
- Data Models وRecords لتغذية تطبيق Flutter.
- Permissions وFeature Flags.
- Sync وEvents وWebSocket.
- Webhooks.
- Code Assets محفوظة بدون تنفيذ مباشر.

## التشغيل
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

لوحة الإدارة: `/admin/login`

Runtime bootstrap: `GET /runtime/bootstrap?app=flutter-app`

Production:
```bash
gunicorn wsgi:app --bind 0.0.0.0:5100 --workers 2 --threads 4
```

Code Assets تخزن الكود فقط. التنفيذ المباشر معطل افتراضيًا (`stored_only`) ويجب أن يمر مستقبلًا عبر registry موقّع وsandbox.
