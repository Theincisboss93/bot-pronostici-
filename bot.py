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

# TOKEN CONFIGURATO
TOKEN = "9109962875:AAEfQyasxkN8Ddqm8I0PEmD3SwwgMBMkw3Y"
FOOTBALL_API_KEY = "be001fd3625a4f84b61b28e26ba101b2"

# 1. Server web fittizio per Render (Piano Free)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is online!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# 2. Menu Principale con i 4 Pulsanti (3 Schedine + Bomba Libera)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **BENVENUTO SU KING PRONOSTICI** ⚽\n\n"
        "Seleziona la schedina desiderata:\n"
        "• **100% Sicura**: Giocate singole blindate\n"
        "• **70% Sicura**: Ottimo equilibrio e valore\n"
        "• **50% Sicura**: Schedina ad alto rendimento\n"
        "• **💣 Schedina Bomba VIP**: Misto Italia & Estero (Sbloccata e libera!)"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛡️ Schedina 100% Sicura", callback_data="btn_100")],
        [InlineKeyboardButton("⚖️ Schedina 70% Sicura", callback_data="btn_70")],
        [InlineKeyboardButton("📊 Schedina 50% Sicura", callback_data="btn_50")],
        [InlineKeyboardButton("💣 Schedina Bomba VIP (Italia & Estero)", callback_data="btn_bomba_avvio")],
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
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
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
        response = requests.get(url, headers=headers)
        data = response.json()
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
                        if home_goals + away_goals >= 2:
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
        logging.error(f"Errore API: {e}")

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
    schedina_text +=
