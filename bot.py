import os
import logging
import sys
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Configurazione Logging pulito
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKENS = [
    "9109962875:AAEfQyasxkN8Ddqm8I0PEmD3SwwgMBMkw3Y",
    "8987770671:AAHZ5vFUWWT2t83Dbxr6wCeVyNrMP2zEQHM"
]
TOKEN = TOKENS[0]

FOOTBALL_API_KEYS = [
    "be001fd3625a4f84b61b28e26ba101b2",
    "A7IauxgMoOQxH4XXRH8Eyflf16KC5OzoJ4tGb5ORCTMwqDg5VHpDaKadrl0O"
]

ADMIN_USERNAME = "Theincisboss" 
ADMIN_CHAT_ID = 1220916735  

# ⚠️ IL TUO CANALE PRIVATO VIP (Ricordati di rendere il bot Amministratore del canale!)
CHANNEL_PRIVATO = "@KingPronosticiVIP"

# --- DATABASE LOCALE (SQLite SICURO) ---
def init_db():
    try:
        conn = sqlite3.connect("bot_database.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                is_vip INTEGER DEFAULT 0,
                expiry_date TEXT,
                bankroll REAL DEFAULT 100.0
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Errore init_db: {e}")

init_db()

def save_or_update_user(chat_id, username):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO users (chat_id, username, is_vip, bankroll) VALUES (?, ?, 0, 100.0)", (chat_id, username or "Utente"))
            conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Errore save_or_update_user: {e}")

def get_user_data(chat_id):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT is_vip, expiry_date, bankroll FROM users WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            is_vip = row[0]
            expiry_date_str = row[1]
            bankroll = row[2]
            
            if is_vip == 1 and expiry_date_str:
                try:
                    expiry_dt = datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S')
                    if datetime.now() > expiry_dt:
                        set_user_vip_db(chat_id, 0, None)
                        is_vip = 0
                except Exception:
                    pass
                    
            return {"is_vip": is_vip, "bankroll": bankroll}
    except Exception as e:
        logging.error(f"Errore get_user_data: {e}")
    return {"is_vip": 0, "bankroll": 100.0}

def update_user_bankroll(chat_id, amount):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET bankroll = ? WHERE chat_id = ?", (amount, chat_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Errore update_user_bankroll: {e}")

def set_user_vip_db(chat_id, status=1, expiry_dt=None):
    try:
        conn = sqlite3.connect("bot_database.db", timeout=20)
        cursor = conn.cursor()
        expiry_str = expiry_dt.strftime('%Y-%m-%d %H:%M:%S') if expiry_dt else None
        cursor.execute("UPDATE users SET is_vip = ?, expiry_date = ? WHERE chat_id = ?", (status, expiry_str, chat_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Errore set_user_vip_db: {e}")

def get_all_users():
    try:
        conn = sqlite3.connect("bot_database.db", timeout=20)
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []

def fetch_from_football_api(endpoint_url):
    def query_key(api_key):
        headers = {"X-Auth-Token": api_key}
        try:
            response = requests.get(endpoint_url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=len(FOOTBALL_API_KEYS)) as executor:
        futures = [executor.submit(query_key, key) for key in FOOTBALL_API_KEYS]
        for future in futures:
            res = future.result()
            if res:
                return res
    return None

# --- WEB SERVER PER RENDER (KEEP-ALIVE / UPTIMEROBOT) ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is online and running 24/7!")
        
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), SimpleHandler)
        server.serve_forever()
    except Exception as e:
        logging.error(f"Errore server web: {e}")

# --- MENU PRINCIPALE ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        if not chat:
            return
            
        save_or_update_user(chat.id, chat.username or "Utente")
        user_info = get_user_data(chat.id)

        status_vip = "👑 VIP Attivo" if user_info["is_vip"] == 1 else "🔒 Standard (Free)"

        welcome_text = (
            f"🤖 BENVENUTO SU KING PRONOSTICI PRO ⚽\n\n"
            f"Stato Account: {status_vip}\n"
            f"Budget (Bankroll): {user_info['bankroll']}€\n\n"
            "Seleziona un'opzione dal menu sottostante:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🔥 Schedina Bomba & Percentuali", callback_data="btn_schedina_bomba")],
            [InlineKeyboardButton("📅 Partite e Risultati Oggi", callback_data="btn_partite_oggi")],
            [InlineKeyboardButton("🔴 Monitoraggio LIVE", callback_data="btn_live_radar")],
            [InlineKeyboardButton("📊 Gestione Bankroll & Stake", callback_data="btn_bankroll")],
            [InlineKeyboardButton("🔍 Fonti e Siti di Analisi (xG)", callback_data="btn_fonti_analisi")],
            [InlineKeyboardButton("💎 Diventa VIP / Attiva Servizio", callback_data="btn_vip")]
        ]
        if user_info["is_vip"] == 1:
            keyboard.append([InlineKeyboardButton("🔗 Ottieni Link Canale Privato", callback_data="btn_get_link")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        elif update.callback_query:
            query = update.callback_query
            try:
                await query.answer()
            except Exception:
                pass
            try:
                await query.message.edit_text(welcome_text, reply_markup=reply_markup)
            except Exception:
                await query.message.reply_text(welcome_text, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Errore in start: {e}")

# --- SCHEDINA BOMBA & PERCENTUALI ---
async def genera_testo_schedina_bomba():
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={datetime.now().strftime('%Y-%m-%d')}"
    
    match_trovati = []
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            for match in data.get("matches", []):
                home = match.get('homeTeam', {}).get('name', 'Casa')
                away = match.get('awayTeam', {}).get('name', 'Ospiti')
                match_trovati.append(f"{home} vs {away}")
    except Exception:
        pass

    m1 = match_trovati[0] if len(match_trovati) > 0 else "Real Madrid vs Barcellona"
    m2 = match_trovati[1] if len(match_trovati) > 1 else "Inter vs Milan"
    m3 = match_trovati[2] if len(match_trovati) > 2 else "Manchester City vs Arsenal"
    m4 = match_trovati[3] if len(match_trovati) > 3 else "Bayern Monaco vs Dortmund"

    return (
        f"🔥 **SCHEDINA DEL GIORNO & PERCENTUALI ({oggi_ita})** 🔥\n\n"
        f"🎯 **Quota 100% (Affidabilità Massima):**\n"
        f"⚽ {m1} -> **Over 1.5 / Segna Goal**\n\n"
        f"📊 **Quota 70% (Alta Probabilità):**\n"
        f"⚽ {m2} -> **Gol / Over 2.5**\n\n"
        f"📈 **Quota 50% (Rischio Calcolato):**\n"
        f"⚽ {m3} -> **1X + Over 1.5**\n\n"
        f"💣 **LA BOMBA DEL GIORNO (Quota Alta):**\n"
        f"⚽ {m4} -> **Risultato Esatto / Combo 1X + Goal**\n\n"
        "⚠️ _Gioca responsabilmente._"
    )

# --- PARTITE E CALENDARIO LIVE ---
async def genera_testo_partite_oggi():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    partite_list = []
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            for match in data.
