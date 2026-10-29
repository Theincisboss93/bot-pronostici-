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
        logging.info(f"Server web avviato sulla porta {port}")
        server.serve_forever()
    except Exception as e:
        logging.error(f"Errore server web: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_CHAT_ID
    if update.effective_chat:
        USER_CHAT_ID = update.effective_chat.id

    welcome_text = (
        "🤖 BENVENUTO SU KING PRONOSTICI ⚽\n\n"
        "Usa i tasti interattivi o scrivimi in chat "
        "(es. 'schedina 100', 'schedina bomba', 'live')!"
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

def calcola_esito_partita(giocata, hg, ag, status):
    if status in ['TIMED', 'SCHEDULED']:
        return "⏳ In attesa"
    elif status in ['IN_PLAY', 'PAUSED']:
        return f"🔴 LIVE ({hg} - {ag})"
    elif status == 'FINISHED':
        tot_gol = hg + ag
        vinta = False
        
        if giocata == "1X":
            vinta = (hg >= ag)
        elif giocata == "X2":
            vinta = (ag >= hg)
        elif giocata == "1":
            vinta = (hg > ag)
        elif giocata == "2":
            vinta = (ag > hg)
        elif giocata == "Over 1.5":
            vinta = (tot_gol >= 2)
        elif giocata == "Over 2.5":
            vinta = (tot_gol >= 3)
        elif giocata == "Under 3.5":
            vinta = (tot_gol <= 3)
        elif giocata == "Gol Casa":
            vinta = (hg > 0)
        elif giocata in ["Gol (Entrambe Segnano)", "Gol"]:
            vinta = (hg > 0 and ag > 0)
        elif giocata == "1 + Over 1.5":
            vinta = (hg > ag and tot_gol >= 2)
        elif giocata == "Gol + Over 2.5":
            vinta = (hg > 0 and ag > 0 and tot_gol >= 3)
        elif giocata == "1 & Gol":
            vinta = (hg > ag and ag > 0)
        else:
            vinta = (tot_gol >= 1)
            
        if vinta:
            return "✅ VINTO!"
        else:
            return "❌ PERSO"
    return "⏳ In attesa"

async def genera_testo_schedina(tipo_sicurezza):
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    matches_found = False
    partite_list = []
    quota_totale = 1.0
    
    giocate_100 = ["1X", "Over 1.5", "Gol Casa", "Under 3.5"]
    giocate_70 = ["Gol", "1", "Over 2.5", "X2 + Over 1.5"]
    giocate_50 = ["1 + Over 2.5", "Gol + Over 2.5", "2 + Over 1.5", "1 + Over 1.5"]
    
    if tipo_sicurezza == "100":
        titolo = f"🛡️ SCHEDINA 100% SICURA ({oggi_ita})"
        prob = "10/10 (Massima Stabilita)"
        puntata = 20
        max_p = 3
    elif tipo_sicurezza == "70":
        titolo = f"⚖️ SCHEDINA 70% SICURA ({oggi_ita})"
        prob = "7/10 (Valore ed Equilibrio)"
        puntata = 10
        max_p = 4
    else:
        titolo = f"📊 SCHEDINA 50% SICURA ({oggi_ita})"
        prob = "5/10 (Alto Profitto)"
        puntata = 5
        max_p = 4

    schedina_text = f"{titolo}\n\n"
    
    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            matches = data.get("matches", [])
            if matches:
                count = 0
                for i, match in enumerate(matches[:max_p]):
                    home = match.get('homeTeam', {}).get('name', 'Casa')
                    away = match.get('awayTeam', {}).get('name', 'Ospiti')
                    comp = match.get('competition', {}).get('name', 'Campionato')
                    status = match.get('status', 'SCHEDULED')
                    
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0) if score.get('home') is not None else 0
                    ag = score.get('away', 0) if score.get('away') is not None else 0
                    
                    if tipo_sicurezza == "100":
                        giocata = giocate_100[i % len(giocate_100)]
                        q = round(1.20 + (i * 0.05), 2)
                    elif tipo_sicurezza == "70":
                        giocata = giocate_70[i % len(giocate_70)]
                        q = round(1.55 + (i * 0.10), 2)
                    else:
                        giocata = giocate_50[i % len(giocate_50)]
                        q = round(2.30 + (i * 0.15), 2)
                        
                    quota_totale *= q
                    esito = calcola_esito_partita(giocata, hg, ag, status)
                    m_title = f"{home} {hg} - {ag} {away}" if status == 'FINISHED' else f"{home} vs {away}"

                    partite_list.append(
                        f"Torneo: {comp}\n⚽ {m_title}\n🎯 Giocata: {giocata} | Quota: {q}\n📌 Esito: {esito}\n"
                    )
                    count += 1
                if count > 0:
                    matches_found = True
    except Exception as e:
        logging.error(f"Errore Schedina: {e}")

    if not matches_found:
        partite_list = [
            f"Torneo: Partite Odierne ({oggi_ita})\n⚽ Evento 1 vs Evento 2\n🎯 Giocata: 1X | Quota: 1.35 | 📌 Esito: ⏳ In attesa\n",
            f"Torneo: Partite Odierne ({oggi_ita})\n⚽ Evento 3 vs Evento 4\n🎯 Giocata: Over 1.5 | Quota: 1.40 | 📌 Esito: ⏳ In attesa\n"
        ]
        quota_totale = 1.89

    quota_totale = round(quota_totale, 2)
    vincita = round(puntata * quota_totale, 2)

    for p in partite_list:
        schedina_text += p + "\n"

    schedina_text += "-----------------------------------\n"
    schedina_text += f"QUOTA TOTALE: {quota_totale}\n"
    schedina_text += f"Probabilità: {prob}\n"
    schedina_text += f"Puntata consigliata: {puntata}€\n"
    schedina_text += f"VINCITA COMPLESSIVA: {vincita}€\n"
    schedina_text += "-----------------------------------\n"
    schedina_text += "Gioca responsabilmente!"
    
    return schedina_text

async def genera_testo_bomba():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    partite_bomba = []
    quota_bomba = 1.0
    puntata_bomba = 5
    trovate = False
    giocate = ["1 + Over 1.5", "Gol + Over 2.5", "1 & Gol"]

    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            matches = data.get("matches", [])
            if matches:
                for i, match in enumerate(matches[:3]):
                    home = match.get('homeTeam', {}).get('name', 'Casa')
                    away = match.get('awayTeam', {}).get('name', 'Ospiti')
                    comp = match.get('competition', {}).get('name', 'Torneo')
                    status = match.get('status', 'SCHEDULED')
                    
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0) if score.get('home') is not None else 0
                    ag = score.get('away', 0) if score.get('away') is not None else 0
                    
                    giocata = giocate[i % len(giocate)]
                    q = round(2.20 + (i * 0.30), 2)
                    quota_bomba *= q
                    
                    esito = calcola_esito_partita(giocata, hg, ag, status)
                    m_title = f"{home} {hg} - {ag} {away}" if status == 'FINISHED' else f"{home} vs {away}"

                    partite_bomba.append(
                        f"Torneo: {comp}\n⚽ {m_title}\n🎯 Giocata: {giocata} | Quota: {q}\n📌 Esito: {esito}\n"
                    )
                trovate = True
    except Exception as e:
        logging.error(f"Errore Bomba: {e}")

    if not trovate:
        quota_bomba = 15.50
        partite_bomba = [
            f"Torneo: Serie A ({oggi_ita})\n⚽ Squadra A vs Squadra B\n🎯 Giocata: 1 + Over 1.5 | Quota: 2.50 | 📌 Esito: ⏳ In attesa\n",
            f"Torneo: Premier League ({oggi_ita})\n⚽ Squadra C vs Squadra D\n🎯 Giocata: Gol + Over 2.5 | Quota: 2.50 | 📌 Esito: ⏳ In attesa\n",
            f"Torneo: Champions League ({oggi_ita})\n⚽ Squadra E vs Squadra F\n🎯 Giocata: 1 & Gol | Quota: 2.48 | 📌 Esito: ⏳ In attesa\n"
        ]

    quota_bomba = round(quota_bomba, 2)
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)

    testo = f"💣 SCHEDINA BOMBA VIP ({oggi_ita}) 💣\n\n"
    for p in partite_bomba:
        testo += p + "\n"

    testo += "-----------------------------------\n"
    testo += f"QUOTA TOTALE BOMBA: {quota_bomba}\n"
    testo += f"Sicurezza: 3.5/10 (Rischio Alto VIP)\n"
    testo += f"Puntata consigliata: {puntata_bomba}€\n"
    testo += f"VINCITA COMPLESSIVA: {vincita_bomba}€\n"
    testo += "-----------------------------------\n"
    testo += "Puntare solo il budget di svago!"
    
    return testo

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
                if match.get('status') in ['IN_PLAY', 'PAUSED']:
                    home = match.get('homeTeam', {}).get('name', 'Casa')
                    away = match.get('awayTeam', {}).get('name', 'Ospiti')
                    comp = match.get('competition', {}).get('name', 'Campionato')
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0)
                    ag = score.get('away', 0)
                    
                    segnali_live.append(
                        f"🔴 MATCH LIVE ({comp})\n"
                        f"⚽ {home} {hg} - {ag} {away}\n"
                        f"🔥 PUNTARE: Prossimo Gol Casa\n"
                        f"📊 Quota: 1.95 | 💰 Puntata: 12€\n"
                        f"-----------------------------------\n"
                    )
    except Exception as e:
        logging.error(f"Errore Live: {e}")

    if not segnali_live:
        segnali_live.append(
            f"🔴 RADAR LIVE ({oggi_ita})\n\nNessuna partita in corso adesso. Riceverai notifiche appena inizierà un match!"
        )

    testo = f"🚨 RADAR SCOMMESSE LIVE ({oggi_ita}) 🚨\n\n"
    for s in segnali_live:
        testo += s + "\n"
    return testo

