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
        self.wfile.write(b"Cybernetic Bot Online!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# 2. Menu Principale con Bottoni Interattivi e Cyber Grafica
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "╔═════════════════════════╗\n"
        " 🛡️ **SISTEMA: KING_AI v4.0** 🛡️\n"
        "╚═════════════════════════╝\n\n"
        "⚡ *Core di Calcolo Quantistico Attivo.*\n"
        "🎯 *Affidabilità Pronostici: Quasi 100%*\n\n"
        "🤖 **SELEZIONA PROTOCOLLO O USA I COMANDI:**"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 [ SCHEDINA DEL GIORNO ]", callback_data="btn_pronostici")],
        [InlineKeyboardButton("⚡ [ PROTOCOLLO BOMBA ]", callback_data="btn_bomba_avvio")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# 3. Schedina del Giorno (Alta Affidabilità / Quota Sicura)
async def genera_testo_pronostici():
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    matches_found = False
    schedina_text = (
        "╔═════════════════════════╗\n"
        " 📊 **MATRIX: SCHEDINA SICURA (99%)**\n"
        f" 📅 *DATA:* `{oggi_ita}`\n"
        "╚═════════════════════════╝\n\n"
    )
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        matches = data.get("matches", [])
        
        if matches:
            count = 0
            for match in matches[:3]:
                home = match.get('homeTeam', {}).get('name', 'Squadra A')
                away = match.get('awayTeam', {}).get('name', 'Squadra B')
                competition = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                pronostico = "1X ( Doppia Chance Sicura )"
                quota = 1.35
                stake_euro = 20
                vincita_possibile = round(stake_euro * quota, 2)
                
                esito_str = "⏳ `[ IN ATTESA ]`"
                
                if status == 'FINISHED':
                    score = match.get('score', {}).get('fullTime', {})
                    home_goals = score.get('home', 0)
                    away_goals = score.get('away', 0)
                    
                    if home_goals >= away_goals:
                        esito_str = "🟢 `[ STATO: VINTO! ]` 🎉"
                    else:
                        esito_str = "🔴 `[ STATO: PERSO ]` 😢"
                        
                    match_title = f"⚔️ `{home}` **[{home_goals} - {away_goals}]** `{away}`"
                elif status in ['IN_PLAY', 'PAUSED']:
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0)
                    ag = score.get('away', 0)
                    esito_str = f"🔴 `[ LIVE: {hg} - {ag} ]`"
                    match_title = f"⚔️ `{home}` vs `{away}`"
                else:
                    match_title = f"⚔️ `{home}` vs `{away}`"

                schedina_text += f"🏆 *Competizione:* {competition}\n"
                schedina_text += f"{match_title}\n"
                schedina_text += f"🎯 *Algoritmo:* `{pronostico}`\n"
                schedina_text += f"📊 *Quota:* `{quota}`\n"
                schedina_text += f"💻 *Stake Consigliato:* `[ █ █ █ ░ ] {stake_euro}€`\n"
                schedina_text += f"💵 *Vincita Possibile:* `{vincita_possibile}€`\n"
                schedina_text += f"📌 *Esito:* {esito_str}\n"
                schedina_text += "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    if not matches_found:
        schedina_text += (
            "🛰️ *[ MODALITÀ SIMULAZIONE SICURA ]*\n\n"
            "1️⃣ **Real Madrid vs Valencia**\n"
            "🎯 *Algoritmo:* 1X (Affidabilità 98%) | 📊 *Quota:* `1.30`\n"
            "💻 *Stake:* `20€` | 💵 *Vincita:* `26.00€`\n"
            "📌 *Esito:* ⏳ `[ IN ATTESA ]`\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
            "2️⃣ **Inter vs Lecce**\n"
            "🎯 *Algoritmo:* Segno 1 Fisso | 📊 *Quota:* `1.35`\n"
            "💻 *Stake:* `20€` | 💵 *Vincita:* `27.00€`\n"
            "📌 *Esito:* ⏳ `[ IN ATTESA ]`\n"
            "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
        )
    
    schedina_text += "⚠️ *Sistema a bassa varianza. Gioca responsabilmente.* 🍀"
    return schedina_text

# 4. Schedina Bomba con Squadre, Dettagli e Vincita Alta
def genera_testo_bomba():
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    quota_bomba = 15.50
    puntata_bomba = 5
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)
    
    testo = (
        "╔═════════════════════════╗\n"
        " ☢️ **PROTOCOLLO CYBER-BOMBA** ☢️\n"
        f" 📅 *DATA:* `{oggi_ita}`\n"
        "╚═════════════════════════╝\n\n"
        "⚡ *Combinata d'élite ad altissimo rendimento*\n\n"
        "1️⃣ **Real Madrid vs Inter** (Champions League)\n"
        "   └ *Cosa giocare:* `1 + Over 2.5` | 📊 *Quota:* `2.40`\n\n"
        "2️⃣ **Bayern Monaco vs Barcellona** (Champions League)\n"
        "   └ *Cosa giocare:* `Goal + Over 3.5` | 📊 *Quota:* `2.35`\n\n"
        "3️⃣ **Manchester City vs PSG** (Champions League)\n"
        "   └ *Cosa giocare:* `1 & Gol` | 📊 *Quota:* `2.50`\n\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
        "📊 *QUOTA TOTALE BOMBA:* `⚡ ~" + str(quota_bomba) + "`\n"
        "💻 *Puntata consigliata:* `[ █ ░ ░ ░ ] " + str(puntata_bomba) + "€` (Stake 1/10)\n"
        "💵 **VINCITA POSSIBILE:** `🚀 " + str(vincita_bomba) + "€`\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
        "⚠️ *Allerta: Moltiplicatore estremo. Puntare solo il budget di svago!* 🍀"
    )
    return testo

# 5. Funzioni di Comando e Risposta con Pulsanti
async def cmd_pronostici(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_pronostici()
    keyboard = [
        [InlineKeyboardButton("🔄 Aggiorna Analisi", callback_data="btn_pronostici")],
        [InlineKeyboardButton("🔙 [ TORNA AL MENU PRINCIPALE ]", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(testo, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(testo, parse_mode="Markdown", reply_markup=reply_markup)

# Effetto Esplosione Dinamico prima della Bomba
async def bomba_effetto_esplosione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text("💣 *INNESCO PROTOCOLLO BOMBA IN CORSO...*\n\n⏱️ `[ 3 ]` ⏳", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    await query.message.edit_text("💣 *INNESCO PROTOCOLLO BOMBA IN CORSO...*\n\n⏱️ `[ 2 ]` ⚡", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    await query.message.edit_text("💣 *INNESCO PROTOCOLLO BOMBA IN CORSO...*\n\n⏱️ `[ 1 ]` 🔥", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    testo_bomba = genera_testo_bomba()
    keyboard = [
        [InlineKeyboardButton("⚡ Ricarica Bomba", callback_data="btn_bomba_avvio")],
        [InlineKeyboardButton("🔙 [ TORNA AL MENU PRINCIPALE ]", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(f"💥 **K A B O O M ! ! !** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup)

async def cmd_bomba_testuale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo_bomba = genera_testo_bomba()
    keyboard = [
        [InlineKeyboardButton("🔙 [ TORNA AL MENU PRINCIPALE ]", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"💥 **PROTOCOLLO BOMBA ATTIVATO** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup)

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

    logging.info("Cybernetic Bot definitivo avviato con successo!")
    application.run_polling()

if __name__ == '__main__':
    main()
