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

# 1. Piccolo server web fittizio per accontentare la porta di Render (Piano Free)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# 2. Comando /start del bot Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Sono il tuo bot per i pronostici calcistici @KingPronostici_bot attivo e operativo! ⚽🔥")

def main():
    # Avvia il server web fittizio in un thread separato
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # Costruisce l'applicazione del bot Telegram
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    logging.info("Bot avviato con successo in modalità polling!")
    
    # Avvia il bot
    application.run_polling()

if __name__ == '__main__':
    main()
