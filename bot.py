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
    except Exception as e:
        logging.error(f"Errore get_all_users: {e}")
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
            f"👑 **KING PRONOSTICI PRO** ⚽\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 **Stato Account:** {status_vip}\n"
            f"💰 **Bankroll Attuale:** {user_info['bankroll']}€\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            "Seleziona un'opzione dal pannello di controllo:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🎯 Schedina 100% (Multipla)", callback_data="btn_schedina_100"), InlineKeyboardButton("📊 Schedina 70% (Multipla)", callback_data="btn_schedina_70")],
            [InlineKeyboardButton("📈 Schedina 50% (Multipla)", callback_data="btn_schedina_50"), InlineKeyboardButton("💣 Bomba Schedina (Multipla)", callback_data="btn_schedina_bomba")],
            [InlineKeyboardButton("📅 Tutte le Partite di Oggi", callback_data="btn_partite_oggi")],
            [InlineKeyboardButton("🔴 Monitoraggio LIVE", callback_data="btn_live_radar")],
            [InlineKeyboardButton("📊 Gestione Bankroll & Stake", callback_data="btn_bankroll")],
            [InlineKeyboardButton("🔍 Fonti e Siti di Analisi (xG)", callback_data="btn_fonti_analisi")],
            [InlineKeyboardButton("💎 Diventa VIP / Attiva Servizio", callback_data="btn_vip")]
        ]
        if user_info["is_vip"] == 1:
            keyboard.append([InlineKeyboardButton("🔗 Ottieni Link Canale Privato", callback_data="btn_get_link")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
        elif update.callback_query:
            query = update.callback_query
            try:
                await query.answer()
            except Exception:
                pass
            try:
                await query.message.edit_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
            except Exception:
                await query.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Errore in start: {e}")

def valuta_esito_partita(match_obj, tipo_giocata):
    status = match_obj.get('status', 'SCHEDULED')
    score = match_obj.get('score', {}).get('fullTime', {})
    hg = score.get('home', 0) if score.get('home') is not None else 0
    ag = score.get('away', 0) if score.get('away') is not None else 0
    
    if status not in ['FINISHED', 'IN_PLAY', 'PAUSED']:
        return f"⏳ [In Programma] ({hg}-{ag})"

    total_goals = hg + ag
    if status == 'FINISHED':
        if "Over" in tipo_giocata:
            try:
                 soglia = float(tipo_giocata.split("Over")[1].split()[0])
                 if total_goals > soglia:
                     return f"✅ **VINTA** ({hg}-{ag} FINALE)"
                 else:
                     return f"❌ **PERSA** ({hg}-{ag} FINALE)"
            except Exception:
                pass
        if "Gol" in tipo_giocata or "Goal" in tipo_giocata:
            if hg > 0 and ag > 0:
                return f"✅ **VINTA** ({hg}-{ag} FINALE)"
            else:
                return f"❌ **PERSA** ({hg}-{ag} FINALE)"
        return f"🏁 [Terminata] ({hg}-{ag})"
    else:
        return f"🔴 **LIVE** ({hg}-{ag} in corso)"

async def genera_schedina_singola(tipo, chat_id=1220916735):
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={datetime.now().strftime('%Y-%m-%d')}"
    
    matches_api = []
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            matches_api = data.get("matches", [])
    except Exception:
        pass

    u_data = get_user_data(chat_id)
    bankroll = u_data["bankroll"]

    def get_match_info(index, fallback_home, fallback_away, tipologia):
        if index < len(matches_api):
            m = matches_api[index]
            h = m.get('homeTeam', {}).get('name', 'Casa')
            a = m.get('awayTeam', {}).get('name', 'Ospiti')
            stato = valuta_esito_partita(m, tipologia)
            return f"• ⚽ `{h} vs {a}`\n  └ 📌 Pronostico: *{tipologia}*\n  └ ⚡ Esito: {stato}"
        else:
            return f"• ⚽ `{fallback_home} vs {fallback_away}`\n  └ 📌 Pronostico: *{tipologia}*\n  └ ⚡ Esito: ⏳ [In Programma]"

    if tipo == "100":
        m1 = get_match_info(0, "Real Madrid", "Barcellona", "Over 1.5")
        m2 = get_match_info(1, "Inter", "Milan", "Segna Goal")
        m3 = get_match_info(2, "Manchester City", "Arsenal", "1X")
        p4 = get_match_info(3, "Bayern Monaco", "Dortmund", "Multigol 1-4")
        quota_totale = 3.85
        stake = round(bankroll * 0.05, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"🎯 **VIP MASTER MULTIPLA 100%**\n"
            f"📅 Data Analisi: `{oggi_ita}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{m1}\n\n"
            f"{m2}\n\n"
            f"{m3}\n\n"
            f"{p4}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Quota Totale:** `@{quota_totale}`\n"
            f"💰 **Stake Consigliato (5%):** `{stake}€`\n"
            f"🏆 **VINCITA POTENZIALE:** `✨ {vincita}€ ✨`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ _Servizio statistico ad alta affidabilità._"
        )
    elif tipo == "70":
        m1 = get_match_info(4, "Napoli", "Juventus", "Gol / Over 2.5")
        m2 = get_match_info(5, "Roma", "Lazio", "1X + Over 1.5")
        m3 = get_match_info(6, "PSG", "Marsiglia", "Over 1.5")
        m4 = get_match_info(7, "Liverpool", "Chelsea", "Gol")
        m5 = get_match_info(8, "Bayer Leverkusen", "Lipsia", "Over 0.5 1° Tempo")
        quota_totale = 7.90
        stake = round(bankroll * 0.04, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"📊 **PRO MULTIPLA 70% (ALTA PROBABILITÀ)**\n"
            f"📅 Data Analisi: `{oggi_ita}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{m1}\n\n"
            f"{m2}\n\n"
            f"{m3}\n\n"
            f"{m4}\n\n"
            f"{m5}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Quota Totale:** `@{quota_totale}`\n"
            f"💰 **Stake Consigliato (4%):** `{stake}€`\n"
            f"🏆 **VINCITA POTENZIALE:** `✨ {vincita}€ ✨`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ _Gestione professionale del bankroll._"
        )
    elif tipo == "50":
        m1 = get_match_info(9, "Porto", "Benfica", "Combo 1X + Goal")
        m2 = get_match_info(10, "Ajax", "Feyenoord", "Over 3.5")
        m3 = get_match_info(11, "Galatasaray", "Fenerbahce", "Parziale/Finale 1/1")
        m4 = get_match_info(0, "Atletico Madrid", "Valencia", "Multigol 2-4")
        m5 = get_match_info(1, "Villarreal", "Real Sociedad", "Rigore Si")
        quota_totale = 18.50
        stake = round(bankroll * 0.03, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"📈 **EXPERT MULTIPLA 50% (RISCHIO CALCOLATO)**\n"
            f"📅 Data Analisi: `{oggi_ita}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{m1}\n\n"
            f"{m2}\n\n"
            f"{m3}\n\n"
            f"{m4}\n\n"
            f"{m5}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Quota Totale:** `@{quota_totale}`\n"
            f"💰 **Stake Consigliato (3%):** `{stake}€`\n"
            f"🏆 **VINCITA POTENZIALE:** `🔥 {vincita}€ 🔥`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ _Selezioni avanzate con studio xG._"
        )
    elif tipo == "bomba":
        m1 = get_match_info(2, "Tottenham", "Aston Villa", "Risultato Esatto")
        m2 = get_match_info(3, "Atalanta", "Fiorentina", "X Parziale / 1 Finale")
        m3 = get_match_info(4, "Monaco", "Lione", "Gol + Over 3.5")
        m4 = get_match_info(5, "Stoccarda", "Wolfsburg", "Combo 2 + Over 1.5")
        m5 = get_match_info(6, "Betis", "Sevilla", "Espulsione Si")
        quota_totale = 55.00
        stake = round(bankroll * 0.02, 2)
        vincita = round(stake * quota_totale, 2)
        return (
            f"💣 **SUPER BOMBA MULTIPLA (QUOTA PAZZESCA)**\n"
            f"📅 Data Analisi: `{oggi_ita}`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"{m1}\n\n"
            f"{m2}\n\n"
            f"{m3}\n\n"
            f"{m4}\n\n"
            f"{m5}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **Quota Totale:** `@{quota_totale}`\n"
            f"💰 **Stake Consigliato (2% - Prudente):** `{stake}€`\n"
            f"🏆 **VINCITA POTENZIALE CONSISTENTE:** `🚀 {vincita}€ 🚀`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ _Tentativo a quota alta, puntare il minimo._"
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
            for match in data.get("matches", []):
                home = match.get('homeTeam', {}).get('name', 'Casa')
                away = match.get('awayTeam', {}).get('name', 'Ospiti')
                comp = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                score = match.get('score', {}).get('fullTime', {})
                hg = score.get('home', 0) if score.get('home') is not None else 0
                ag = score.get('away', 0) if score.get('away') is not None else 0
                
                if status == 'FINISHED':
                    stato_str = f"🏁 [Terminata] ({hg} - {ag})"
                elif status in ['IN_PLAY', 'PAUSED']:
                    stato_str = f"🔴 **LIVE IN CORSO** ({hg} - {ag})"
                else:
                    stato_str = "⏳ [Programmata]"
                    
                partite_list.append(f"🏆 `{comp}`\n⚽ **{home} vs {away}**\n📌 Stato: {stato_str}\n───────────────────────────")
    except Exception as e:
        logging.error(f"Errore recupero tutte le partite: {e}")

    testo = f"📅 **CALENDARIO COMPLETO MATCH ({oggi_ita})**\n━━━━━━━━━━━━━━━━━━━\n\n"
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
                        f"🔴 **SEGNALE LIVE CALDO!**\n"
                        f"🏆 `{comp}`\n"
                        f"⚽ **{home} {hg} - {ag} {away}**\n"
                        f"💡 _Consiglio:_ Valutare Over in live o Goal in base al pressing.\n"
                        f"───────────────────────────"
                    )
    except Exception as e:
        logging.error(f"Errore Live: {e}")

    if not segnali_live:
        segnali_live.append("Nessuna partita in corso con segnali live attivi in questo momento.")

    return f"🚨 **RADAR MONITORAGGIO LIVE ({oggi_ita})** 🚨\n━━━━━━━━━━━━━━━━━━━\n\n" + "\n".join(segnali_live)

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
                            f"🚨 **NOTIFICA LIVE: OCCASIONE DA GOL!** 🚨\n\n"
                            f"⚽ **{home} {hg} - {ag} {away}**\n"
                            f"🔥 Match caldissimo! Apri il tuo bookmaker e valuta una giocata live.\n"
                        )
                        
                        utenti = get_all_users()
                        for uid in utenti:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    bot_app.bot.send_message(chat_id=uid, text=notif_text, parse_mode="Markdown"),
                                    bot_app.loop
                                )
                            except Exception:
                                pass
                        break
        except Exception as e:
            logging.error(f"Errore nel thread notifiche live: {e}")

