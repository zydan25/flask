"""
Flask API لاستقبال البيانات من بوت واتساب
مع واجهة ويب لعرض الرسائل والحالات

المطور: HASRIAN TOPTECH
"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
import json
import os
import base64
from collections import deque

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ===== تخزين البيانات في الذاكرة =====
# في الإنتاج، استخدم قاعدة بيانات فعلية
bot_status = {
    'status': 'disconnected',
    'isReady': False,
    'hasQR': False,
    'clientInfo': None,
    'lastUpdate': None,
    'reconnectAttempts': 0
}

current_qr = {
    'qrCode': None,
    'qrImage': None,
    'timestamp': None
}

# قائمة الرسائل (نحتفظ بآخر 100 رسالة)
messages = deque(maxlen=100)

# إحصائيات
stats = {
    'total_messages': 0,
    'messages_today': 0,
    'qr_scans': 0,
    'status_updates': 0
}

# ===== مجلد الصور =====
QR_IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'qr_images')
os.makedirs(QR_IMAGES_DIR, exist_ok=True)


# =============================================================================
# ===== Webhook Endpoints =====
# =============================================================================

@app.route('/webhook/qr', methods=['POST'])
def receive_qr():
    """استقبال QR Code من البوت"""
    try:
        data = request.json
        
        # حفظ QR Code
        current_qr['qrCode'] = data.get('qrCode')
        current_qr['qrImage'] = data.get('qrImage')
        current_qr['timestamp'] = data.get('timestamp')
        
        # حفظ QR كصورة
        if current_qr['qrImage']:
            save_qr_image(current_qr['qrImage'])
        
        # تحديث الحالة
        bot_status['hasQR'] = True
        bot_status['status'] = 'qr'
        bot_status['lastUpdate'] = datetime.now().isoformat()
        
        # إحصائيات
        stats['qr_scans'] += 1
        
        print(f"📱 تم استقبال QR Code جديد - {data.get('timestamp')}")
        
        # إرسال للعملاء المتصلين عبر WebSocket
        socketio.emit('qr_update', {
            'qrImage': current_qr['qrImage'],
            'timestamp': current_qr['timestamp']
        })
        
        socketio.emit('status_update', bot_status)
        
        return jsonify({
            'success': True,
            'message': 'تم استقبال QR Code بنجاح'
        }), 200
        
    except Exception as e:
        print(f"❌ خطأ في استقبال QR: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/webhook/status', methods=['POST'])
def receive_status():
    """استقبال حالة البوت"""
    try:
        data = request.json
        
        # تحديث الحالة
        bot_status['status'] = data.get('status', 'unknown')
        bot_status['isReady'] = data.get('isReady', False)
        bot_status['hasQR'] = data.get('hasQR', False)
        bot_status['clientInfo'] = data.get('clientInfo')
        bot_status['reconnectAttempts'] = data.get('reconnectAttempts', 0)
        bot_status['lastUpdate'] = datetime.now().isoformat()
        
        # إحصائيات
        stats['status_updates'] += 1
        
        # إذا أصبح البوت جاهزاً، احذف QR
        if bot_status['isReady']:
            current_qr['qrCode'] = None
            current_qr['qrImage'] = None
        
        print(f"📊 تحديث الحالة: {bot_status['status']} - Ready: {bot_status['isReady']}")
        
        # إرسال للعملاء المتصلين
        socketio.emit('status_update', bot_status)
        
        return jsonify({
            'success': True,
            'message': 'تم استقبال تحديث الحالة'
        }), 200
        
    except Exception as e:
        print(f"❌ خطأ في استقبال الحالة: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/webhook/message', methods=['POST'])
def receive_message():
    """استقبال رسالة من البوت"""
    try:
        data = request.json
        
        # إضافة timestamp إذا لم يكن موجوداً
        if 'receivedAt' not in data:
            data['receivedAt'] = datetime.now().isoformat()
        
        # إضافة الرسالة للقائمة
        messages.append(data)
        
        # إحصائيات
        stats['total_messages'] += 1
        stats['messages_today'] += 1
        
        print(f"💬 رسالة جديدة من {data.get('from')}: {data.get('body', '')[:50]}")
        
        # إرسال للعملاء المتصلين
        socketio.emit('new_message', data)
        socketio.emit('stats_update', stats)
        
        return jsonify({
            'success': True,
            'message': 'تم استقبال الرسالة'
        }), 200
        
    except Exception as e:
        print(f"❌ خطأ في استقبال الرسالة: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# ===== API Endpoints للواجهة =====
# =============================================================================

@app.route('/api/status', methods=['GET'])
def get_status():
    """الحصول على حالة البوت"""
    return jsonify({
        'success': True,
        'data': bot_status
    })


@app.route('/api/qr', methods=['GET'])
def get_qr():
    """الحصول على QR Code الحالي"""
    return jsonify({
        'success': True,
        'data': current_qr
    })


@app.route('/api/messages', methods=['GET'])
def get_messages():
    """الحصول على قائمة الرسائل"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify({
        'success': True,
        'data': list(messages)[-limit:],
        'count': len(messages)
    })


