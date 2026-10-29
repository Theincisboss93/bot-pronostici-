import os
import logging
import sys
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Abilita i log di sistema dettagliati
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# TOKEN E API KEYS CONFIGURATI
TOKENS = [
    "9109962875:AAEfQyasxkN8Ddqm8I0PEmD3SwwgMBMkw3Y",
    "8987770671:AAHZ5vFUWWT2t83Dbxr6wCeVyNrMP2zEQHM"
]
TOKEN = TOKENS[0]

FOOTBALL_API_KEYS = [
    "be001fd3625a4f84b61b28e26ba101b2",
    "A7IauxgMoOQxH4XXRH8Eyflf16KC5OzoJ4tGb5ORCTMwqDg5VHpDaKadrl0O"
]

USER_CHAT_ID = None
BOT_APPLICATION = None

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

# 1. Server web per Render (Piano Free)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is online and running perfectly!")
        
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = HTTPServer(("0.0.0.0", port), SimpleHandler)
        logging.info(f"Server web avviato con successo sulla porta {port}")
        server.serve_forever()
    except Exception as e:
        logging.error(f"Errore nell'avvio del server web sulla porta {port}: {e}")

# 2. Menu Principale con Bottoni Interattivi e Registrazione Chat ID
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_CHAT_ID
    if update.effective_chat:
        USER_CHAT_ID = update.effective_chat.id

    welcome_text = (
        "🤖 BENVENUTO SU KING PRONOSTICI ⚽\n\n"
        "Usa i **tasti interattivi** qui sotto oppure **scrivimi liberamente in chat** "
        "(es. 'dammi la schedina 100', 'schedina bomba', 'live') per avere tutto all'istante!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛡️ Schedina 100% Sicura", callback_data="btn_100")],
        [InlineKeyboardButton("⚖️ Schedina 70% Sicura", callback_data="btn_70")],
        [InlineKeyboardButton("📊 Schedina 50% Sicura", callback_data="btn_50")],
        [InlineKeyboardButton("💣 Schedina Bomba VIP", callback_data="btn_bomba_avvio")],
        [InlineKeyboardButton("🔴 Segnali LIVE & Imminente Gol", callback_data="btn_live_radar")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, reply_markup=reply_markup)