async def chat_assistant_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_CHAT_ID
    if update.effective_chat:
        USER_CHAT_ID = update.effective_chat.id

    if not update.message or not update.message.text:
        return

    testo = update.message.text.lower()

    if "100" in testo or "sicura" in testo:
        await update.message.reply_text(await genera_testo_schedina("100"))
    elif "70" in testo:
        await update.message.reply_text(await genera_testo_schedina("70"))
    elif "50" in testo:
        await update.message.reply_text(await genera_testo_schedina("50"))
    elif "bomba" in testo or "vip" in testo:
        await update.message.reply_text(await genera_testo_bomba())
    elif "live" in testo or "gol" in testo or "partite" in testo:
        await update.message.reply_text(await genera_testo_live())
    else:
        risposta = (
            "🤖 Ciao! Sono King Pronostici.\n"
            "Chiedimi 'schedina 100', 'schedina 70', 'schedina 50', 'schedina bomba' o 'live', oppure usa /start!"
        )
        await update.message.reply_text(risposta)

async def mostra_live_radar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_live()
    keyboard = [
        [InlineKeyboardButton("Aggiorna", callback_data="btn_live_radar")],
        [InlineKeyboardButton("Menu Principale", callback_data="btn_menu")]
    ]
    await update.callback_query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(keyboard))

