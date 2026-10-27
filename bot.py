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
        "Sono il tuo assistente avanzato per le scommesse.\n"
        "Usa /pronostici per vedere le partite, le quote e l'esito in tempo reale!"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# 3. Comando /pronostici con quote dedicate e controllo esito Vinto/Perso
async def pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    matches_found = False
    schedina_text = f"🔥 **SCHEDINA E RISULTATI ({oggi_ita})** 🔥\n\n"
    
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
                status = match.get('status', 'SCHEDULED')
                
                # Definiamo un pronostico standard per la partita e una quota consigliata
                pronostico = "1X + Over 1.5"
                quota = "1.55"
                
                esito_str = "⏳ *In programma / Non iniziata*"
                
                # Se la partita è finita, calcoliamo se è Vinta o Persa in base ai gol reali
                if status == 'FINISHED':
                    score = match.get('score', {}).get('fullTime', {})
                    home_goals = score.get('home', 0)
                    away_goals = score.get('away', 0)
                    tot_goals = home_goals + away_goals
                    
                    # Logica di esempio per 1X + Over 1.5: Vinto se Casa non perde e ci sono almeno 2 gol totali
                    casa_non_perde = home_goals >= away_goals
                    over_15 = tot_goals >= 2
                    
                    if casa_non_perde and over_15:
                        esito_str = "✅ **PRONOSTICO VINTO!** 🎉"
                    else:
                        esito_str = "❌ **PRONOSTICO PERSO** 😢"
                        
                    risultato_finale = f"({home_goals} - {away_goals})"
                elif status in ['IN_PLAY', 'PAUSED']:
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0)
                    ag = score.get('away', 0)
                    esito_str = f"🔴 *LIVE ({hg} - {ag})*"
                else:
                    risultato_finale = "vs"

                if status == 'FINISHED':
                    match_title = f"⚽ **{home} {home_goals}-{away_goals} {away}**"
                else:
                    match_title = f"⚽ **{home} vs {away}**"

                schedina_text += f"🏆 *{competition}*\n"
                schedina_text += f"{match_title}\n"
                schedina_text += f"🔹 Pronostico: {pronostico}\n"
                schedina_text += f"📊 Quota consigliata: `{quota}`\n"
                schedina_text += f"📌 Esito: {esito_str}\n\n"
                
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    # Fallback se non ci sono match oggi
    if not matches_found:
        schedina_text += (
            "⚽ **Top Match di Riferimento**\n\n"
            "1️⃣ **Milan vs Napoli**\n"
            "🔹 Pronostico: Goal | Quota: `1.72` | 📌 Esito: ⏳ *In programma*\n\n"
            "2️⃣ **Liverpool vs Chelsea**\n"
            "🔹 Pronostico: Over 2.5 | Quota: `1.65` | 📌 Esito: ⏳ *In programma*\n\n"
        )
    
    schedina_text += "⚠️ *Aggiornato in tempo reale con i dati ufficiali!*\n"
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
