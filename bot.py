import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Abilita i log
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "8736023738:AAGfnjI9MURTUKNqbG80Pe4_aah4_IyPfpk"

# 1. Server web fittizio per mantenere attivo il Web Service gratuito su Render
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
        "Sono il tuo assistente personale per le scommesse calcistiche.\n"
        "Usa il comando /pronostici per ricevere la schedina del giorno studiata per te!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Comando /pronostici (La Schedina del Giorno)
async def pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    schedina_text = (
        "🔥 **SCHEDINA DEL GIORNO** 🔥\n\n"
        "⚽ **Inter - Juventus**\n"
        "🔹 Pronostico: 1X + Over 1.5\n"
        "📊 Quota stimata: 1.55\n\n"
        "⚽ **Real Madrid - Barcellona**\n"
        "🔹 Pronostico: Goal (Entrambe segnano)\n"
        "📊 Quota stimata: 1.65\n\n"
        "⚽ **Manchester City - Arsenal**\n"
        "🔹 Pronostico: 1 (Vittoria Casa)\n"
        "📊 Quota stimata: 1.80\n\n"
        "💰 **QUOTA TOTALE: ~4.60**\n"
        "⚠️ *Gioca responsabilmente!*"
    )
    await update.message.reply_text(schedina_text, parse_mode="Markdown")

def main():
    # Avvia il server web in un thread separato
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # Configura il bot Telegram
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Registra i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pronostici", pronostici))

    logging.info("Bot avviato con successo in modalità polling!")
    
    # Avvia il bot
    application.run_polling()

if __name__ == '__main__':
    main()
