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
                        f"🔴 LIVE ({comp})\n"
                        f"⚽ {home} {hg} - {ag} {away}\n"
                        f"-----------------------------------\n"
                    )
    except Exception as e:
        logging.error(f"Errore Live: {e}")

    if not segnali_live:
        segnali_live.append("Nessuna partita in corso in questo momento.")

    return f"🚨 MONITORAGGIO MATCH LIVE ({oggi_ita}) 🚨\n\n" + "\n".join(segnali_live)

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
            await query.message.reply_text(testo, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.error(f"Errore bankroll menu: {e}")

async def set_bankroll_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if context.args:
            valore = float(context.args[0])
            update_user_bankroll(chat_id, valore)
            await update.message.reply_text(f"✅ Bankroll aggiornato a {valore}€!")
        else:
            await update.message.reply_text("⚠️ Specifica il valore. Esempio: /setbankroll 150")
    except ValueError:
        await update.message.reply_text("❌ Valore non valido. Usa es: /setbankroll 150")

async def mostra_info_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            pass
        
        testo = (
            "💎 **AREA ABBONAMENTO VIP / SERVIZIO**\n\n"
            "• Abbonamento Mensile: 19.99€\n"
            "• Abbonamento Annuale: 99.00€\n\n"
            "🔄 **Come pagare:**\n"
            "1. Contatta direttamente l'amministratore per concordare il pagamento.\n"
            "2. Invia la ricevuta in chat: verrai abilitato immediatamente e riceverai il link d'invito al canale VIP!"
        )
        keyboard = [
            [InlineKeyboardButton("✉️ Contatta Admin per Pagare", url=f"https://t.me/{ADMIN_USERNAME}")],
            [InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]
        ]
        try:
            await query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            await query.message.reply_text(testo, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.error(f"Errore info vip: {e}")

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
            await update.message.reply_text(f"✅ Utente {target_id} impostato VIP per {giorni} giorni!")
            try:
                await context.bot.send_message(chat_id=target_id, text="🎉 Abbonamento VIP attivato! Usa /start per avere il link d'invito.")
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ Usa: /setvip <chat_id> <giorni>")
    else:
        await update.message.reply_text("⚠️ Usa: /setvip <chat_id> <giorni>")

async def givevip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Non autorizzato.")
        return

    if len(context.args) >= 1:
        try:
            target_id = int(context.args[0])
            set_user_vip_db(target_id, 1, None)
            await update.message.reply_text(f"✅ Accesso VIP gratuito illimitato concesso all'utente {target_id}!")
            try:
                await context.bot.send_message(chat_id=target_id, text="🎉 Ti è stato concesso l'accesso VIP gratuito illimitato! Usa /start per ottenere il link d'invito.")
            except Exception:
                pass
        except ValueError:
            await update.message.reply_text("❌ ID non valido. Usa: /givevip <chat_id>")
    else:
        await update.message.reply_text("⚠️ Specifica l'ID. Esempio: /givevip 123456789")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Non autorizzato.")
        return

    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("⚠️ Usa: /broadcast <messaggio>")
        return

    utenti = get_all_users()
    inviati = 0
    for uid in utenti:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {msg}")
            inviati += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast inviato a {inviati} utenti.")

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
                testo = f"🎉 Ecco il tuo link d'invito monouso:\n\n{link.invite_link}\n\n⚠️ Il link scade in 24 ore ed è utilizzabile una sola volta."
            except Exception as e:
                logging.error(f"Errore creazione link canale: {e}")
                testo = "⚠️ Errore generazione link. Verifica che il bot sia amministratore del canale privato."
        else:
            testo = "🔒 Non sei un utente VIP."

        keyboard = [[InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]]
        try:
            await query.message.edit_text(text=testo, reply_markup=InlineKeyboardMarkup(keyboard), disable_web_page_preview=True)
        except Exception:
            await query.message.reply_text(text=testo, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logging.error(f"Errore get invite link: {e}")

async def chat_assistant_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text:
            return

        testo = update.message.text.lower()
        if "bomba" in testo or "schedina" in testo:
            risposta = await genera_testo_schedina_bomba()
            await update.message.reply_text(risposta)
        elif "live" in testo or "partite" in testo:
            risposta = await genera_testo_partite_oggi()
            await update.message.reply_text(risposta)
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
        
        if query.data == "btn_schedina_bomba":
            text = await genera_testo_schedina_bomba()
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]))
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]))
        elif query.data == "btn_partite_oggi":
            text = await genera_testo_partite_oggi()
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]))
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]))
        elif query.data == "btn_live_radar":
            text = await genera_testo_live()
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]))
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]))
        elif query.data == "btn_fonti_analisi":
            text = await genera_testo_fonti()
            try:
                await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), disable_web_page_preview=True)
            except Exception:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Menu", callback_data="btn_menu")]]), disable_web_page_preview=True)
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
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("setbankroll", setbankroll_command))
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
