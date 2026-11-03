import os
import logging
import sys
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

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
CHANNEL_PRIVATO = "@KingPronosticiVIP"

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
            [InlineKeyboardButton("🎯 Schedina 100% (Multipla)", callback_data="btn_schedina_100"), InlineKeyboardButton("📊 Schedina 70% (Multipla)", callback_data="btn_schedina_70")],
            [InlineKeyboardButton("📈 Schedina 50% (Multipla)", callback_data="btn_schedina_50"), InlineKeyboardButton("💣 Bomba Schedina (Multipla)", callback_data="btn_schedina_bomba")],
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

# --- 4 SCHEDINE MULTIPLE SEPARATE (CON PIÙ PARTITE E VINCITE CONSISTENTI) ---
async def genera_schedina_singola(tipo, chat_id=1220916735):
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

    while len(match_trovati) < 12:
        match_trovati.append(f"Match di cartello #{len(match_trovati)+1}")

    u_data = get_user_data(chat_id)
    bankroll = u_data["bankroll"]

    if tipo == "100":
        p1, p2, p3 = match_trovati[0], match_trovati[1], match_trovati[2]
        quota_totale = 2.55
        stake = round(bankroll * 0.05, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"🎯 **SCHEDINA MULTIPLA 100% (Alta Affidabilità) - {oggi_ita}**\n\n"
            f"1️⃣ ⚽ {p1} -> **Over 1.5**\n"
            f"2️⃣ ⚽ {p2} -> **Segna Goal**\n"
            f"3️⃣ ⚽ {p3} -> **1X**\n\n"
            f"📊 Quota Totale Multipla: **{quota_totale}**\n"
            f"💰 Puntata Consigliata (5%): **{stake}€**\n"
            f"🏆 **VINCITA POTENZIALE: {vincita}€**\n\n"
            "⚠️ _Gioca responsabilmente._"
        )
    elif tipo == "70":
        p1, p2, p3, p4 = match_trovati[3], match_trovati[4], match_trovati[5], match_trovati[6]
        quota_totale = 5.20
        stake = round(bankroll * 0.04, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"📊 **SCHEDINA MULTIPLA 70% (Alta Probabilità) - {oggi_ita}**\n\n"
            f"1️⃣ ⚽ {p1} -> **Gol / Over 2.5**\n"
            f"2️⃣ ⚽ {p2} -> **1X + Over 1.5**\n"
            f"3️⃣ ⚽ {p3} -> **Over 1.5**\n"
            f"4️⃣ ⚽ {p4} -> **Gol**\n\n"
            f"📊 Quota Totale Multipla: **{quota_totale}**\n"
            f"💰 Puntata Consigliata (4%): **{stake}€**\n"
            f"🏆 **VINCITA POTENZIALE: {vincita}€**\n\n"
            "⚠️ _Gioca responsabilmente._"
        )
    elif tipo == "50":
        p1, p2, p3, p4 = match_trovati[7], match_trovati[8], match_trovati[9], match_trovati[10]
        quota_totale = 12.50
        stake = round(bankroll * 0.03, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"📈 **SCHEDINA MULTIPLA 50% (Rischio Calcolato) - {oggi_ita}**\n\n"
            f"1️⃣ ⚽ {p1} -> **1 2T / Combo**\n"
            f"2️⃣ ⚽ {p2} -> **Over 2.5**\n"
            f"3️⃣ ⚽ {p3} -> **Gol + Over 1.5**\n"
            f"4️⃣ ⚽ {p4} -> **X2 + Over 1.5**\n\n"
            f"📊 Quota Totale Multipla: **{quota_totale}**\n"
            f"💰 Puntata Consigliata (3%): **{stake}€**\n"
            f"🏆 **VINCITA POTENZIALE: {vincita}€**\n\n"
            "⚠️ _Gioca responsabilmente._"
        )
    elif tipo == "bomba":
        p1, p2, p3, p4 = match_trovati[11], match_trovati[0], match_trovati[3], match_trovati[5]
        quota_totale = 35.00
        stake = round(bankroll * 0.02, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"💣 **BOMBA SCHEDINA MULTIPLA (Quota Pazzesca) - {oggi_ita}**\n\n"
            f"1️⃣ ⚽ {p1} -> **Risultato Esatto / Combo**\n"
            f"2️⃣ ⚽ {p2} -> **X Primo Tempo**\n"
            f"3️⃣ ⚽ {p3} -> **Multigol 2-3**\n"
            f"4️⃣ ⚽ {p4} -> **Ribaltone / Gol Gol**\n\n"
            f"📊 Quota Totale Multipla: **{quota_totale}**\n"
            f"💰 Puntata Consigliata (2% - Prudente): **{stake}€**\n"
            f"🏆 **VINCITA POTENZIALE CONSISTENTE: {vincita}€**\n\n"
            "⚠️ _Gioca responsabilmente._"
        )
    return "Seleziona una schedina valida."