async def genera_testo_fonti():
    return (
        "🔍 **FONTI DI ANALISI STATISTICA (xG)**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1. **FBref** (Metriche avanzate): `https://fbref.com/`\n"
        "2. **Understat** (Expected Goals): `https://understat.com/`\n"
        "3. **WhoScored** (Heatmap & Rating): `https://it.whoscored.com/`\n"
        "4. **Transfermarkt** (Valori di mercato): `https://www.transfermarkt.it/`\n"
        "5. **Sofascore** (Copertura live): `https://www.sofascore.com/it/`"
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
            f"📊 **GESTIONE BANKROLL & STAKE**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💰 **Budget Attuale:** `{bank}€`\n\n"
            f"• 🛡️ Puntata Prudente (2%): `{stake_1}€`\n"
            f"• ⚖️ Puntata Standard (5%): `{stake_2}€`\n\n"
            "Usa `/setbankroll <valore>` per aggiornare il budget."
        )
        keyboard = [[InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]]
        
        try:
            await query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception:
            await query.message.reply_text(testo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Errore bankroll menu: {e}")

async def set_bankroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if context.args:
            valore = float(context.args[0])
            update_user_bankroll(chat_id, valore)
            await update.message.reply_text(f"✅ Bankroll aggiornato con successo a `{valore}€`!", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Specifica il valore. Esempio: `/setbankroll 150`", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Valore non valido. Usa es: `/setbankroll 150`", parse_mode="Markdown")

async def mostra_info_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        
        testo = (
            "💎 **AREA ABBONAMENTO VIP EXCLUSIVE**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "• Abbonamento Mensile: `19.99€`\n"
            "• Abbonamento Annuale: `99.00€`\n\n"
            "🔄 **Procedura di Attivazione:**\n"
            "1. Contatta l'amministratore per concordare il pagamento.\n"
            "2. Invia la ricevuta in chat: verrai abilitato immediatamente e riceverai il link d'invito al canale VIP!"
        )
        keyboard = [
            [InlineKeyboardButton("✉️ Contatta Admin per Pagare", url=f"https://t.me/{ADMIN_USERNAME}")],
            [InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]
        ]
        try:
            await query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception:
            await query.message.reply_text(testo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Errore info vip: {e}")

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Non autorizzato.")
        return
    
    testo = (
        "👑 **PANNELLO DI CONTROLLO ADMIN** 👑\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Comandi disponibili:\n"
        "• `/setvip <chat_id> <giorni>` -> Attiva VIP a tempo.\n"
        "• `/givevip <chat_id>` -> Attiva VIP illimitato gratuito.\n"
        "• `/broadcast <messaggio>` -> Invia un broadcast a tutti gli utenti.\n"
        "• `/setbankroll <valore>` -> Modifica il bankroll."
    )
    await update.message.reply_text(testo, parse_mode="Markdown")

async def setvip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Non autorizzato.")
        return

    if len(context.args) >= 2:
        try:
            target_id = int(context.args[0])
            giorni = int(context.args[1])
            expiry_dt = datetime.now() + timedelta(days=giorni)
            set_user_vip_db(target_id, 1, expiry_dt)
            await update.message.reply_text(f"✅ Utente `{target_id}` impostato VIP per `{giorni}` giorni!", parse_mode="Markdown")
            try:
                await context.bot.send_message(chat_id=target_id, text="🎉 Abbonamento VIP attivato! Usa /start per ottenere il link d'invito.")
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ Usa: `/setvip <chat_id> <giorni>`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Usa: `/setvip <chat_id> <giorni>`", parse_mode="Markdown")

async def givevip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Non autorizzato.")
        return

    if len(context.args) >= 1:
        try:
            target_id = int(context.args[0])
            set_user_vip_db(target_id, 1, None)
            await update.message.reply_text(f"✅ Accesso VIP gratuito illimitato concesso all'utente `{target_id}`!", parse_mode="Markdown")
            try:
                await context.bot.send_message(chat_id=target_id, text="🎉 Ti è stato concesso l'accesso VIP gratuito illimitato! Usa /start per ottenere il link d'invito.")
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ ID non valido. Usa: `/givevip <chat_id>`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Specifica l'ID. Esempio: `/givevip 123456789`", parse_mode="Markdown")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Non autorizzato.")
        return

    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("⚠️ Usa: `/broadcast <messaggio>`", parse_mode="Markdown")
        return

    utenti = get_all_users()
    inviati = 0
    for uid in utenti:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **COMUNICAZIONE UFFICIALE:**\n\n{msg}", parse_mode="Markdown")
            inviati += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast inviato con successo a `{inviati}` utenti.", parse_mode="Markdown")

async def termini_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("📜 Servizio puramente statistico e di intrattenimento. Gioco vietato ai minori.")

async def get_invite_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        
        chat_id = query.message.chat_id
        user_info = get_user_data(chat_id)
        
        if user_info["is_vip"] == 1:
            try:
                link = await context.bot.create_chat_invite_link(
                    chat_id=CHANNEL_PRIVATO, 
                    member_limit=1, 
                    expire_date=datetime.now() + timedelta(hours=24)
                )
                testo = f"🎉 **Link d'invito monouso generato:**\n\n`{link.invite_link}`\n\n⚠️ Il link scade in 24 ore ed è utilizzabile una sola volta."
            except Exception as e:
                logging.error(f"Errore creazione link canale: {e}")
                testo = "⚠️ Errore generazione link. Verifica che il bot sia amministratore del canale privato."
        else:
            testo = "🔒 Non sei un utente VIP."

        keyboard = [[InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]]
        try:
            await query.message.edit_text(text=testo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            await query.message.reply_text(text=testo, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Errore get invite link: {e}")

async def chat_assistant_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return

        testo = update.message.text.lower()
        chat_id = update.effective_chat.id
        if "100" in testo:
            risposta = await genera_schedina_singola("100", chat_id)
            await update.message.reply_text(risposta, parse_mode="Markdown")
        elif "70" in testo:
            risposta = await genera_schedina_singola("70", chat_id)
            await update.message.reply_text(risposta, parse_mode="Markdown")
        elif "50" in testo:
            risposta = await genera_schedina_singola("50", chat_id)
            await update.message.reply_text(risposta, parse_mode="Markdown")
        elif "bomba" in testo or "schedina" in testo:
            risposta = await genera_schedina_singola("bomba", chat_id)
            await update.message.reply_text(risposta, parse_mode="Markdown")
        elif "live" in testo or "partite" in testo:
            risposta = await genera_testo_partite_oggi()
            await update.message.reply_text(risposta, parse_mode="Markdown")
        else:
            await update.message.reply_text("🤖 Usa /start per aprire il menu principale.")
    except Exception as e:
        logging.error(f"Errore chat_assistant_handler: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        
        chat_id = query.message.chat_id
        if query.data in ["btn_schedina_100", "btn_schedina_70", "btn_schedina_50", "btn_schedina_bomba"]:
            tipo_map = {"btn_schedina_100": "100", "btn_schedina_70": "70", "btn_schedina_50": "50", "btn_schedina_bomba": "bomba"}
            text = await genera_schedina_singola(tipo_map[query.data], chat_id)
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown")
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown")
        elif query.data == "btn_partite_oggi":
            text = await genera_testo_partite_oggi()
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown")
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown")
        elif query.data == "btn_live_radar":
            text = await genera_testo_live()
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown")
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown")
        elif query.data == "btn_fonti_analisi":
            text = await genera_testo_fonti()
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown", disable_web_page_preview=True)
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), parse_mode="Markdown", disable_web_page_preview=True)
        elif query.data == "btn_bankroll":
            await mostra_bankroll_menu(update, context)
        elif query.data == "btn_vip":
            await mostra_info_vip(update, context)
        elif query.data == "btn_get_link":
            await get_invite_link_handler(update, context)
        elif query.data == "btn_menu":
            await start(update, context)
    except Exception as e:
        logging.error(f"Errore gestione bottoni: {e}")

def main():
    try:
        server_thread = threading.Thread(target=run_web_server, daemon=True)
        server_thread.start()

        application = ApplicationBuilder().token(TOKEN).build()
        
        notif_thread = threading.Thread(target=background_live_notifier, args=(application,), daemon=True)
        notif_thread.start()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin_panel_command))
        application.add_handler(CommandHandler("setbankroll", set_bankroll_command))
        application.add_handler(CommandHandler("setvip", setvip_command))
        application.add_handler(CommandHandler("givevip", givevip_command))
        application.add_handler(CommandHandler("broadcast", broadcast_command))
        application.add_handler(CommandHandler("termini", termini_command))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_assistant_handler))

        logging.info("Bot King Pronostici Pro avviato con successo al 100%!")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logging.critical(f"Errore critico nel main: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
