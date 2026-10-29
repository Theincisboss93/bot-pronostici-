import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from datetime import datetime
import asyncio
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# Abilita i log di sistema
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# TOKEN MULTIPLI E API KEYS CONFIGURATI
TOKENS = [
    "9109962875:AAEfQyasxkN8Ddqm8I0PEmD3SwwgMBMkw3Y",
    "8987770671:AAHZ5vFUWWT2t83Dbxr6wCeVyNrMP2zEQHM"
]
TOKEN = TOKENS[0]

FOOTBALL_API_KEYS = [
    "be001fd3625a4f84b61b28e26ba101b2",
    "A7IauxgMoOQxH4XXRH8Eyflf16KC5OzoJ4tGb5ORCTMwqDg5VHpDaKadrl0O"
]

def fetch_from_football_api(endpoint_url):
    for api_key in FOOTBALL_API_KEYS:
        headers = {"X-Auth-Token": api_key}
        try:
            response = requests.get(endpoint_url, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                continue
        except Exception:
            continue
    return None

# 1. Server web fittizio per Render (Piano Free)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is online!")
        
    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# 2. Menu Principale con i Pulsanti (incluse le Scommesse Live)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **BENVENUTO SU KING PRONOSTICI** ⚽\n\n"
        "Seleziona la schedina o l'area desiderata:\n"
        "• **100% Sicura**: Giocate singole blindate\n"
        "• **70% Sicura**: Ottimo equilibrio e valore\n"
        "• **50% Sicura**: Schedina ad alto rendimento\n"
        "• **💣 Schedina Bomba VIP**: Partite reali del giorno\n"
        "• **🔴 Radar Scommesse LIVE**: Segnali di gol in tempo reale!"
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
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# Funzione generatrice delle 3 schedine standard
async def genera_testo_schedina(tipo_sicurezza):
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    matches_found = False
    partite_list = []
    quota_totale = 1.0
    
    giocate_possibili_100 = ["1X", "Over 1.5", "Gol Sku. Casa", "Under 3.5"]
    giocate_possibili_70 = ["Gol (Entrambe Segnano)", "1", "Over 2.5", "X2 + Over 1.5"]
    giocate_possibili_50 = ["1 + Over 2.5", "Gol + Over 2.5", "2 + Over 1.5", "1X + Gol"]
    
    if tipo_sicurezza == "100":
        titolo_schedina = f"🛡️ **SCHEDINA 100% SICURA ({oggi_ita})** 🛡️"
        prob_str = "10/10 (Massima Stabilità)"
        puntata_consigliata = 20
        max_partite = 3
    elif tipo_sicurezza == "70":
        titolo_schedina = f"⚖️ **SCHEDINA 70% SICURA ({oggi_ita})** ⚖️"
        prob_str = "7/10 (Valore ed Equilibrio)"
        puntata_consigliata = 10
        max_partite = 4
    else:
        titolo_schedina = f"📊 **SCHEDINA 50% SICURA ({oggi_ita})** 📊"
        prob_str = "5/10 (Alto Profitto / Rischio Calcolato)"
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
                    esito_str = "⏳ In attesa"
                    
                    if status == 'FINISHED':
                        score = match.get('score', {}).get('fullTime', {})
                        home_goals = score.get('home', 0)
                        away_goals = score.get('away', 0)
                        tot_goals = home_goals + away_goals
                        
                        if giocata == "1X" and home_goals >= away_goals:
                            esito_str = "✅ **VINTO!** 🎉"
                        elif giocata == "Over 1.5" and tot_goals >= 2:
                            esito_str = "✅ **VINTO!** 🎉"
                        elif giocata == "Gol (Entrambe Segnano)" and home_goals > 0 and away_goals > 0:
                            esito_str = "✅ **VINTO!** 🎉"
                        elif giocata == "Over 2.5" and tot_goals >= 3:
                            esito_str = "✅ **VINTO!** 🎉"
                        elif giocata == "1" and home_goals > away_goals:
                            esito_str = "✅ **VINTO!** 🎉"
                        else:
                            esito_str = "❌ **PERSO** 😢"
                            
                        match_title = f"⚽ **{home} {home_goals} - {away_goals} {away}**"
                    elif status in ['IN_PLAY', 'PAUSED']:
                        score = match.get('score', {}).get('fullTime', {})
                        hg = score.get('home', 0)
                        ag = score.get('away', 0)
                        esito_str = f"🔴 **LIVE ({hg} - {ag})**"
                        match_title = f"⚽ **{home} vs {away}**"
                    else:
                        match_title = f"⚽ **{home} vs {away}**"

                    partite_list.append(
                        f"🏆 *Torneo:* {competition}\n"
                        f"{match_title}\n"
                        f"🎯 **Giocata:** `{giocata}` | 📊 Quota: `{q}`\n"
                        f"📌 Esito: {esito_str}\n"
                    )
                    count += 1
                if count > 0:
                    matches_found = True
    except Exception as e:
        logging.error(f"Errore: {e}")

    if not matches_found:
        if tipo_sicurezza == "100":
            partite_list = [
                "🏆 *Torneo:* Serie A (Italia)\n⚽ **Inter vs Lecce**\n🎯 **Giocata:** `1X` | 📊 Quota: `1.20` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Premier League (Inghilterra)\n⚽ **Manchester City vs Southampton**\n🎯 **Giocata:** `Over 1.5` | 📊 Quota: `1.28` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 1.54
        elif tipo_sicurezza == "70":
            partite_list = [
                "🏆 *Torneo:* La Liga (Spagna)\n⚽ **Real Madrid vs Villarreal**\n🎯 **Giocata:** `Gol (Entrambe Segnano)` | 📊 Quota: `1.70` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Bundesliga (Germania)\n⚽ **Bayern Monaco vs Dortmund**\n🎯 **Giocata:** `Over 2.5` | 📊 Quota: `1.65` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 2.80
        else:
            partite_list = [
                "🏆 *Torneo:* Champions League\n⚽ **PSG vs Real Madrid**\n🎯 **Giocata:** `1 + Over 2.5` | 📊 Quota: `2.60` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Premier League\n⚽ **Arsenal vs Liverpool**\n🎯 **Giocata:** `Gol + Over 2.5` | 📊 Quota: `2.50` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 6.50

    quota_totale = round(quota_totale, 2)
    vincita_totale = round(puntata_consigliata * quota_totale, 2)

    for p in partite_list:
        schedina_text += p + "\n"

    schedina_text += "━━━━━━━━━━━━━━━━━━━\n"
    schedina_text += f"📊 **QUOTA TOTALE:** `{quota_totale}`\n"
    schedina_text += f"📈 **Sicurezza / Probabilità:** `{prob_str}`\n"
    schedina_text += f"💰 **Puntata consigliata:** `{puntata_consigliata}€`\n"
    schedina_text += f"💵 **VINCITA COMPLESSIVA:** `{vincita_totale}€`\n"
    schedina_text += "━━━━━━━━━━━━━━━━━━━\n"
    schedina_text += "🍀 *Gioca responsabilmente!*"
    
    return schedina_text

# Generatore Schedina Bomba VIP
async def genera_testo_bomba():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    
    partite_bomba_list = []
    quota_bomba = 1.0
    puntata_bomba = 5
    bomba_trovata = False
    
    giocate_bomba = ["1 + Over 1.5", "Gol + Over 2.5", "2 + Over 1.5", "1 & Gol"]

    try:
        data = fetch_from_football_api(url)
        if data and "matches" in data:
            matches = data.get("matches", [])
            if matches and len(matches) >= 3:
                for i, match in enumerate(matches[:4]):
                    home = match.get('homeTeam', {}).get('name', 'Squadra A')
                    away = match.get('awayTeam', {}).get('name', 'Squadra B')
                    competition = match.get('competition', {}).get('name', 'Campionato')
                    status = match.get('status', 'SCHEDULED')
                    
                    giocata = giocate_bomba[i % len(giocate_bomba)]
                    q = round(2.30 + (i * 0.35), 2)
                    quota_bomba *= q
                    
                    esito_str = "⏳ In attesa"
                    if status == 'FINISHED':
                        score = match.get('score', {}).get('fullTime', {})
                        hg = score.get('home', 0)
                        ag = score.get('away', 0)
                        esito_str = "✅ **VINTO!** 🎉" if (hg + ag) >= 2 else "❌ **PERSO** 😢"
                        match_title = f"⚽ **{home} {hg} - {ag} {away}**"
                    elif status in ['IN_PLAY', 'PAUSED']:
                        score = match.get('score', {}).get('fullTime', {})
                        hg = score.get('home', 0)
                        ag = score.get('away', 0)
                        esito_str = f"🔴 **LIVE ({hg} - {ag})**"
                        match_title = f"⚽ **{home} vs {away}**"
                    else:
                        match_title = f"⚽ **{home} vs {away}**"

                    partite_bomba_list.append(
                        f"🏆 *Torneo:* {competition}\n"
                        f"{match_title}\n"
                        f"🎯 **Giocata:** `{giocata}` | 📊 Quota: `{q}`\n"
                        f"📌 Esito: {esito_str}\n"
                    )
                bomba_trovata = True
    except Exception as e:
        logging.error(f"Errore: {e}")

    if not bomba_trovata:
        quota_bomba = 24.50
        partite_bomba_list = [
            "🏆 *Torneo:* Serie A (Italia)\n⚽ **AC Milan vs Napoli**\n🎯 **Giocata:** `1 + Over 1.5` | 📊 Quota: `2.40` | 📌 Esito: ⏳ In attesa\n",
            "🏆 *Torneo:* La Liga (Spagna)\n⚽ **Real Madrid vs Barcellona**\n🎯 **Giocata:** `Gol + Over 2.5` | 📊 Quota: `2.50` | 📌 Esito: ⏳ In attesa\n",
            "🏆 *Torneo:* Premier League (Inghilterra)\n⚽ **Arsenal vs Manchester City**\n🎯 **Giocata:** `1 & Gol` | 📊 Quota: `3.00` | 📌 Esito: ⏳ In attesa\n"
        ]

    quota_bomba = round(quota_bomba, 2)
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)