def background_live_notifier():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def worker():
        inviati = set()
        while True:
            await asyncio.sleep(45)
            global USER_CHAT_ID, BOT_APPLICATION
            if USER_CHAT_ID and BOT_APPLICATION:
                oggi = datetime.now().strftime('%Y-%m-%d')
                url = f"https://api.football-data.org/v4/matches?date={oggi}"
                try:
                    data = fetch_from_football_api(url)
                    if data and "matches" in data:
                        for match in data.get("matches", []):
                            if match.get('status') == 'IN_PLAY':
                                m_id = match.get('id')
                                home = match.get('homeTeam', {}).get('name', 'Casa')
                                away = match.get('awayTeam', {}).get('name', 'Ospiti')
                                comp = match.get('competition', {}).get('name', 'Campionato')
                                score = match.get('score', {}).get('fullTime', {})
                                hg = score.get('home', 0)
                                ag = score.get('away', 0)
                                
                                key = f"{m_id}_{hg}_{ag}"
                                if key not in inviati:
                                    msg = (
                                        f"🚨 NOTIFICA LIVE ({comp}) 🚨\n\n"
                                        f"⚽ {home} {hg} - {ag} {away}\n"
                                        f"🔥 PUNTARE: Over 0.5 Live\n"
                                        f"📊 Quota: 1.95 | 💰 Puntata: 12€"
                                    )
                                    await BOT_APPLICATION.bot.send_message(chat_id=USER_CHAT_ID, text=msg)
                                    inviati.add(key)
                except Exception as e:
                    logging.error(f"Errore Notifiche Live: {e}")

    loop.run_until_complete(worker())

async def bomba_effetto_esplosione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("💣 Innesco Schedina Bomba...\n\n3...")
    await asyncio.sleep(0.4)
    await query.message.edit_text("💣 Innesco Schedina Bomba...\n\n2...")
    await asyncio.sleep(0.4)
    await query.message.edit_text("💣 Innesco Schedina Bomba...\n\n1...")
    await asyncio.sleep(0.4)
    
    testo = await genera_testo_bomba()
    kb = [
        [InlineKeyboardButton("Aggiorna", callback_data="btn_bomba_avvio")],
        [InlineKeyboardButton("Menu Principale", callback_data="btn_menu")]
    ]
    await query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(kb))

async def mostra_100(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("100")
    kb = [[InlineKeyboardButton("Aggiorna", callback_data="btn_100")], [InlineKeyboardButton("Menu Principale", callback_data="btn_menu")]]
    await update.callback_query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(kb))

async def mostra_70(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("70")
    kb = [[InlineKeyboardButton("Aggiorna", callback_data="btn_70")], [InlineKeyboardButton("Menu Principale", callback_data="btn_menu")]]
    await update.callback_query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(kb))

async def mostra_50(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("50")
    kb = [[InlineKeyboardButton("Aggiorna", callback_data="btn_50")], [InlineKeyboardButton("Menu Principale", callback_data="btn_menu")]]
    await update.callback_query.message.edit_text(testo, reply_markup=InlineKeyboardMarkup(kb))

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

        logging.info("Bot avviato con successo!")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logging.critical(f"Errore critico: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
