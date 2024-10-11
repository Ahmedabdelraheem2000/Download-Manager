import os
import yt_dlp
from flask import Flask, render_template, request, jsonify
import threading

app = Flask(__name__)

# قائمة الجودات المعروفة التي نريد عرضها فقط
ALLOWED_QUALITIES = [144, 240, 360, 480, 720, 1080, 1440, 2160]

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

def download_video(url, quality):
    """تحميل الفيديو بالجودة المختارة دون تحويل"""
    video_opts = {
        'format': f'bestvideo[height<={quality}]+bestaudio/best',
        'outtmpl': os.path.join(os.getcwd(), 'downloads', '%(title)s.%(ext)s'),  # حفظ الملف في مجلد التنزيلات
        'noplaylist': True
    }

    try:
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            info = ydl.extract_info(url)
            video_file = ydl.prepare_filename(info)  # الحصول على مسار الملف المحمّل
            ydl.download([url])  # تحميل الفيديو
            return video_file
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load_formats', methods=['POST'])
def load_formats():
    url = request.json.get('url')
    formats = get_video_formats(url)
    return jsonify({'formats': formats})

@app.route('/download_video', methods=['POST'])
def download_video_api():
    url = request.json.get('url')
    quality = request.json.get('quality')
    video_path = download_video(url, quality)
    if video_path:
        return jsonify({'status': 'success', 'path': video_path})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to download the video.'})

if __name__ == '__main__':
    os.makedirs('downloads', exist_ok=True)  # تأكد من وجود مجلد التنزيلات
    app.run(debug=True)
