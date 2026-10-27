import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from datetime import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# Abilita i log
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# CHIAVI CONFIGURATE CORRETTAMENTE
TOKEN = "8736023738:AAGfnjI9MURTUKNqbG80Pe4_aah4_IyPfpk"
FOOTBALL_API_KEY = "be001fd3625a4f84b61b28e26ba101b2"

# 1. Server web fittizio per Render (Piano Free)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# 2. Comando /start con pulsanti interattivi grafici
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👑 **BENVENUTO SU KING PRONOSTICI** 👑\n\n"
        "⚡ *Il tuo canale d'élite per schedine ad alta precisione con stake e vincite stimate.*\n"
        "Seleziona una delle opzioni qui sotto per iniziare 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Schedina del Giorno", callback_data="btn_pronostici")],
        [InlineKeyboardButton("💣 Schedina Bomba (Quota Alta)", callback_data="btn_bomba")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# 3. Funzione per generare la Schedina del Giorno con Stake e Vincita
async def genera_testo_pronostici():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    matches_found = False
    schedina_text = f"━━━━━━━━━━━━━━━━━━━━━\n" \
                    f"🔥 **ANALISI & SCHEDINA DEL GIORNO** ⚡\n" \
                    f"📅 *Data:* `{oggi_ita}`\n" \
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        matches = data.get("matches", [])
        
        if matches:
            count = 0
            for match in matches[:3]:
                home = match.get('homeTeam', {}).get('name', 'Squadra Casa')
                away = match.get('awayTeam', {}).get('name', 'Squadra Ospite')
                competition = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                pronostico = "1X + Over 1.5"
                quota = 1.55
                stake_euro = 10  # 10€ consigliati di puntata
                vincita_possibile = round(stake_euro * quota, 2)
                
                esito_str = "⏳ *In attesa di inizio*"
                
                if status == 'FINISHED':
                    score = match.get('score', {}).get('fullTime', {})
                    home_goals = score.get('home', 0)
                    away_goals = score.get('away', 0)
                    tot_goals = home_goals + away_goals
                    
                    casa_non_perde = home_goals >= away_goals
                    over_15 = tot_goals >= 2
                    
                    if casa_non_perde and over_15:
                        esito_str = "✅ **ESITO: VINTO!** 🎉"
                    else:
                        esito_str = "❌ **ESITO: PERSO** 😢"
                        
                    match_title = f"⚽ `{home}` **{home_goals} - {away_goals}** `{away}`"
                elif status in ['IN_PLAY', 'PAUSED']:
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0)
                    ag = score.get('away', 0)
                    esito_str = f"🔴 **LIVE IN CORSO** `({hg} - {ag})`"
                    match_title = f"⚽ `{home}` vs `{away}`"
                else:
                    match_title = f"⚽ `{home}` vs `{away}`"

                schedina_text += f"🏆 *{competition}*\n"
                schedina_text += f"{match_title}\n"
                schedina_text += f"🎯 *Pronostico:* `{pronostico}`\n"
                schedina_text += f"📊 *Quota:* `{quota}`\n"
                schedina_text += f"💰 *Puntata consigliata:* `{stake_euro}€` (Stake 4/10)\n"
                schedina_text += f"💵 *Vincita possibile:* `{vincita_possibile}€`\n"
                schedina_text += f"📌 *Stato:* {esito_str}\n"
                schedina_text += f"─────────────────────\n\n"
                
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    # Fallback se non ci sono partite oggi
    if not matches_found:
        q1, s1, v1 = 1.55, 10, 15.50
        q2, s2, v2 = 1.70, 10, 17.00
        schedina_text += (
            "🌟 *Top Match Selezionati dagli Esperti* 🌟\n\n"
            "1️⃣ **Milan vs Napoli**\n"
            "🎯 *Pronostico:* 1X + Over 1.5 | 📊 *Quota:* `{}`\n"
            "💰 *Puntata:* `{}€` | 💵 *Vincita:* `{}€`\n"
            "📌 *Stato:* ⏳ *In programma*\n"
            "─────────────────────\n\n"
            "2️⃣ **Liverpool vs Chelsea**\n"
            "🎯 *Pronostico:* Goal | 📊 *Quota:* `{}`\n"
            "💰 *Puntata:* `{}€` | 💵 *Vincita:* `{}€`\n"
            "📌 *Stato:* ⏳ *In programma*\n"
            "─────────────────────\n\n".format(q1, s1, v1, q2, s2, v2)
        )
    
    schedina_text += "⚠️ *Gioca con responsabilità. Il gioco è vietato ai minori.* 🍀"
    return schedina_text

# 4. Funzione per la Schedina Bomba con calcolo vincita ad alta quota
def genera_testo_bomba():
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    quota_bomba = 8.50
    puntata_bomba = 5  # 5€ di tentativo consigliato sulla bomba
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)
    
    testo = (
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💣 **AREA VIP: SCHEDINA BOMBA** 💣\n"
        f"📅 *Data:* `{oggi_ita}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 *Combinata speciale ad alto moltiplicatore*\n\n"
        "🔹 **Combo 1:** 1 + Over 1.5\n"
        "🔹 **Combo 2:** Goal Squadra Ospite\n"
        "🔹 **Combo 3:** Multigol 2-4\n\n"
        "📊 *Quota Totale:* `{}`\n"
        "💰 *Puntata consigliata:* `{}€` (Stake 1/10)\n"
        "💵 **VINCITA POSSIBILE:** `⚡ {}€`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *Puntare solo il budget di svago!* 🍀".format(quota_bomba, puntata_bomba, vincita_bomba)
    )
    return testo

# 5. Handler per i comandi e i pulsanti
async def pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_pronostici()
    keyboard = [[InlineKeyboardButton("🔙 Torna al Menu", callback_data="btn_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(testo, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(testo, parse_mode="Markdown", reply_markup=reply_markup)

async def bomba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = genera_testo_bomba()
    keyboard = [[InlineKeyboardButton("🔙 Torna al Menu", callback_data="btn_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(testo, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(testo, parse_mode="Markdown", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "btn_pronostici":
        await pronostici(update, context)
    elif query.data == "btn_bomba":
        await bomba(update, context)
    elif query.data == "btn_menu":
        await start(update, context)

def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pronostici", pronostici))
    application.add_handler(CommandHandler("bomba", bomba))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot con calcolo vincite avviato con successo!")
    application.run_polling()

if __name__ == '__main__':
    main()
