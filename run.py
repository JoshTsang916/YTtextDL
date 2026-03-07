import argparse
import json
import os
import sys
import re
from datetime import datetime
import requests
import qrcode
import io
import base64
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# Load environment variables
load_dotenv()

import urllib.parse as urlparse

def extract_video_id(url):
    """從網址中抽出乾淨的 Video ID"""
    parsed_url = urlparse.urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            qs = urlparse.parse_qs(parsed_url.query)
            return qs.get('v', [None])[0]
        if parsed_url.path.startswith('/embed/'):
            return parsed_url.path.split('/')[2]
        if parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    return None

def get_cookie_file():
    """
    Returns the path to the cookie file if configured via ENV or local file.
    """
    # 檢查是否透過環境變數提供 cookies
    if os.getenv('YOUTUBE_COOKIES'):
        cookies_path = '/tmp/youtube_cookies.txt'
        # 在 Windows 上可能是 /tmp 不存在，改放當前目錄
        if not os.path.exists('/tmp'):
            cookies_path = 'youtube_cookies.tmp'
        
        # 避免重複寫入，若已存在且內容一致（或簡單覆寫即可）
        with open(cookies_path, 'w', encoding='utf-8') as f:
            f.write(os.getenv('YOUTUBE_COOKIES').replace('\\n', '\n'))
        return cookies_path
    
    # 檢查本地是否有 cookies.txt
    if os.path.exists('cookies.txt'):
        return 'cookies.txt'
        
    return None

def get_video_metadata(url):
    """
    獲取 YouTube metadata，優先使用繞過驗證的 OEmbed 方案，失敗則回退 yt-dlp
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise Exception("無效的 YouTube 網址")
    
    # 策略 1: 使用 OEmbed API (不觸發 Bot 驗證)
    try:
        oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        response = requests.get(oembed_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                'id': video_id,
                'title': data.get('title'),
                'channel': data.get('author_name'),
                'upload_date': None 
            }
    except Exception as e:
        print(f"OEmbed API 發生錯誤: {e}，切換至備用方案 yt-dlp...")
        
    # 策略 2: 備案使用 yt-dlp
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'default']
            }
        }
    }
    
    # 載入 cookies 繞過機器人驗證 (特別是在 Zeabur 這種機房環境)
    cookie_file = get_cookie_file()
    if cookie_file:
        ydl_opts['cookiefile'] = cookie_file

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'channel': info.get('uploader'),
                'upload_date': info.get('upload_date'),
            }
    except Exception as e:
        raise Exception(f"無法獲取影片資訊: {str(e)}")

def get_transcript(video_id):
    """
    Fetches transcript using youtube-transcript-api.
    Priority: zh-TW > zh-Hant > zh > en
    """
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # Try to find transcript in preferred languages
        try:
            transcript = transcript_list.find_transcript(['zh-TW', 'zh-Hant', 'zh'])
            lang = transcript.language_code
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_transcript(['en'])
                lang = 'en'
            except NoTranscriptFound:
                raise Exception("[沒有字幕]")
        
        return transcript.fetch(), lang

    except TranscriptsDisabled:
        raise Exception("[沒有字幕] (字幕功能已停用)")
    except Exception as e:
        # If it's already one of our custom exceptions, re-raise it
        if str(e).startswith("["):
            raise e
        raise Exception(f"獲取字幕失敗: {str(e)}")

def chunk_transcript(transcript_data, max_chars=3500):
    """
    Chunks transcript into smaller pieces based on sentence boundaries.
    """
    full_text = ""
    for item in transcript_data:
        text = item.text.strip()
        full_text += text + " "
    
    # Split by sentence endings (., !, ?, 。, ！, ？)
    # Using regex to keep the delimiter
    sentences = re.split(r'(?<=[.!?。！？])\s*', full_text)
    
    chunks = []
    current_chunk = ""
    chunk_index = 0
    
    for sentence in sentences:
        if not sentence:
            continue
            
        if len(current_chunk) + len(sentence) > max_chars:
            if current_chunk:
                chunks.append({
                    "index": chunk_index,
                    "text": current_chunk.strip()
                })
                chunk_index += 1
                current_chunk = sentence
            else:
                # Case where a single sentence is longer than max_chars (unlikely but possible)
                chunks.append({
                    "index": chunk_index,
                    "text": sentence.strip()
                })
                chunk_index += 1
                current_chunk = ""
        else:
            current_chunk += sentence
            
    if current_chunk:
        chunks.append({
            "index": chunk_index,
            "text": current_chunk.strip()
        })
        
    return chunks

def send_webhook(payload):
    """
    Sends payload to n8n webhook.
    """
    webhook_url = os.getenv('N8N_WEBHOOK_URL')
    if not webhook_url:
        raise Exception("未設定 N8N_WEBHOOK_URL 環境變數")
        
    try:
        response = requests.post(webhook_url, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        raise Exception(f"Webhook 發送失敗: {str(e)}")

def process_video(url):
    """
    Orchestrates the entire process.
    Returns a result dict or raises Exception.
    """
    print(f"正在處理: {url}")
    
    # 1. Metadata
    metadata = get_video_metadata(url)
    
    # 2. Transcript
    transcript_data, lang = get_transcript(metadata['id'])
    
    # 3. Chunking
    chunks = chunk_transcript(transcript_data)
    
    # 4. Payload
    payload = {
        "video_id": metadata['id'],
        "url": url,
        "title": metadata['title'],
        "channel": metadata['channel'],
        "chunks": chunks,
        "total_chunks": len(chunks),
        "metadata": {
            "captured_at": datetime.now().strftime("%Y-%m-%d"),
            "language": lang,
            "upload_date": metadata['upload_date']
        }
    }
    
    # 5. Webhook
    send_webhook(payload)
    
    return {
        "status": "success",
        "title": metadata['title'],
        "chunks_count": len(chunks),
        "language": lang
    }

def generate_qr_code(url):
    """
    Generates a QR code for the given URL and returns it as a base64 string.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def process_qr(url):
    """
    Generates QR code and sends it to n8n.
    """
    print(f"正在生成 QR Code: {url}")
    
    # Generate QR Code
    qr_code_base64 = generate_qr_code(url)
    
    # Payload
    payload = {
        "type": "qrcode",
        "url": url,
        "qr_code_image": qr_code_base64,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Webhook
    send_webhook(payload)
    
    return {
        "status": "success",
        "qr_code": qr_code_base64
    }

def main():
    parser = argparse.ArgumentParser(description='YouTube Transcript Fetcher for n8n')
    parser.add_argument('url', help='YouTube Video URL')
    args = parser.parse_args()
    
    try:
        result = process_video(args.url)
        print(f"成功: 已處理影片 '{result['title']}' 並發送 {result['chunks_count']} 個區塊至 n8n")
    except Exception as e:
        print(f"錯誤: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
