import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

# Abilita i log per vedere cosa succede
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# INCOLLA QUI IL NUOVO TOKEN CHE TI HA DATO BOTFATHER TRA LE VIRGOLETTE
TOKEN = "8736023738:AAGfnjI9MURTUKNqbG80Pe4_aah4_IyPfpk"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Sono il tuo bot per i pronostici calcistici @KingPronostici_bot attivo e operativo! ⚽🔥")

def main():
    # Costruisce l'applicazione del bot
    application = ApplicationBuilder().token(TOKEN).build()

    # Aggiunge il comando /start
    application.add_handler(CommandHandler("start", start))

    print("Bot avviato con successo!")
    
    # Avvia il bot in modalità polling continuo
    application.run_polling()

if __name__ == '__main__':
    main()