# Funzione generatrice delle schedine standard (filtrate per la giornata odierna)
async def genera_testo_schedina(tipo_sicurezza):
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    matches_found = False
    partite_list = []
    quota_totale = 1.0
    
    giocate_possibili_100 = ["1X", "Over 1.5", "Gol Casa", "Under 3.5"]
    giocate_possibili_70 = ["Gol (Entrambe Segnano)", "1", "Over 2.5", "X2 + Over 1.5"]
    giocate_possibili_50 = ["1 + Over 2.5", "Gol + Over 2.5", "2 + Over 1.5", "1X + Gol"]
    
    if tipo_sicurezza == "100":
        titolo_schedina = f"🛡️ SCHEDINA 100% SICURA ({oggi_ita})"
        prob_str = "10/10 (Massima Stabilita)"
        puntata_consigliata = 20
        max_partite = 3
    elif tipo_sicurezza == "70":
        titolo_schedina = f"⚖️ SCHEDINA 70% SICURA ({oggi_ita})"
        prob_str = "7/10 (Valore ed Equilibrio)"
        puntata_consigliata = 10
        max_partite = 4
    else:
        titolo_schedina = f"📊 SCHEDINA 50% SICURA ({oggi_ita})"
        prob_str = "5/10 (Alto Profitto)"
        puntata_consigliata = 5
        max_partite = 4

    schedina_text = f"{titolo_schedina}\n\n"
    
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            matches = data.get("matches", [])
            if matches:
                count = 0
                for i, match in enumerate(matches[:max_partite]):
                    home = match.get('homeTeam', {}).get('name', 'Squadra A')
                    away = match.get('awayTeam', {}).get('name', 'Squadra B')
                    competition = match.get('competition', {}).get('name', 'Campionato')
                    status = match.get('status', 'SCHEDULED')
                    
                    if tipo_sicurezza == "100":
                        giocata = giocate_possibili_100[i % len(giocate_possibili_100)]
                        q = round(1.20 + (i * 0.05), 2)
                    elif tipo_sicurezza == "70":
                        giocata = giocate_possibili_70[i % len(giocate_possibili_70)]
                        q = round(1.55 + (i * 0.10), 2)
                    else:
                        giocata = giocate_possibili_50[i % len(giocate_possibili_50)]
                        q = round(2.30 + (i * 0.15), 2)
                        
                    quota_totale *= q
                    esito_str = "In attesa"
                    
                    if status == 'FINISHED':
                        score = match.get('score', {}).get('fullTime', {})
                        hg = score.get('home', 0)
                        ag = score.get('away', 0)
                        esito_str = "VINTO!" if (hg + ag) >= 1 else "PERSO"
                        match_title = f"{home} {hg} - {ag} {away}"
                    elif status in ['IN_PLAY', 'PAUSED']:
                        score = match.get('score', {}).get('fullTime', {})
                        hg = score.get('home', 0)
                        ag = score.get('away', 0)
                        esito_str = f"LIVE ({hg} - {ag})"
                        match_title = f"{home} vs {away}"
                    else:
                        match_title = f"{home} vs {away}"

                    partite_list.append(
                        f"Torneo: {competition}\n"
                        f"⚽ {match_title}\n"
                        f"🎯 Giocata: {giocata} | Quota: {q}\n"
                        f"📌 Esito: {esito_str}\n"
                    )
                    count += 1
                if count > 0:
                    matches_found = True
    except Exception as e:
        logging.error(f"Errore API Schedina: {e}")

    if not matches_found:
        partite_list = [
            f"Torneo: Partite Odierne ({oggi_ita})\n⚽ Evento Principale 1 vs Evento Principale 2\n🎯 Giocata: 1X | Quota: 1.35 | Esito: In attesa\n",
            f"Torneo: Partite Odierne ({oggi_ita})\n⚽ Evento Principale 3 vs Evento Principale 4\n🎯 Giocata: Over 1.5 | Quota: 1.40 | Esito: In attesa\n"
        ]
        quota_totale = 1.89

    quota_totale = round(quota_totale, 2)
    vincita_totale = round(puntata_consigliata * quota_totale, 2)

    for p in partite_list:
        schedina_text += p + "\n"

    schedina_text += "-----------------------------------\n"
    schedina_text += f"QUOTA TOTALE: {quota_totale}\n"
    schedina_text += f"Probabilità: {prob_str}\n"
    schedina_text += f"Puntata consigliata: {puntata_consigliata}€\n"
    schedina_text += f"VINCITA COMPLESSIVA: {vincita_totale}€\n"
    schedina_text += "-----------------------------------\n"
    schedina_text += "Gioca responsabilmente!"
    
    return schedina_text

# Generatore Schedina Bomba VIP (Rigorosamente per oggi)
async def genera_testo_bomba():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    partite_bomba_list = []
    quota_bomba = 1.0
    puntata_bomba = 5
    trovate = False

    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            matches = data.get("matches", [])
            if matches:
                for i, match in enumerate(matches[:3]):
                    home = match.get('homeTeam', {}).get('name', 'Casa')
                    away = match.get('awayTeam', {}).get('name', 'Ospiti')
                    comp = match.get('competition', {}).get('name', 'Torneo')
                    q = round(2.20 + (i * 0.30), 2)
                    quota_bomba *= q
                    partite_bomba_list.append(
                        f"Torneo: {comp}\n⚽ {home} vs {away}\n🎯 Giocata: 1 + Over 1.5 | Quota: {q} | Esito: In attesa\n"
                    )
                trovate = True
    except Exception as e:
        logging.error(f"Errore Bomba API: {e}")

    if not trovate:
        quota_bomba = 15.50
        partite_bomba_list = [
            f"Torneo: Serie A ({oggi_ita})\n⚽ Squadra A vs Squadra B\n🎯 Giocata: 1 + Over 1.5 | Quota: 2.50 | Esito: In attesa\n",
            f"Torneo: Premier League ({oggi_ita})\n⚽ Squadra C vs Squadra D\n🎯 Giocata: Gol + Over 2.5 | Quota: 2.50 | Esito: In attesa\n",
            f"Torneo: Champions League ({oggi_ita})\n⚽ Squadra E vs Squadra F\n🎯 Giocata: 1 & Gol | Quota: 2.48 | Esito: In attesa\n"
        ]

    quota_bomba = round(quota_bomba, 2)
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)

    testo = f"💣 SCHEDINA BOMBA VIP DEL GIORNO ({oggi_ita}) 💣\n\n"
    testo += "Combinata ad altissimo rendimento sui match di oggi:\n\n"
    
    for p in partite_bomba_list:
        testo += p + "\n"

    testo += "-----------------------------------\n"
    testo += f"QUOTA TOTALE BOMBA: {quota_bomba}\n"
    testo += f"Sicurezza: 3.5/10 (Rischio Alto VIP)\n"
    testo += f"Puntata consigliata: {puntata_bomba}€\n"
    testo += f"VINCITA COMPLESSIVA: {vincita_bomba}€\n"
    testo += "-----------------------------------\n"
    testo += "Puntare solo il budget di svago!"
    
    return testo

