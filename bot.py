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
        "Usa i pulsanti sottostanti per consultare le schedine in un solo click, "
        "senza dover digitare i comandi ogni volta!"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Schedina Globale del Giorno", callback_data="btn_pronostici")],
        [InlineKeyboardButton("💣 Protocollo Schedina Bomba", callback_data="btn_bomba_avvio")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# 3. Schedina del Giorno (Multi-Campionato ad Alta Affidabilità)
async def genera_testo_pronostici():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    matches_found = False
    schedina_text = f"🔥 **SCHEDINA DEL GIORNO ({oggi_ita})** 🔥\n\n"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        matches = data.get("matches", [])
        
        if matches:
            count = 0
            for match in matches[:4]:
                home = match.get('homeTeam', {}).get('name', 'Squadra A')
                away = match.get('awayTeam', {}).get('name', 'Squadra B')
                competition = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                pronostico = "1X o Over 1.5 (Alta Affidabilità)"
                quota = 1.40
                stake_euro = 15
                vincita_possibile = round(stake_euro * quota, 2)
                
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

                schedina_text += f"🏆 *Torneo:* {competition}\n"
                schedina_text += f"{match_title}\n"
                schedina_text += f"🔹 Pronostico: `{pronostico}`\n"
                schedina_text += f"📊 Quota: `{quota}` | 💰 Puntata: `{stake_euro}€`\n"
                schedina_text += f"💵 Vincita Possibile: `{vincita_possibile}€`\n"
                schedina_text += f"📌 Esito: {esito_str}\n\n"
                
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    if not matches_found:
        schedina_text += (
            "⚽ **Top Match Selezionati (Simulazione)**\n\n"
            "1️⃣ **Real Madrid vs Valencia** (La Liga)\n"
            "🔹 Pronostico: 1X | Quota: `1.30` | 💰 Puntata: `15€` | 💵 Vincita: `19.50€`\n"
            "📌 Esito: ⏳ In attesa\n\n"
            "2️⃣ **Arsenal vs Chelsea** (Premier League)\n"
            "🔹 Pronostico: Over 1.5 | Quota: `1.35` | 💰 Puntata: `15€` | 💵 Vincita: `20.25€`\n"
            "📌 Esito: ⏳ In attesa\n\n"
        )
    
    schedina_text += "🍀 *Gioca responsabilmente!*"
    return schedina_text

# 4. Schedina Bomba con Squadre e Vincita Alta
def genera_testo_bomba():
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    quota_bomba = 18.50
    puntata_bomba = 5
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)
    
    testo = (
        f"💣 **SCHEDINA BOMBA DEL GIORNO ({oggi_ita})** 💣\n\n"
        "⚽ *Combinata speciale ad altissimo rendimento*\n\n"
        "1️⃣ **Manchester City vs Real Madrid** (Champions League)\n"
        "   🔹 Cosa giocare: `1 + Over 2.5` (Quota: `2.50`)\n\n"
        "2️⃣ **Barcelona vs Atletico Madrid** (La Liga)\n"
        "   🔹 Cosa giocare: `Goal + Over 2.5` (Quota: `2.45`)\n\n"
        "3️⃣ **Liverpool vs Tottenham** (Premier League)\n"
        "   🔹 Cosa giocare: `1 & Gol` (Quota: `3.00`)\n\n"
        f"📊 **QUOTA TOTALE BOMBA:** `{quota_bomba}`\n"
        f"💰 **Puntata consigliata:** `{puntata_bomba}€`\n"
        f"💵 **VINCITA POSSIBILE:** `{vincita_bomba}€`\n\n"
        "⚠️ *Puntare solo il budget di svago!* 🍀"
    )
    return testo

# 5. Handlers con Pulsanti Integrati
async def cmd_pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_pronostici()
    keyboard = [
        [InlineKeyboardButton("🔄 Aggiorna Partite", callback_data="btn_pronostici")],
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
    
    await query.message.edit_text(f"💥 **KABOOM! ECCO LA BOMBA!** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup)

async def cmd_bomba_testuale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo_bomba = genera_testo_bomba()
    keyboard = [
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"💥 **SCHEDINA BOMBA ATTIVA** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup)

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

    logging.info("Bot avviato con successo con pulsanti permanenti!")
    application.run_polling()

if __name__ == '__main__':
    main()
