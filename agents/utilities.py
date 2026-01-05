"""
Utilities - Çeşitli yardımcı araçlar

Özellikler:
    - Hava durumu
    - Kripto/Döviz fiyatları
    - URL kısaltma
    - QR kod oluşturma
    - Pomodoro timer
    - Export (JSON/CSV)
    - Kullanım istatistikleri
    - Hedef takip
"""

import os
import json
import csv
import io
import base64
import requests
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

from agents import db

load_dotenv()

# ============ Hava Durumu ============

def get_weather(city: str) -> str:
    """Hava durumu bilgisi al (wttr.in API - ücretsiz, API key gerektirmez)."""
    try:
        # wttr.in API - basit ve ücretsiz
        resp = requests.get(
            f"https://wttr.in/{city}?format=j1",
            timeout=10,
            headers={"Accept-Language": "tr"}
        )

        if resp.status_code != 200:
            return f"Hava durumu alınamadı: {city}"

        data = resp.json()
        current = data.get("current_condition", [{}])[0]
        location = data.get("nearest_area", [{}])[0]

        city_name = location.get("areaName", [{}])[0].get("value", city)
        country = location.get("country", [{}])[0].get("value", "")

        temp = current.get("temp_C", "?")
        feels_like = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        desc = current.get("lang_tr", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", ""))
        wind = current.get("windspeedKmph", "?")

        # Emoji seç
        weather_code = int(current.get("weatherCode", 0))
        if weather_code in [113]:
            emoji = "☀️"
        elif weather_code in [116, 119, 122]:
            emoji = "⛅"
        elif weather_code in [176, 263, 266, 293, 296, 299, 302, 305, 308]:
            emoji = "🌧️"
        elif weather_code in [179, 182, 185, 227, 230, 323, 326, 329, 332, 335, 338, 350, 368, 371, 374, 377]:
            emoji = "🌨️"
        elif weather_code in [200, 386, 389, 392, 395]:
            emoji = "⛈️"
        else:
            emoji = "🌤️"

        text = f"{emoji} {city_name}, {country}\n"
        text += "━━━━━━━━━━━━━━━━\n\n"
        text += f"🌡️ Sıcaklık: {temp}°C\n"
        text += f"🤔 Hissedilen: {feels_like}°C\n"
        text += f"💧 Nem: %{humidity}\n"
        text += f"💨 Rüzgar: {wind} km/h\n"
        text += f"📝 {desc}"

        return text
    except Exception as e:
        return f"Hava durumu hatası: {str(e)}"


# ============ Kripto & Döviz ============

def get_crypto_price(symbol: str) -> str:
    """Kripto para fiyatı al (CoinGecko API)."""
    try:
        symbol = symbol.lower()

        # Yaygın kısaltmalar
        symbol_map = {
            "btc": "bitcoin",
            "eth": "ethereum",
            "bnb": "binancecoin",
            "xrp": "ripple",
            "ada": "cardano",
            "doge": "dogecoin",
            "sol": "solana",
            "dot": "polkadot",
            "matic": "matic-network",
            "avax": "avalanche-2"
        }

        coin_id = symbol_map.get(symbol, symbol)

        resp = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": "usd,try",
                "include_24hr_change": "true"
            },
            timeout=10
        )

        if resp.status_code != 200:
            return f"Fiyat alınamadı: {symbol}"

        data = resp.json()

        if coin_id not in data:
            return f"Coin bulunamadı: {symbol}"

        coin = data[coin_id]
        usd = coin.get("usd", 0)
        try_price = coin.get("try", 0)
        change = coin.get("usd_24h_change", 0)

        emoji = "📈" if change >= 0 else "📉"
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

        text = f"💰 {symbol.upper()}\n"
        text += "━━━━━━━━━━━━━\n\n"
        text += f"💵 ${usd:,.2f}\n"
        text += f"₺ {try_price:,.2f} TRY\n"
        text += f"{emoji} 24s: {change_str}"

        return text
    except Exception as e:
        return f"Kripto hatası: {str(e)}"


