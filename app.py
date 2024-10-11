import os
import yt_dlp
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import platform

app = Flask(__name__)
socketio = SocketIO(app)

# قائمة الجودات المعروفة التي نريد عرضها فقط
ALLOWED_QUALITIES = [144, 240, 360, 480, 720, 1080, 1440, 2160]


def get_download_folder():
    """احصل على مسار مجلد التنزيلات الخاص بالمستخدم"""
    if platform.system() == "Windows":
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    elif platform.system() == "Darwin":  # نظام macOS
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    else:  # نظام Linux
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    return download_folder


def get_video_formats(url):
    """احصل على تنسيقات الفيديو المتاحة لعنوان URL المقدم"""
    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])

        unique_formats = {}
        for fmt in formats:
            height = fmt.get('height', 'N/A')
            if height in ALLOWED_QUALITIES and height not in unique_formats and fmt.get('vcodec') != 'none':
                unique_formats[height] = fmt

        sorted_formats = sorted(unique_formats.values(), key=lambda x: x.get('height', 0))
        return sorted_formats


def download_video(url, quality, video_id):
    """تحميل الفيديو بالجودة المختارة دون تحويل"""
    download_folder = get_download_folder()  # احصل على مجلد التنزيلات
    video_opts = {
        'format': f'bestvideo[height<={quality}]+bestaudio/best',
        'outtmpl': os.path.join(download_folder, '%(title)s.%(ext)s'),  # حفظ الملف في مجلد التنزيلات
        'noplaylist': True,
        'progress_hooks': [lambda d: progress_hook(d, video_id)]
    }

    try:
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            ydl.download([url])  # تحميل الفيديو
            socketio.emit('download_status', {'video_id': video_id, 'status': 'success'})  # إرسال تحديث الحالة
    except Exception as e:
        print(f"Error downloading video: {e}")
        socketio.emit('download_status', {'video_id': video_id, 'status': 'error'})  # إرسال تحديث الحالة


def progress_hook(d, video_id):
    """تحديث الحالة عند تحميل الفيديو"""
    if d['status'] == 'downloading':
        percent = d.get('downloaded_bytes', 0) / d.get('total_bytes', 1) * 100
        socketio.emit('download_status', {'video_id': video_id, 'status': 'downloading', 'percent': percent})


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/load_formats', methods=['POST'])
def load_formats():
    """نقطة نهاية لتحميل تنسيقات الفيديو المتاحة"""
    data = request.json
    url = data.get('url', '')

    if url:
        formats = get_video_formats(url)
        return jsonify({'formats': formats}), 200
    else:
        return jsonify({'error': 'URL is required'}), 400


@socketio.on('start_download')
def handle_download(data):
    url = data['url']
    quality = data['quality']
    video_id = data['video_id']  # استخدم معرف الفيديو المرسل

    # بدء تحميل الفيديو في خيط جديد
    socketio.start_background_task(download_video, url, quality, video_id)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080)  # السماح بالوصول من جميع العناوين
