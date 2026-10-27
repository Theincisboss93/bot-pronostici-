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

# 2. Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Benvenuto su **@KingPronostici_bot**! ⚽🔥\n\n"
        "Ecco i comandi disponibili:\n"
        "📊 /pronostici - Per ricevere la schedina del giorno con gli stake di puntata\n"
        "💣 /bomba - Per scoprire la Schedina Bomba ad alta quota\n\n"
        "Usa i comandi quando vuoi!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Comando /pronostici (Schedina standard e stake)
async def pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    testo = (
        f"🔥 **SCHEDINA DEL GIORNO ({oggi_ita})** 🔥\n\n"
        "⚽ **Partite Selezionate & Analisi:**\n\n"
        "1️⃣ **Match Principale**\n"
        "🔹 Pronostico: 1X + Over 1.5\n"
        "📊 Quota consigliata: `1.55`\n"
        "💰 **Stake consigliato:** 4/10 (Moderata)\n\n"
        "2️⃣ **Match Secondario**\n"
        "🔹 Pronostico: Goal (Entrambe segnano)\n"
        "📊 Quota consigliata: `1.70`\n"
        "💰 **Stake consigliato:** 3/10 (Tranquilla)\n\n"
        "⚠️ *Gioca responsabilmente!* 🍀"
    )
    await update.message.reply_text(testo, parse_mode="Markdown")

# 4. Comando /bomba (Schedina Bomba ad alta quota)
async def bomba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    testo = (
        f"💣 **SCHEDINA BOMBA DEL GIORNO ({oggi_ita})** 💣\n\n"
        "⚽ *Combinata speciale ad alto rendimento*\n\n"
        "🔹 Evento 1: Segno 1 + Over 2.5\n"
        "🔹 Evento 2: Combo Gol + Over 1.5\n"
        "🔹 Evento 3: Risultato Esatto Multiplo / X2\n\n"
        "📊 **QUOTA TOTALE BOMBA:** `~8.50`\n"
        "💰 **Stake consigliato:** 1/10 (Tentativo a quota alta)\n\n"
        "⚠️ *Gioca con moderazione e testa!* 🍀"
    )
    await update.message.reply_text(testo, parse_mode="Markdown")

def main():
    # Avvia il server web in background per Render
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # Costruisce l'applicazione Telegram
    application = ApplicationBuilder().token(TOKEN).build()

    # Registra i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pronostici", pronostici))
    application.add_handler(CommandHandler("bomba", bomba))

    logging.info("Bot avviato con successo!")
    application.run_polling()

if __name__ == '__main__':
    main()