def get_exchange_rate(currency: str) -> str:
    """Döviz kuru al."""
    try:
        currency = currency.upper()

        resp = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{currency}",
            timeout=10
        )

        if resp.status_code != 200:
            return f"Kur alınamadı: {currency}"

        data = resp.json()
        rates = data.get("rates", {})

        try_rate = rates.get("TRY", 0)
        usd_rate = rates.get("USD", 0)
        eur_rate = rates.get("EUR", 0)

        text = f"💱 {currency} Kurları\n"
        text += "━━━━━━━━━━━━━━\n\n"

        if currency == "USD":
            text += f"₺ {try_rate:.2f} TRY\n"
            text += f"€ {eur_rate:.4f} EUR\n"
        elif currency == "TRY":
            text += f"$ {usd_rate:.4f} USD\n"
            text += f"€ {eur_rate:.4f} EUR\n"
        else:
            text += f"$ {usd_rate:.4f} USD\n"
            text += f"₺ {try_rate:.2f} TRY\n"
            text += f"€ {eur_rate:.4f} EUR\n"

        return text
    except Exception as e:
        return f"Döviz hatası: {str(e)}"


# ============ URL Kısaltma ============

def shorten_url(url: str) -> str:
    """URL kısalt (cleanuri.com API)."""
    try:
        resp = requests.post(
            "https://cleanuri.com/api/v1/shorten",
            data={"url": url},
            timeout=10
        )

        if resp.status_code == 200:
            data = resp.json()
            short = data.get("result_url", "")
            return f"🔗 Kısa URL:\n{short}"
        else:
            return "URL kısaltılamadı. Geçerli bir URL girin."
    except Exception as e:
        return f"URL kısaltma hatası: {str(e)}"


# ============ QR Kod ============

def generate_qr_url(text: str) -> str:
    """QR kod URL'i oluştur (goqr.me API)."""
    import urllib.parse
    encoded = urllib.parse.quote(text)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded}"
    return qr_url


# ============ Pomodoro ============

# Pomodoro state (in-memory, basit)
pomodoro_sessions = {}

def start_pomodoro(chat_id: str, minutes: int = 25) -> dict:
    """Pomodoro başlat."""
    end_time = datetime.now() + timedelta(minutes=minutes)

    pomodoro_sessions[chat_id] = {
        "end_time": end_time,
        "duration": minutes,
        "type": "work" if minutes >= 20 else "break"
    }

    return {
        "message": f"🍅 Pomodoro başladı!\n⏱️ {minutes} dakika\n🏁 Bitiş: {end_time.strftime('%H:%M')}",
        "end_time": end_time
    }


