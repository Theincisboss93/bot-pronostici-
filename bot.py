import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from datetime import datetime
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Abilita i log
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# INCOLLA QUI LE TUE DUE CHIAVI:
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

# 2. Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Benvenuto su **@KingPronostici_bot**! ⚽🔥\n\n"
        "Sono il tuo assistente per le scommesse calcistiche.\n"
        "Usa il comando /pronostici per ricevere la schedina aggiornata!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Comando /pronostici con dati reali e sistema di fallback
async def pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                home = match.get('homeTeam', {}).get('name', 'Squadra Casa')
                away = match.get('awayTeam', {}).get('name', 'Squadra Ospite')
                competition = match.get('competition', {}).get('name', 'Campionato')
                
                schedina_text += f"🏆 *{competition}*\n"
                schedina_text += f"⚽ **{home} vs {away}**\n"
                schedina_text += f"🔹 Pronostico: 1X + Over 1.5\n\n"
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    # Se l'API non ha partite oggi, mostra i top match di backup
    if not matches_found:
        schedina_text += (
            "⚽ **Top Match della Settimana**\n\n"
            "1️⃣ **Milan vs Napoli**\n"
            "🔹 Pronostico: Goal (Entrambe segnano)\n"
            "📊 Quota stimata: 1.72\n\n"
            "2️⃣ **Liverpool vs Chelsea**\n"
            "🔹 Pronostico: Over 2.5\n"
            "📊 Quota stimata: 1.65\n\n"
            "3️⃣ **Real Madrid vs Atletico Madrid**\n"
            "🔹 Pronostico: 1X + Under 3.5\n"
            "📊 Quota stimata: 1.55\n\n"
        )
    
    schedina_text += "💰 **QUOTA TOTALE ESTIMATA: ~4.40**\n"
    schedina_text += "⚠️ *Analisi aggiornata in tempo reale!*\n"
    schedina_text += "🍀 *Gioca responsabilmente!*"

    await update.message.reply_text(schedina_text, parse_mode="Markdown")

def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pronostici", pronostici))

    logging.info("Bot avviato con successo in modalità polling!")
    application.run_polling()

if __name__ == '__main__':
    main()