@app.route('/api/messages/<message_id>', methods=['GET'])
def get_message(message_id):
    """الحصول على رسالة محددة"""
    for msg in messages:
        if msg.get('messageId') == message_id:
            return jsonify({
                'success': True,
                'data': msg
            })
    
    return jsonify({
        'success': False,
        'error': 'الرسالة غير موجودة'
    }), 404


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """الحصول على الإحصائيات"""
    return jsonify({
        'success': True,
        'data': stats
    })


@app.route('/api/clear-messages', methods=['POST'])
def clear_messages():
    """حذف جميع الرسائل"""
    messages.clear()
    stats['total_messages'] = 0
    stats['messages_today'] = 0
    
    socketio.emit('messages_cleared')
    
    return jsonify({
        'success': True,
        'message': 'تم حذف جميع الرسائل'
    })


# =============================================================================
# ===== صفحات الواجهة =====
# =============================================================================

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    return render_template('index.html')


@app.route('/messages')
def messages_page():
    """صفحة الرسائل"""
    return render_template('messages.html')


@app.route('/qr')
def qr_page():
    """صفحة QR Code"""
    return render_template('qr.html')


# =============================================================================
# ===== WebSocket Events =====
# =============================================================================

@socketio.on('connect')
def handle_connect():
    """عند اتصال عميل جديد"""
    print('✅ عميل جديد متصل')
    
    # إرسال البيانات الحالية للعميل
    emit('status_update', bot_status)
    emit('stats_update', stats)
    
    if current_qr['qrImage']:
        emit('qr_update', {
            'qrImage': current_qr['qrImage'],
            'timestamp': current_qr['timestamp']
        })


@socketio.on('disconnect')
def handle_disconnect():
    """عند قطع اتصال عميل"""
    print('⚠️ عميل قطع الاتصال')


@socketio.on('request_messages')
def handle_request_messages(data):
    """طلب الرسائل"""
    limit = data.get('limit', 50)
    emit('messages_list', {
        'messages': list(messages)[-limit:],
        'count': len(messages)
    })


# =============================================================================
# ===== وظائف مساعدة =====
# =============================================================================

def save_qr_image(qr_image_base64):
    """حفظ QR Code كصورة"""
    try:
        # إزالة البادئة
        if 'base64,' in qr_image_base64:
            qr_image_base64 = qr_image_base64.split('base64,')[1]
        
        # فك التشفير
        image_data = base64.b64decode(qr_image_base64)
        
        # اسم الملف
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'qr_{timestamp}.png'
        filepath = os.path.join(QR_IMAGES_DIR, filename)
        
        # حفظ الملف
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        print(f"💾 تم حفظ QR Code: {filename}")
        
        return filename
        
    except Exception as e:
        print(f"❌ خطأ في حفظ QR: {str(e)}")
        return None


@app.route('/qr_images/<filename>')
def serve_qr_image(filename):
    """عرض صورة QR المحفوظة"""
    return send_from_directory(QR_IMAGES_DIR, filename)


# =============================================================================
# ===== تشغيل التطبيق =====
# =============================================================================

if __name__ == '__main__':
    print('=' * 60)
    print('🚀 Flask API لبوت واتساب')
    print('=' * 60)
    print('📡 الخادم يعمل على: http://localhost:5000')
    print('🌐 الواجهة الرئيسية: http://localhost:5000/')
    print('💬 صفحة الرسائل: http://localhost:5000/messages')
    print('📱 صفحة QR: http://localhost:5000/qr')
    print('=' * 60)
    print('')
    
    # تشغيل الخادم
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