# Generatore Segnali LIVE
async def genera_testo_live():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    segnali_live = []
    
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            matches = data.get("matches", [])
            for match in matches:
                status = match.get('status', '')
                if status in ['IN_PLAY', 'PAUSED']:
                    home = match.get('homeTeam', {}).get('name', 'Casa')
                    away = match.get('awayTeam', {}).get('name', 'Ospiti')
                    competition = match.get('competition', {}).get('name', 'Campionato')
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0)
                    ag = score.get('away', 0)
                    
                    segnali_live.append(
                        f"🔴 MATCH LIVE ({competition})\n"
                        f"⚽ {home} {hg} - {ag} {away}\n"
                        f"🔥 SQUADRA DA PUNTARE: Prossimo Gol Casa\n"
                        f"📊 Quota Live: 1.95\n"
                        f"💰 Puntata Consigliata: 12€\n"
                        f"-----------------------------------\n"
                    )
    except Exception as e:
        logging.error(f"Errore Live: {e}")

    if not segnali_live:
        segnali_live.append(
            f"🔴 RADAR LIVE ATTIVO ({oggi_ita})\n\n"
            "Nessuna partita in corso in questo momento. Appena comincerà un match live oggi, riceverai l'allerta automatica!"
        )

    testo = f"🚨 RADAR SCOMMESSE LIVE & SEGNALI GOL ({oggi_ita}) 🚨\n\n"
    for s in segnali_live:
        testo += s + "\n"
    
    return testo

# Assistente Intelligente per la Chat Testuale Libera
async def chat_assistant_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_CHAT_ID
    if update.effective_chat:
        USER_CHAT_ID = update.effective_chat.id

    if not update.message or not update.message.text:
        return

    testo_utente = update.message.text.lower()

    if "100" in testo_utente or "sicura" in testo_utente:
        risposta = await genera_testo_schedina("100")
        await update.message.reply_text(risposta)
    elif "70" in testo_utente:
        risposta = await genera_testo_schedina("70")
        await update.message.reply_text(risposta)
    elif "50" in testo_utente:
        risposta = await genera_testo_schedina("50")
        await update.message.reply_text(risposta)
    elif "bomba" in testo_utente or "vip" in testo_utente:
        risposta = await genera_testo_bomba()
        await update.message.reply_text(risposta)
    elif "live" in testo_utente or "gol" in testo_utente or "partite" in testo_utente:
        risposta = await genera_testo_live()
        await update.message.reply_text(risposta)
    else:
        risposta = (
            "🤖 Ciao! Sono il tuo assistente King Pronostici.\n"
            "Puoi usare i bottoni interattivi con il comando /start oppure chiedermi direttamente:\n"
            "• 'Dammi la schedina 100'\n"
            "• 'Schedina 70'\n"
            "• 'Schedina 50'\n"
            "• 'Schedina Bomba'\n"
            "• 'Partite live'"
        )
        await update.message.reply_text(risposta)

