import os
import yt_dlp
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# قائمة الجودات المسموح بها
ALLOWED_QUALITIES = [144, 240, 360, 480, 720, 1080, 1440, 2160]

def get_download_folder():
    """احصل على مسار مجلد التنزيلات الخاص بالمستخدم"""
    return os.path.join(os.path.expanduser("~"), "Downloads")

def get_video_formats(url):
    """احصل على تنسيقات الفيديو المتاحة لعنوان URL"""
    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])

        unique_formats = {}
        for fmt in formats:
            height = fmt.get('height', 'N/A')
            if height in ALLOWED_QUALITIES and height not in unique_formats and fmt.get('vcodec') != 'none':
                unique_formats[height] = fmt

        sorted_formats = sorted(unique_formats.values(), key=lambda x: x.get('height', 0))
        return [{'height': fmt['height'], 'format_id': fmt['format_id']} for fmt in sorted_formats]

def download_video(url, quality, video_id):
    """تحميل الفيديو بالجودة المختارة"""
    download_folder = get_download_folder()  # مجلد التنزيلات
    base_filename = os.path.join(download_folder, '%(title)s')  # اسم الملف بدون امتداد
    extension = '.%(ext)s'  # الامتداد

    # إعداد اسم الملف الجديد
    original_filename = base_filename + extension  # اسم الملف الأصلي
    new_filename = original_filename  # البداية بنفس الاسم الأصلي
    count = 1

    # تحقق مما إذا كان الملف موجودًا، وإذا كان موجودًا، أضف رقمًا
    while os.path.exists(new_filename):
        new_filename = f"{base_filename}({count}){extension}"  # أضف رقمًا إلى اسم الملف
        count += 1

    video_opts = {
        'format': f'bestvideo[height<={quality}]+bestaudio/best',
        'outtmpl': new_filename,  # استخدام الاسم الجديد
        'noplaylist': True,
        'progress_hooks': [lambda d: progress_hook(d, video_id)]
    }

    try:
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            ydl.download([url])
            socketio.emit('download_status', {'video_id': video_id, 'status': 'success'})
    except Exception as e:
        print(f"Error downloading video: {e}")
        socketio.emit('download_status', {'video_id': video_id, 'status': 'error'})

def progress_hook(d, video_id):
    """تحديث حالة التحميل"""
    if d['status'] == 'downloading':
        percent = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
        socketio.emit('download_status', {'video_id': video_id, 'status': 'downloading', 'percent': percent})
    elif d['status'] == 'finished':
        socketio.emit('download_status', {'video_id': video_id, 'status': 'finished', 'percent': 100})

@socketio.on('load_formats')
def handle_load_formats(data):
    url = data['url']
    formats = get_video_formats(url)
    socketio.emit('formats_loaded', {'formats': formats})

@socketio.on('start_download')
def handle_download(data):
    url = data['url']
    quality = data['quality']
    video_id = data['video_id']

    # بدء تحميل الفيديو في مهمة خلفية باستخدام eventlet
    socketio.start_background_task(target=download_video, url=url, quality=quality, video_id=video_id)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=8080)
