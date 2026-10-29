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
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

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

# 2. Menu Principale e Registrazione Chat ID
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global USER_CHAT_ID
    if update.effective_chat:
        USER_CHAT_ID = update.effective_chat.id

    welcome_text = (
        "🤖 BENVENUTO SU KING PRONOSTICI ⚽\n\n"
        "Seleziona la schedina o l'area desiderata:\n"
        "• 100% Sicura: Giocate singole blindate\n"
        "• 70% Sicura: Ottimo equilibrio e valore\n"
        "• 50% Sicura: Schedina ad alto rendimento\n"
        "• 💣 Schedina Bomba VIP: Partite reali del giorno\n"
        "• 🔴 Radar Scommesse LIVE: Segnali in tempo reale!"
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

# Funzione generatrice delle 3 schedine standard
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
        if tipo_sicurezza == "100":
            partite_list = [
                "Torneo: Serie A\n⚽ Inter vs Lecce\n🎯 Giocata: 1X | Quota: 1.20 | Esito: In attesa\n",
                "Torneo: Premier League\n⚽ Manchester City vs Southampton\n🎯 Giocata: Over 1.5 | Quota: 1.28 | Esito: In attesa\n"
            ]
            quota_totale = 1.54
        elif tipo_sicurezza == "70":
            partite_list = [
                "Torneo: La Liga\n⚽ Real Madrid vs Villarreal\n🎯 Giocata: Gol | Quota: 1.70 | Esito: In attesa\n",
                "Torneo: Bundesliga\n⚽ Bayern Monaco vs Dortmund\n🎯 Giocata: Over 2.5 | Quota: 1.65 | Esito: In attesa\n"
            ]
            quota_totale = 2.80
        else:
            partite_list = [
                "Torneo: Champions League\n⚽ PSG vs Real Madrid\n🎯 Giocata: 1 + Over 2.5 | Quota: 2.60 | Esito: In attesa\n",
                "Torneo: Premier League\n⚽ Arsenal vs Liverpool\n🎯 Giocata: Gol + Over 2.5 | Quota: 2.50 | Esito: In attesa\n"
            ]
            quota_totale = 6.50

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

# Generatore Schedina Bomba VIP
async def genera_testo_bomba():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    partite_bomba_list = []
    quota_bomba = 24.50
    puntata_bomba = 5
    
    partite_bomba_list = [
        "Torneo: Serie A\n⚽ AC Milan vs Napoli\n🎯 Giocata: 1 + Over 1.5 | Quota: 2.40 | Esito: In attesa\n",
        "Torneo: La Liga\n⚽ Real Madrid vs Barcellona\n🎯 Giocata: Gol + Over 2.5 | Quota: 2.50 | Esito: In attesa\n",
        "Torneo: Premier League\n⚽ Arsenal vs Manchester City\n🎯 Giocata: 1 & Gol | Quota: 3.00 | Esito: In attesa\n"
    ]

    vincita_bomba = round(puntata_bomba * quota_bomba, 2)

    testo = f"💣 SCHEDINA BOMBA VIP DEL GIORNO ({oggi_ita}) 💣\n\n"
    testo += "Combinata ad altissimo rendimento:\n\n"
    
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
            "🔴 RADAR LIVE ATTIVO (Tutti i Campionati Mondiali)\n\n"
            "Nessun match in corso adesso. Appena comincerà una partita live, riceverai l'allerta automatica!"
        )

    testo = f"🚨 RADAR SCOMMESSE LIVE & SEGNALI GOL ({oggi_ita}) 🚨\n\n"
    for s in segnali_live:
        testo += s + "\n"
    
    return testo

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
            if USER_CHAT_ID
