from flask import Flask, request, jsonify
import yt_dlp
import os
from threading import Thread
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'downloads'
MAX_SIZE = 1 * 1024 * 1024 * 1024  # 1 جيجابايت

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# وظيفة لتحميل الفيديو
def download_video(url):
    ydl_opts = {
        'outtmpl': os.path.join(UPLOAD_FOLDER, '%(title)s.%(ext)s'),
        'format': 'best',
        'noplaylist': True,  # تجنب تحميل قوائم التشغيل
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info_dict)


# دالة لمعالجة التحميل في الخلفية
def download_in_background(url, callback):
    try:
        filename = download_video(url)
        callback(filename)
    except Exception as e:
        callback(None, str(e))


@app.route('/download', methods=['POST'])
def download():
    video_url = request.form['url']

    # هنا نقوم بتشغيل التحميل في الخلفية باستخدام Thread
    def callback(filename, error=None):
        if error:
            return jsonify({"message": "فشل تحميل الفيديو", "error": error})
        return jsonify({"message": "تم تحميل الفيديو بنجاح", "filename": filename})

    # تشغيل التحميل في الخلفية
    thread = Thread(target=download_in_background, args=(video_url, callback))
    thread.start()

    return jsonify({"message": "تم بدء تحميل الفيديو، سيتم إعلامك عند الانتهاء."})


if __name__ == "__main__":
    app.run(debug=True)
