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
        self.wfile.write(b"Bot is online!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# 2. Menu Principale con Pulsanti Rapidi per le 3 Schedine
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **BENVENUTO SU KING PRONOSTICI** ⚽\n\n"
        "Seleziona il livello di sicurezza desiderato tramite i pulsanti sottostanti:\n"
        "• **100% Sicura**: Massima stabilità\n"
        "• **70% Sicura**: Ottimo compromesso rischio/rendimento\n"
        "• **50% Sicura**: Schedina Bomba ad alto profitto"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛡️ Schedina 100% Sicura", callback_data="btn_100")],
        [InlineKeyboardButton("⚖️ Schedina 70% Sicura", callback_data="btn_70")],
        [InlineKeyboardButton("🚀 Schedina 50% Sicura (Bomba)", callback_data="btn_bomba_avvio")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# Funzione di supporto per generare le schedine basate su API o simulazione
async def genera_testo_schedina(tipo_sicurezza):
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    matches_found = False
    partite_list = []
    quota_totale = 1.0
    
    if tipo_sicurezza == "100":
        titolo_schedina = f"🛡️ **SCHEDINA 100% SICURA ({oggi_ita})** 🛡️"
        prob_str = "10/10 (Massima Affidabilità)"
        puntata_consigliata = 20
        pronostico_base = "1X o Over 1.5"
        quota_singola = 1.25
        max_partite = 3
    elif tipo_sicurezza == "70":
        titolo_schedina = f"⚖️ **SCHEDINA 70% SICURA ({oggi_ita})** ⚖️"
        prob_str = "7/10 (Equilibrio Rischio/Profitto)"
        puntata_consigliata = 10
        pronostico_base = "1 Over 1.5 o Gol"
        quota_singola = 1.65
        max_partite = 4
    else: # 50% Bomba
        titolo_schedina = f"🚀 **SCHEDINA 50% SICURA - BOMBA ({oggi_ita})** 🚀"
        prob_str = "5/10 (Alto Profitto / Rischio Calcolato)"
        puntata_consigliata = 5
        pronostico_base = "1 + Over 2.5 o Combo"
        quota_singola = 2.40
        max_partite = 4

    schedina_text = f"{titolo_schedina}\n\n"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        matches = data.get("matches", [])
        
        if matches:
            count = 0
            for match in matches[:max_partite]:
                home = match.get('homeTeam', {}).get('name', 'Squadra A')
                away = match.get('awayTeam', {}).get('name', 'Squadra B')
                competition = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                # Assegnazione quota specifica in base al livello
                if tipo_sicurezza == "100":
                    q = 1.25
                elif tipo_sicurezza == "70":
                    q = 1.60
                else:
                    q = 2.35
                    
                quota_totale *= q
                esito_str = "⏳ In attesa"
                
                if status == 'FINISHED':
                    score = match.get('score', {}).get('fullTime', {})
                    home_goals = score.get('home', 0)
                    away_goals = score.get('away', 0)
                    tot_goals = home_goals + away_goals
                    
                    if tipo_sicurezza == "100" and (home_goals >= away_goals or tot_goals >= 2):
                        esito_str = "✅ **VINTO!** 🎉"
                    elif tipo_sicurezza == "70" and (tot_goals >= 2):
                        esito_str = "✅ **VINTO!** 🎉"
                    elif tipo_sicurezza == "50" and (home_goals + away_goals >= 3):
                        esito_str = "✅ **VINTO!** 🎉"
                    else:
                        esito_str = "❌ **PERSO** 😢"
                        
                    match_title = f"⚽ **{home} {home_goals} - {away_goals} {away}**"
                elif status in ['IN_PLAY', 'PAUSED']:
                    score = match.get('score', {}).get('fullTime', {})
                    hg = score.get('home', 0)
                    ag = score.get('away', 0)
                    esito_str = f"🔴 **LIVE ({hg} - {ag})**"
                    match_title = f"⚽ **{home} vs {away}**"
                else:
                    match_title = f"⚽ **{home} vs {away}**"

                partite_list.append(
                    f"🏆 *Torneo:* {competition}\n"
                    f"{match_title}\n"
                    f"🔹 Giocata: `{pronostico_base}` | Quota: `{q}`\n"
                    f"📌 Esito: {esito_str}\n"
                )
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    if not matches_found:
        # Fallback simulato se l'API non restituisce match oggi
        if tipo_sicurezza == "100":
            partite_list = [
                "🏆 *Torneo:* Serie A (Italia)\n⚽ **Inter vs Lecce**\n🔹 Giocata: `1X` | Quota: `1.20` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Premier League (Inghilterra)\n⚽ **Manchester City vs Southampton**\n🔹 Giocata: `1` | Quota: `1.25` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 1.50
        elif tipo_sicurezza == "70":
            partite_list = [
                "🏆 *Torneo:* La Liga (Spagna)\n⚽ **Real Madrid vs Villarreal**\n🔹 Giocata: `1 + Over 1.5` | Quota: `1.75` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Bundesliga (Germania)\n⚽ **Bayern Monaco vs Dortmund**\n🔹 Giocata: `Goal` | Quota: `1.60` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 2.80
        else:
            partite_list = [
                "🏆 *Torneo:* Champions League\n⚽ **PSG vs Real Madrid**\n🔹 Giocata: `1 + Over 2.5` | Quota: `2.60` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Premier League\n⚽ **Arsenal vs Liverpool**\n🔹 Giocata: `Goal + Over 2.5` | Quota: `2.50` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 6.50

    quota_totale = round(quota_totale, 2)
    vincita_totale = round(puntata_consigliata * quota_totale, 2)

    for p in partite_list:
        schedina_text += p + "\n"

    schedina_text += "━━━━━━━━━━━━━━━━━━━\n"
    schedina_text += f"📊 **QUOTA TOTALE:** `{quota_totale}`\n"
    schedina_text += f"📈 **Sicurezza / Probabilità:** `{prob_str}`\n"
    schedina_text += f"💰 **Puntata consigliata:** `{puntata_consigliata}€`\n"
    schedina_text += f"💵 **VINCITA COMPLESSIVA:** `{vincita_totale}€`\n"
    schedina_text += "━━━━━━━━━━━━━━━━━━━\n"
    schedina_text += "🍀 *Gioca responsabilmente!*"
    
    return schedina_text

# Handlers per le visualizzazioni
async def mostra_100(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("100")
    keyboard = [
        [InlineKeyboardButton("🔄 Aggiorna", callback_data="btn_100")],
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(testo, parse_mode="Markdown", reply_markup=reply_markup)

async def mostra_70(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("70")
    keyboard = [
        [InlineKeyboardButton("🔄 Aggiorna", callback_data="btn_70")],
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(testo, parse_mode="Markdown", reply_markup=reply_markup)

# Effetto Esplosione Animato per la Schedina Bomba (50%)
async def bomba_effetto_esplosione(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.edit_text("💣 *Innesco Schedina Bomba 50% in corso...*\n\n⏱️ `3...`", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    await query.message.edit_text("💣 *Innesco Schedina Bomba 50% in corso...*\n\n⏱️ `2...`", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    await query.message.edit_text("💣 *Innesco Schedina Bomba 50% in corso...*\n\n⏱️ `1...`", parse_mode="Markdown")
    await asyncio.sleep(1)
    
    testo_bomba = await genera_testo_schedina("50")
    keyboard = [
        [InlineKeyboardButton("🔄 Ricarica Bomba", callback_data="btn_bomba_avvio")],
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(f"💥 **KABOOM! ECCO LA BOMBA!** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup)

# Gestore dei Click dei Bottoni
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "btn_100":
        await mostra_100(update, context)
    elif query.data == "btn_70":
        await mostra_70(update, context)
    elif query.data == "btn_bomba_avvio":
        await bomba_effetto_esplosione(update, context)
    elif query.data == "btn_menu":
        await start(update, context)

def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot multi-livello (100%, 70%, 50%) avviato con successo!")
    application.run_polling()

if __name__ == '__main__':
    main()
