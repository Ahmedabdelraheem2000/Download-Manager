import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
import yt_dlp

app = Flask(__name__)

# السماح بالاتصال من جميع المصادر (أو من مصدر معين)
socketio = SocketIO(app, cors_allowed_origins="*")  # أو يمكنك استبدال "*" بـ "http://localhost:5001" لو أردت السماح فقط لهذا المصدر

# مجلد التخزين المؤقت على السيرفر داخل مجلد المشروع
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# دالة لتحميل الفيديو إلى السيرفر
def download_video(url, progress_hook=None):
    print("بدء التحميل من الرابط: ", url)  # سجل بداية التحميل
    ydl_opts = {
        'format': 'bestvideo',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),  # وضع الفيديو في مجلد downloads
        'progress_hooks': [progress_hook] if progress_hook else [],
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print("خطأ في التحميل: ", e)  # سجل أي خطأ يحدث أثناء التحميل

# دالة لتحديث حالة التحميل
def progress_hook(d):
    if d['status'] == 'finished':
        file_name = d['info_dict']['title'] + '.' + d['info_dict']['ext']
        print(f"التحميل انتهى. الملف: {file_name}")  # سجل اسم الملف عند الانتهاء من التحميل
        # إرسال رابط التحميل إلى العميل بعد الانتهاء من التحميل
        socketio.emit('download_status', {'status': 'تم التحميل بنجاح', 'filename': file_name})
    elif d['status'] == 'downloading':
        # إرسال التحديثات الخاصة بحالة التحميل
        socketio.emit('download_status', {'status': f"جاري التحميل: {d['_percent_str']}"})

# الصفحة الرئيسية
@app.route('/')
def index():
    return render_template('index.html')

# رابط لتحميل الفيديو
@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data['url']
    # بدء التحميل في الخلفية
    socketio.start_background_task(download_video, url, progress_hook)
    return jsonify({'status': 'started'}), 200

# تنزيل الملف بعد التحميل
@app.route('/download_file/<filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

# تشغيل السيرفر
if __name__ == '__main__':
    socketio.run(app, debug=True, port=5001)
