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

# ID della chat o del canale in cui inviare la schedina automatica alle 10:00
# (Se vuoi che arrivi a te in chat privata, metti il tuo Chat ID numerico, oppure '@TuoCanale')
TARGET_CHAT_ID = "1220916735" 

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

# Funzione per generare il testo della schedina e della Bomba
def genera_testo_pronostici():
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    # Testo della Schedina Standard con Stake (quanto puntare)
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
        "💣 **--- SCHEDINA BOMBA DEL GIORNO ---** 💣\n"
        "⚽ *Combinata ad alto rendimento*\n"
        "🔹 Segno 1 + Over 2.5 + Multigol\n"
        "📊 **Quota Totale Bomba:** `~8.50`\n"
        "💰 **Stake consigliato:** 1/10 (Tentativo a quota alta)\n\n"
        "⚠️ *Gioca responsabilmente!* 🍀"
    )
    return testo

# 2. Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Benvenuto su **@KingPronostici_bot**! ⚽🔥\n\n"
        "Il tuo bot definitivo per Schedine, Stake di puntata e Schedina Bomba giornaliera!\n"
        "Usa /pronostici per vedere subito i consigli del giorno."
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Comando /pronostici manuale
async def pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo_schedina = genera_testo_pronostici()
    await update.message.reply_text(testo_schedina, parse_mode="Markdown")

# 4. Funzione per l'invio automatico giornaliero delle 10:00
async def invio_automatico_mattutino(context: ContextTypes.DEFAULT_TYPE):
    try:
        testo_schedina = genera_testo_pronostici()
        # Invia il messaggio programmato alla chat impostata
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=f"⏰ **PUBBLICAZIONE AUTOMATICA ORE 10:00** ⏰\n\n{testo_schedina}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Errore nell'invio automatico delle 10:00: {e}")

def main():
    # Avvia il server web in background per Render
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # Costruisce l'applicazione Telegram con il supporto per i Job (orari)
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Configura l'invio automatico ogni giorno alle 10:00 del mattino (orario del server)
    job_queue = application.job_queue
    # time(hour=10, minute=0, second=0) imposta l'orario esatto
    from datetime import time
    job_queue.run_daily(invio_automatico_mattutino, time=time(hour=10, minute=0, second=0))

    # Registra i comandi
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pronostici", pronostici))

    logging.info("Bot avviato con successo in modalità polling con Job Queue attiva!")
    application.run_polling()

if __name__ == '__main__':
main()
