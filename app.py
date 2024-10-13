from flask import Flask, request, send_from_directory, jsonify, render_template
import os
import yt_dlp
from threading import Thread
import time
import shutil

app = Flask(__name__)
UPLOAD_FOLDER = 'downloads'
MAX_SIZE = 1 * 1024 * 1024 * 1024  # 1 جيجابايت

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# وظيفة لتحميل الفيديو
def download_video(url):
    # تعديل إعدادات yt-dlp لاختيار أفضل تنسيق فيديو لا يتطلب ffmpeg
    ydl_opts = {
        'outtmpl': os.path.join(UPLOAD_FOLDER, '%(title)s.%(ext)s'),
        'format': 'best',  # اختيار أفضل تنسيق يحتوي على الفيديو والصوت
        'noplaylist': True,  # تجنب تحميل قوائم التشغيل
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info_dict)  # إرجاع اسم الملف الكامل


# دالة لحساب الحجم الإجمالي للمجلد
def get_folder_size(folder):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


# وظيفة لحذف الملفات بعد 24 ساعة
def auto_cleanup():
    while True:
        now = time.time()
        for filename in os.listdir(UPLOAD_FOLDER):
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            if os.stat(filepath).st_mtime < now - 86400:  # 24 ساعة
                os.remove(filepath)
        if get_folder_size(UPLOAD_FOLDER) > MAX_SIZE:
            shutil.rmtree(UPLOAD_FOLDER)
            os.makedirs(UPLOAD_FOLDER)
        time.sleep(3600)  # تحقق كل ساعة


# بدء عملية الحذف التلقائي في الخلفية
Thread(target=auto_cleanup, daemon=True).start()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    video_url = request.form['url']

    # تحميل الفيديو بشكل متزامن وإرجاع اسم الملف
    try:
        filename = download_video(video_url)
        return jsonify({"message": "تم تحميل الفيديو بنجاح", "filename": os.path.basename(filename)})
    except Exception as e:
        return jsonify({"message": "فشل تحميل الفيديو", "error": str(e)})


@app.route('/downloads/<filename>')
def get_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    app.run(debug=True)
