import os
import re
import json
import glob
from flask import Flask, render_template, request, send_from_directory, jsonify, url_for, session, redirect
from yt_dlp import YoutubeDL
from dotenv import load_dotenv

load_dotenv()

def sanitize_filename(name):
    """파일명에서 사용할 수 없는 문자 제거"""
    return re.sub(r'[\\/*?:"<>|]', "_", name)

def create_app():
    app = Flask(__name__, static_folder='static')
    app.secret_key = os.getenv("SECRET_KEY", "default-secret")
    
    PASSWORD = os.getenv("ACCESS_CODE")
    
    # 1. 로그인 라우트 (예외)
    @app.route("/auth", methods=["GET", "POST"])
    def auth():
        if request.method == "POST":
            code = request.form.get("code")
            if code == PASSWORD:
                session['authenticated'] = True
                return redirect(url_for('index'))
            return render_template("auth.html", error="암호가 틀렸습니다.")
        return render_template("auth.html")

    # 2. 전역 요청 전에 인증 검사
    @app.before_request
    def require_authentication():
        allowed_paths = {'/auth', '/static'}  # 인증 없이 허용할 경로들
        if request.path.startswith("/static"):
            return  # 정적 파일은 통과

        if not session.get("authenticated") and request.path not in allowed_paths:
            return redirect(url_for("auth"))

    # 서버가 임시로 저장할 다운로드 폴더
    DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "downloads"))
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/", methods=["POST"])
    def download():
        data = request.get_json()
        url = data.get("url")
        if not url:
            return jsonify({"error": "URL이 비어 있습니다."}), 400

        try:
            # 1단계: 영상 정보 추출
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                title = sanitize_filename(info.get("title", "video"))

            # 2단계: 저장 경로 템플릿 지정
            outtmpl = os.path.join(DOWNLOAD_FOLDER, title + ".%(ext)s")
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': outtmpl,
                'merge_output_format': 'mp4',
                'quiet': True,
                'noplaylist': True
            }

            # 3단계: 실제 다운로드 수행
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # 4단계: 다운로드된 파일의 실제 경로 찾기
            matched_files = glob.glob(os.path.join(DOWNLOAD_FOLDER, title + ".*"))
            if not matched_files:
                return jsonify({"error": "다운로드된 파일을 찾을 수 없습니다."}), 404

            filename = os.path.basename(matched_files[0])
            download_url = url_for("serve_file", filename=filename)
            return jsonify({"download_url": download_url})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/download/<filename>")
    def serve_file(filename):
        return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

    return app