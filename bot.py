import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Il tuo token di Telegram
TOKEN = "8736023738:AAGfnjI9MURTUKNqbG80Pe4_aah4_IyPfpk"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("KingPronostici è online e operativo! ⚽🔥\nUsa /schedina o /superbomba per i pronostici.")

async def schedina(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎯 **SCHEDINA DEL GIORNO**\n1. Inter - Juventus: 1X + Over 1.5\n2. Real Madrid - Barcellona: Goal\nQuota Totale: @2.45")

async def superbomba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💣 **SUPERBOMBA DI OGGI**\nPartita ad alta quota:\nManchester City - Arsenal: X (Quota @3.60)")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("schedina", schedina))
    app.add_handler(CommandHandler("superbomba", superbomba))
    
    print("Bot avviato con successo!")
    app.run_polling()

if __name__ == "__main__":
    main()