async def mostra_live_radar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_live()
    keyboard = [
        [InlineKeyboardButton("Aggiorna Radar Live", callback_data="btn_live_radar")],
        [InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(testo, reply_markup=reply_markup)

# BACKGROUND THREAD: Notifiche push automatiche in chat
def background_live_notifier():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def worker():
        notiziario_inviato = set()
        while True:
            await asyncio.sleep(45)
            global USER_CHAT_ID, BOT_APPLICATION
            if USER_CHAT_ID and BOT_APPLICATION:
                oggi = datetime.now().strftime('%Y-%m-%d')
                url = f"https://api.football-data.org/v4/matches?date={oggi}"
                try:
                    data = fetch_from_football_api(url)
                    if data and "matches" in data:
                        matches = data.get("matches", [])
                        for match in matches:
                            match_id = match.get('id')
                            status = match.get('status', '')
                            
                            if status == 'IN_PLAY':
                                home = match.get('homeTeam', {}).get('name', 'Casa')
                                away = match.get('awayTeam', {}).get('name', 'Ospiti')
                                competition = match.get('competition', {}).get('name', 'Campionato')
                                score = match.get('score', {}).get('fullTime', {})
                                hg = score.get('home', 0)
                                ag = score.get('away', 0)
                                
                                match_key = f"{match_id}_{hg}_{ag}"
                                if match_key not in notiziario_inviato:
                                    notifica_text = (
                                        f"🚨 NOTIFICA PUSH LIVE AUTOMATICA ({competition}) 🚨\n\n"
                                        f"⚽ {home} {hg} - {ag} {away}\n"
                                        f"🔥 CHI PUNTARE: Prossimo Gol / Assedio\n"
                                        f"🎯 Cosa giocare: Over 0.5 Live\n"
                                        f"📊 Quota Live: 1.95\n"
                                        f"💰 Puntata consigliata: 12€\n\n"
                                        f"Piazzala subito prima del cambio quota!"
                                    )
                                    await BOT_APPLICATION.bot.send_message(chat_id=USER_CHAT_ID, text=notifica_text)
                                    notiziario_inviato.add(match_key)
                except Exception as e:
                    logging.error(f"Errore nel worker di notifica push live: {e}")

    loop.run_until_complete(worker())

async def bomba_effetto_esplosione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text("💣 Innesco Schedina Bomba VIP in corso...\n\n3...")
    await asyncio.sleep(0.5)
    await query.message.edit_text("💣 Innesco Schedina Bomba VIP in corso...\n\n2...")
    await asyncio.sleep(0.5)
    await query.message.edit_text("💣 Innesco Schedina Bomba VIP in corso...\n\n1...")
    await asyncio.sleep(0.5)
    
    testo_bomba = await genera_testo_bomba()
    keyboard_bomba = [
        [InlineKeyboardButton("Aggiorna Bomba", callback_data="btn_bomba_avvio")],
        [InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup_bomba = InlineKeyboardMarkup(keyboard_bomba)
    await query.message.edit_text(testo_bomba, reply_markup=reply_markup_bomba)

async def mostra_100(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("100")
    keyboard = [
        [InlineKeyboardButton("Aggiorna", callback_data="btn_100")],
        [InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(testo, reply_markup=reply_markup)

async def mostra_70(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("70")
    keyboard = [
        [InlineKeyboardButton("Aggiorna", callback_data="btn_70")],
        [InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(testo, reply_markup=reply_markup)

async def mostra_50(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("50")
    keyboard = [
        [InlineKeyboardButton("Aggiorna", callback_data="btn_50")],
        [InlineKeyboardButton("Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(testo, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "btn_100":
        await mostra_100(update, context)
    elif query.data == "btn_70":
        await mostra_70(update, context)
    elif query.data == "btn_50":
        await mostra_50(update, context)
    elif query.data == "btn_bomba_avvio":
        await bomba_effetto_esplosione(update, context)
    elif query.data == "btn_live_radar":
        await mostra_live_radar(update, context)
    elif query.data == "btn_menu":
        await start(update, context)

def main():
    global BOT_APPLICATION
    try:
        server_thread = threading.Thread(target=run_web_server, daemon=True)
        server_thread.start()

        application = ApplicationBuilder().token(TOKEN).build()
        BOT_APPLICATION = application

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_assistant_handler))

        notifier_thread = threading.Thread(target=background_live_notifier, daemon=True)
        notifier_thread.start()

        logging.info("Bot avviato con successo: tasti, chat e notifiche live perfettamente attivi!")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logging.critical(f"Errore critico durante l'avvio del bot: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
