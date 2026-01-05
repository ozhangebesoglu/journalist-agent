"""
Keep Alive - Render.com için HTTP sunucu

Render.com "Web Service" modunda çalışırken uygulamanın
bir HTTP portu dinlemesini bekler. Bu modül sahte bir
web sunucusu başlatarak Render'ın botu kapatmasını engeller.
"""

import os
from flask import Flask, jsonify
from threading import Thread
from datetime import datetime

app = Flask(__name__)

# Bot başlangıç zamanı
START_TIME = datetime.now()


@app.route('/')
def home():
    """Ana sayfa - bot durumu."""
    uptime = datetime.now() - START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return f"""
    <html>
    <head>
        <title>JARVIS Bot Status</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; padding: 40px; }}
            .status {{ background: #16213e; padding: 20px; border-radius: 10px; max-width: 500px; }}
            .online {{ color: #00ff88; }}
            h1 {{ color: #00d4ff; }}
        </style>
    </head>
    <body>
        <div class="status">
            <h1>🤖 JARVIS Bot</h1>
            <p class="online">● Online</p>
            <p>⏱️ Uptime: {hours}h {minutes}m {seconds}s</p>
            <p>📅 Started: {START_TIME.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>🚀 Gazeteci AI Tech Briefing System</p>
        </div>
    </body>
    </html>
    """


@app.route('/health')
def health():
    """Health check endpoint for Render."""
    return jsonify({
        "status": "healthy",
        "uptime_seconds": int((datetime.now() - START_TIME).total_seconds()),
        "service": "jarvis-bot"
    })


@app.route('/status')
def status():
    """Detaylı durum bilgisi."""
    return jsonify({
        "bot": "online",
        "start_time": START_TIME.isoformat(),
        "uptime_seconds": int((datetime.now() - START_TIME).total_seconds()),
        "features": [
            "daily_briefing",
            "ai_assistant", 
            "repo_tracking",
            "voice_assistant",
            "smart_notifications"
        ]
    })


def run():
    """Flask sunucusunu başlat."""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    """Arka planda HTTP sunucusunu başlat."""
    t = Thread(target=run, daemon=True)
    t.start()
    print(f"🌐 Keep-alive sunucu başlatıldı (port: {os.environ.get('PORT', 8080)})")


if __name__ == "__main__":
    # Direkt çalıştırılırsa test için
    print("Starting keep-alive server...")
    run()