async def genera_testo_partite_oggi():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    partite_list = []
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            for match in data.get("matches", [])[:10]:
                home = match.get('homeTeam', {}).get('name', 'Casa')
                away = match.get('awayTeam', {}).get('name', 'Ospiti')
                comp = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                score = match.get('score', {}).get('fullTime', {})
                hg = score.get('home', 0) if score.get('home') is not None else 0
                ag = score.get('away', 0) if score.get('away') is not None else 0
                
                if status == 'FINISHED':
                    stato_str = f"🏁 Terminata ({hg} - {ag})"
                elif status in ['IN_PLAY', 'PAUSED']:
                    stato_str = f"🔴 LIVE ({hg} - {ag})"
                else:
                    stato_str = "⏳ Programmata"
                    
                partite_list.append(f"🏆 {comp}\n⚽ {home} vs {away}\n📌 Stato: {stato_str}\n-----------------------------------")
    except Exception as e:
        logging.error(f"Errore recupero partite: {e}")

    testo = f"📅 PARTITE DEL GIORNO ({oggi_ita})\n\n"
    if partite_list:
        testo += "\n".join(partite_list)
    else:
        testo += "Nessuna partita disponibile per la data odierna."
    
    return testo

async def genera_testo_live():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    segnali_live = []
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            for match in data.get("matches", []):
                if match.get('status') in ['IN_PLAY', 'PAUSED']:
                    home = match.get('homeTeam', {}).get('name', 'Casa')
                    away = match.get('awayTeam', {}).get('name', 'Ospiti')
                    comp = match.get('competition', {}).get('name', 'Campionato')
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0)
                    ag = score.get('away', 0)
                    
                    segnali_live.append(
                        f"🔴 **SEGNALE LIVE DA GIOCARE!** ({comp})\n"
                        f"⚽ {home} {hg} - {ag} {away}\n"
                        f"💡 **Cosa scommettere in live:** Valutare Over 0.5 / 1.5 o Gol in base all'andamento in campo.\n"
                        f"-----------------------------------\n"
                    )
    except Exception as e:
        logging.error(f"Errore Live: {e}")

    if not segnali_live:
        segnali_live.append("Nessuna partita in corso con segnali live attivi in questo momento.")

    return f"🚨 MONITORAGGIO MATCH LIVE ({oggi_ita}) 🚨\n\n" + "\n".join(segnali_live)

def background_live_notifier(bot_app):
    import asyncio
    while True:
        try:
            time.sleep(900)
            oggi = datetime.now().strftime('%Y-%m-%d')
            url = f"https://api.football-data.org/v4/matches?date={oggi}"
            data = fetch_from_football_api(url)
            if data and "matches" in data:
                for match in data.get("matches", []):
                    if match.get('status') in ['IN_PLAY', 'PAUSED']:
                        home = match.get('homeTeam', {}).get('name', 'Casa')
                        away = match.get('awayTeam', {}).get('name', 'Ospiti')
                        score = match.get('score', {}).get('fullTime', {})
                        hg = score.get('home', 0)
                        ag = score.get('away', 0)
                        
                        notif_text = (
                            f"🚨 **NOTIFICA LIVE: COSA SCOMMETTERE ORA!** 🚨\n\n"
                            f"⚽ **{home} {hg} - {ag} {away}**\n"
                            f"🔥 Match caldo in corso! Ottima occasione per puntare in live.\n"
                            f"Controlla le quote sul tuo bookmaker!"
                        )
                        
                        utenti = get_all_users()
                        for uid in utenti:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    bot_app.bot.send_message(chat_id=uid, text=notif_text),
                                    bot_app.loop
                                )
                            except Exception:
                                pass
                        break
        except Exception as e:
            logging.error(f"Errore nel thread notifiche live: {e}")

async def genera_testo_fonti():
    return (
        "🔍 **SITI E FONTI DI ANALISI PROFESSIONALE** 📊\n\n"
        "1. **FBref** (Statistiche avanzate e xG): https://fbref.com/\n"
        "2. **Understat** (Expected Goals): https://understat.com/\n"
        "3. **WhoScored**: https://it.whoscored.com/\n"
        "4. **Transfermarkt**: https://www.transfermarkt.it/\n"
        "5. **Sofascore**: https://www.sofascore.com/it/"
    )

async def mostra_bankroll_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        
        chat_id = query.message.chat_id
        u_data = get_user_data(chat_id)
        bank = u_data["bankroll"]
        
        stake_1 = round(bank * 0.02, 2)
        stake_2 = round(bank * 0.05, 2)
        
        testo = (
            f"📊 **GESTIONE DEL BANKROLL**\n\n"
            f"💰 Budget attuale: **{bank}€**\n"
            f"• Puntata Prudente (2%): **{stake_1}€**\n"
            f"• Puntata Standard (5%): **{stake_2}€**\n\n"
            "Usa /setbankroll <valore> per aggiornare il budget."
        )
        keyboard = [[InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]]
        
        try:
            await query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
