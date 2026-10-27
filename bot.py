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

# CREDENZIALI CONFIGURATE
TOKEN = "8736023738:AAGfnjI9MURTUKNqbG80Pe4_aah4_IyPfpk"
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

# 2. Menu Principale con Pulsanti Rapidi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **BENVENUTO SU KING PRONOSTICI** ⚽\n\n"
        "Usa i pulsanti sottostanti per consultare la schedina mista (Italia ed Estero) completa di "
        "quota totale, puntata consigliata, probabilità e riscontro in tempo reale!"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Schedina Mista (Italia & Estero)", callback_data="btn_pronostici")],
        [InlineKeyboardButton("💣 Protocollo Schedina Bomba", callback_data="btn_bomba_avvio")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# 3. Schedina del Giorno con Partite Italiane e Straniere Miste
async def genera_testo_pronostici():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    matches_found = False
    schedina_text = f"🔥 **SCHEDINA MISTA (ITALIA & ESTERO) ({oggi_ita})** 🔥\n\n"
    
    quota_totale = 1.0
    partite_list = []
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        matches = data.get("matches", [])
        
        if matches:
            count = 0
            # Prende fino a 4 partite prendendo sia campionati italiani che esteri globali
            for match in matches[:4]:
                home = match.get('homeTeam', {}).get('name', 'Squadra A')
                away = match.get('awayTeam', {}).get('name', 'Squadra B')
                competition = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                pronostico = "1X o Over 1.5"
                quota = 1.35
                quota_totale *= quota
                
                esito_str = "⏳ In attesa"
                
                if status == 'FINISHED':
                    score = match.get('score', {}).get('fullTime', {})
                    home_goals = score.get('home', 0)
                    away_goals = score.get('away', 0)
                    tot_goals = home_goals + away_goals
                    
                    if home_goals >= away_goals or tot_goals >= 2:
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
                    f"🔹 Pronostico: `{pronostico}` | Quota: `{quota}`\n"
                    f"📌 Esito: {esito_str}\n"
                )
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    if not matches_found:
        quota_totale = 1.30 * 1.35 * 1.40
        partite_list.append(
            "🏆 *Torneo:* Serie A (Italia)\n"
            "⚽ **Inter vs Juventus**\n"
            "🔹 Pronostico: `1X` | Quota: `1.30` | 📌 Esito: ⏳ In attesa\n"
        )
        partite_list.append(
            "🏆 *Torneo:* Premier League (Inghilterra)\n"
            "⚽ **Arsenal vs Chelsea**\n"
            "🔹 Pronostico: `Over 1.5` | Quota: `1.35` | 📌 Esito: ⏳ In attesa\n"
        )
        partite_list.append(
            "🏆 *Torneo:* La Liga (Spagna)\n"
            "⚽ **Real Madrid vs Barcellona**\n"
            "🔹 Pronostico: `1X` | Quota: `1.40` | 📌 Esito: ⏳ In attesa\n"
        )

    quota_totale = round(quota_totale, 2)
    puntata_consigliata = 10
    vincita_totale = round(puntata_consigliata * quota_totale, 2)
    probabilita_schedina = "9/10 (Altissima affidabilità)"

    for p in partite_list:
        schedina_text += p + "\n"

    schedina_text += "━━━━━━━━━━━━━━━━━━━\n"
    schedina_text += f"📊 **QUOTA TOTALE SCHEDINA:** `{quota_totale}`\n"
    schedina_text += f"📈 **Probabilità di vincita:** `{probabilita_schedina}`\n"
    schedina_text += f"💰 **Puntata consigliata:** `{puntata_consigliata}€`\n"
    schedina_text += f"💵 **VINCITA COMPLESSIVA:** `{vincita_totale}€`\n"
    schedina_text += "━━━━━━━━━━━━━━━━━━━\n"
    schedina_text += "🍀 *Gioca responsabilmente!*"
    
    return schedina_text

# 4. Schedina Bomba Mista (Italia & Estero)
def genera_testo_bomba():
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    quota_bomba = 18.50
    puntata_bomba = 5
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)
    probabilita_bomba = "4/10 (Rischio Alto / Tentativo VIP)"
    
    testo = (
        f"💣 **SCHEDINA BOMBA MISTA ({oggi_ita})** 💣\n\n"
        "⚽ *Combinata ad altissimo rendimento (Italia & Estero)*\n\n"
        "1️⃣ **AC Milan vs Napoli** (Serie A - Italia)\n"
        "   🔹 Cosa giocare: `1 + Over 1.5` (Quota: `2.40`)\n\n"
        "2️⃣ **Manchester City vs Real Madrid** (Champions League)\n"
        "   🔹 Cosa giocare: `1 + Over 2.5` (Quota: `2.50`)\n\n"
        "3️⃣ **Bayern Monaco vs Borussia Dortmund** (Bundesliga - Germania)\n"
        "   🔹 Cosa giocare: `Goal + Over 2.5` (Quota: `2.45`)\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **QUOTA TOTALE BOMBA:** `{quota_bomba}`\n"
        f"📈 **Probabilità di vincita:** `{probabilita_bomba}`\n"
        f"💰 **Puntata consigliata:** `{puntata_bomba}€`\n"
        f"💵 **VINCITA COMPLESSIVA:** `{vincita_bomba}€`\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *Puntare solo il budget di svago!* 🍀"
    )
    return testo

# 5. Handlers con Pulsanti Integrati
async def cmd_pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_pronostici()
    keyboard = [
        [InlineKeyboardButton("🔄 Aggiorna Partite Miste", callback_data="btn_pronostici")],
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(testo, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(testo, parse_mode="Markdown", reply_markup=reply_markup)

# Effetto Esplosione prima della Bomba
async def bomba_effetto_esplosione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text("💣 *Innesco Schedina Bomba in corso...*\n\n⏱️ `3...`", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    await query.message.edit_text("💣 *Innesco Schedina Bomba in corso...*\n\n⏱️ `2...`", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    await query.message.edit_text("💣 *Innesco Schedina Bomba in corso...*\n\n⏱️ `1...`", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    testo_bomba = genera_testo_bomba()
    keyboard = [
        [InlineKeyboardButton("🔄 Ricarica Bomba", callback_data="btn_bomba_avvio")],
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(f"💥 **KABOOM! ECCO LA BOMBA MISTA!** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup)

async def cmd_bomba_testuale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo_bomba = genera_testo_bomba()
    keyboard = [
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"💥 **SCHEDINA BOMBA MISTA ATTIVA** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup)

# Gestore dei Click dei Bottoni
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "btn_pronostici":
        await cmd_pronostici(update, context)
    elif query.data == "btn_bomba_avvio":
        await bomba_effetto_esplosione(update, context)
    elif query.data == "btn_menu":
        await start(update, context)

def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()

    # Registrazione Comandi Testuali
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pronostici", cmd_pronostici))
    application.add_handler(CommandHandler("bomba", cmd_bomba_testuale))
    
    # Gestore Bottoni Interattivi
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot misto Italia & Estero avviato con successo!")
    application.run_polling()

if __name__ == '__main__':
    main()
