import os
from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO, emit
import yt_dlp
from eventlet import monkey_patch

monkey_patch()

app = Flask(__name__)

# السماح بالاتصال من جميع المصادر
socketio = SocketIO(app, cors_allowed_origins="*")

# مجلد التخزين المؤقت
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


# دالة لتحميل الفيديو وإرسال التحديثات
def download_video(url, progress_hook=None):
    print("بدء التحميل من الرابط:", url)
    ydl_opts = {
        'format': 'bestvideo',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook] if progress_hook else [],
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print("خطأ في التحميل:", e)


# تحديث حالة التحميل
def progress_hook(d):
    if d['status'] == 'finished':
        file_name = d['info_dict']['title'] + '.' + d['info_dict']['ext']
        print(f"التحميل انتهى. الملف: {file_name}")
        socketio.emit('download_status', {'status': 'التحميل مكتمل', 'filename': file_name})
    elif d['status'] == 'downloading':
        socketio.emit('download_status', {'status': f"جاري التحميل: {d['_percent_str']}"})


# الصفحة الرئيسية
@app.route('/')
def index():
    return render_template('index.html')


# بدء عملية التحميل
@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data['url']
    socketio.start_background_task(download_video, url, progress_hook)
    return jsonify({'status': 'started'}), 200


# إرسال الملف بعد التحميل
@app.route('/download_file/<filename>')
def download_file(filename):
    def generate():
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        with open(file_path, 'rb') as f:
            while chunk := f.read(1024 * 1024):  # إرسال 1 ميجابايت في كل مرة
                yield chunk

    return Response(generate(), mimetype="video/mp4")


# تشغيل السيرفر
if __name__ == '__main__':
    socketio.run(app, debug=False, use_reloader=False)