def get_pomodoro_status(chat_id: str) -> str:
    """Pomodoro durumu."""
    if chat_id not in pomodoro_sessions:
        return "Aktif pomodoro yok. /pomodoro <dakika> ile başlayın."

    session = pomodoro_sessions[chat_id]
    end_time = session["end_time"]
    remaining = end_time - datetime.now()

    if remaining.total_seconds() <= 0:
        del pomodoro_sessions[chat_id]
        return "🍅 Pomodoro tamamlandı! Mola zamanı."

    mins = int(remaining.total_seconds() // 60)
    secs = int(remaining.total_seconds() % 60)

    return f"🍅 Pomodoro aktif\n⏱️ Kalan: {mins}:{secs:02d}"


def stop_pomodoro(chat_id: str) -> str:
    """Pomodoro durdur."""
    if chat_id in pomodoro_sessions:
        del pomodoro_sessions[chat_id]
        return "🛑 Pomodoro durduruldu."
    return "Aktif pomodoro yok."


def get_finished_pomodoros() -> list:
    """Biten pomodoroları kontrol et."""
    finished = []
    now = datetime.now()

    for chat_id, session in list(pomodoro_sessions.items()):
        if session["end_time"] <= now:
            finished.append({
                "chat_id": chat_id,
                "type": session["type"]
            })
            del pomodoro_sessions[chat_id]

    return finished


# ============ Export ============

def export_bookmarks(chat_id: str, format: str = "json") -> tuple[str, bytes]:
    """Bookmarkları export et."""
    bookmarks = db.get_bookmarks(chat_id, limit=1000)

    if format == "json":
        content = json.dumps(bookmarks, indent=2, ensure_ascii=False)
        return "bookmarks.json", content.encode('utf-8')
    else:  # csv
        output = io.StringIO()
        if bookmarks:
            writer = csv.DictWriter(output, fieldnames=bookmarks[0].keys())
            writer.writeheader()
            writer.writerows(bookmarks)
        return "bookmarks.csv", output.getvalue().encode('utf-8')


def export_notes(chat_id: str, format: str = "json") -> tuple[str, bytes]:
    """Notları export et."""
    notes = db.get_notes(chat_id, limit=1000)

    if format == "json":
        content = json.dumps(notes, indent=2, ensure_ascii=False)
        return "notes.json", content.encode('utf-8')
    else:
        output = io.StringIO()
        if notes:
            writer = csv.DictWriter(output, fieldnames=notes[0].keys())
            writer.writeheader()
            writer.writerows(notes)
        return "notes.csv", output.getvalue().encode('utf-8')


def export_snippets(chat_id: str) -> tuple[str, bytes]:
    """Snippetları export et."""
    snippets = db.get_all_snippets(chat_id)
    content = json.dumps(snippets, indent=2, ensure_ascii=False)
    return "snippets.json", content.encode('utf-8')


def export_all(chat_id: str) -> tuple[str, bytes]:
    """Tüm verileri export et."""
    data = {
        "bookmarks": db.get_bookmarks(chat_id, limit=1000),
        "notes": db.get_notes(chat_id, limit=1000),
        "snippets": db.get_all_snippets(chat_id),
        "watches": db.get_watched_repos(chat_id),
        "alerts": db.get_keyword_alerts(chat_id),
        "exported_at": datetime.now().isoformat()
    }
    content = json.dumps(data, indent=2, ensure_ascii=False)
    return "gazeteci_export.json", content.encode('utf-8')


# ============ İstatistikler ============

def get_user_stats(chat_id: str) -> str:
    """Kullanıcı istatistikleri."""
    bookmarks = db.get_bookmarks(chat_id, limit=1000)
    notes = db.get_notes(chat_id, limit=1000)
    snippets = db.get_all_snippets(chat_id)
    watches = db.get_watched_repos(chat_id)
    alerts = db.get_keyword_alerts(chat_id)
    reminders = db.get_user_reminders(chat_id)
    history = db.get_chat_history(chat_id, limit=100)

    text = "📊 Kullanım İstatistiklerin\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += f"🔖 Bookmark: {len(bookmarks)}\n"
    text += f"📝 Not: {len(notes)}\n"
    text += f"📋 Snippet: {len(snippets)}\n"
    text += f"👀 Takip: {len(watches)} repo\n"
    text += f"🔔 Alert: {len(alerts)} keyword\n"
    text += f"⏰ Hatırlatıcı: {len(reminders)} bekliyor\n"
    text += f"💬 Sohbet: {len(history)} mesaj\n"

    return text


# ============ Hedef Takip ============

def add_goal(chat_id: str, goal: str) -> str:
    """Hedef ekle (not olarak kaydediliyor, özel prefix ile)."""
    goal_text = f"[GOAL] {goal} | Progress: 0%"
    db.add_note(chat_id, goal_text)
    return f"🎯 Hedef eklendi: {goal}\n\nİlerleme için: /progress <hedef-no> <yüzde>"


def get_goals(chat_id: str) -> str:
    """Hedefleri listele."""
    notes = db.get_notes(chat_id, limit=100)
    goals = [n for n in notes if n['content'].startswith('[GOAL]')]

    if not goals:
        return "Hedef yok. /goal <hedef> ile ekleyin."

    text = "🎯 Hedefler\n━━━━━━━━━━━\n\n"
    for i, g in enumerate(goals, 1):
        content = g['content'].replace('[GOAL] ', '')
        text += f"{i}. {content}\n"

    return text


if __name__ == "__main__":
    print(get_weather("istanbul"))
    print(get_crypto_price("btc"))
