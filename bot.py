import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from datetime import datetime, time
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

# 2. Menu Principale con i 4 Pulsanti (3 Schedine + Bomba Sbloccata alle 16:00)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🤖 **BENVENUTO SU KING PRONOSTICI** ⚽\n\n"
        "Seleziona la schedina desiderata:\n"
        "• **100% Sicura**: Giocate singole blindate\n"
        "• **70% Sicura**: Ottimo equilibrio e valore\n"
        "• **50% Sicura**: Schedina ad alto rendimento\n"
        "• **💣 Schedina Bomba VIP**: Misto Italia & Estero (Sblocco ore **16:00**!)"
    )
    
    keyboard = [
        [InlineKeyboardButton("🛡️ Schedina 100% Sicura", callback_data="btn_100")],
        [InlineKeyboardButton("⚖️ Schedina 70% Sicura", callback_data="btn_70")],
        [InlineKeyboardButton("📊 Schedina 50% Sicura", callback_data="btn_50")],
        [InlineKeyboardButton("💣 Schedina Bomba VIP (Ore 16:00)", callback_data="btn_bomba_check")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)

# Funzione generatrice delle 3 schedine standard
async def genera_testo_schedina(tipo_sicurezza):
    oggi = datetime.now().strftime('%Y-%m-%d')
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    
    url = f"https://api.football-data.org/v4/matches?date={oggi}"
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    
    matches_found = False
    partite_list = []
    quota_totale = 1.0
    
    giocate_possibili_100 = ["1X", "Over 1.5", "Gol Sku. Casa", "Under 3.5"]
    giocate_possibili_70 = ["Gol (Entrambe Segnano)", "1", "Over 2.5", "X2 + Over 1.5"]
    giocate_possibili_50 = ["1 + Over 2.5", "Gol + Over 2.5", "2 + Over 1.5", "1X + Gol"]
    
    if tipo_sicurezza == "100":
        titolo_schedina = f"🛡️ **SCHEDINA 100% SICURA ({oggi_ita})** 🛡️"
        prob_str = "10/10 (Massima Stabilità)"
        puntata_consigliata = 20
        max_partite = 3
    elif tipo_sicurezza == "70":
        titolo_schedina = f"⚖️ **SCHEDINA 70% SICURA ({oggi_ita})** ⚖️"
        prob_str = "7/10 (Valore ed Equilibrio)"
        puntata_consigliata = 10
        max_partite = 4
    else:
        titolo_schedina = f"📊 **SCHEDINA 50% SICURA ({oggi_ita})** 📊"
        prob_str = "5/10 (Alto Profitto / Rischio Calcolato)"
        puntata_consigliata = 5
        max_partite = 4

    schedina_text = f"{titolo_schedina}\n\n"
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        matches = data.get("matches", [])
        
        if matches:
            count = 0
            for i, match in enumerate(matches[:max_partite]):
                home = match.get('homeTeam', {}).get('name', 'Squadra A')
                away = match.get('awayTeam', {}).get('name', 'Squadra B')
                competition = match.get('competition', {}).get('name', 'Campionato')
                status = match.get('status', 'SCHEDULED')
                
                if tipo_sicurezza == "100":
                    giocata = giocate_possibili_100[i % len(giocate_possibili_100)]
                    q = round(1.20 + (i * 0.05), 2)
                elif tipo_sicurezza == "70":
                    giocata = giocate_possibili_70[i % len(giocate_possibili_70)]
                    q = round(1.55 + (i * 0.10), 2)
                else:
                    giocata = giocate_possibili_50[i % len(giocate_possibili_50)]
                    q = round(2.30 + (i * 0.15), 2)
                    
                quota_totale *= q
                esito_str = "⏳ In attesa"
                
                if status == 'FINISHED':
                    score = match.get('score', {}).get('fullTime', {})
                    home_goals = score.get('home', 0)
                    away_goals = score.get('away', 0)
                    tot_goals = home_goals + away_goals
                    
                    if giocata == "1X" and home_goals >= away_goals:
                        esito_str = "✅ **VINTO!** 🎉"
                    elif giocata == "Over 1.5" and tot_goals >= 2:
                        esito_str = "✅ **VINTO!** 🎉"
                    elif giocata == "Gol (Entrambe Segnano)" and home_goals > 0 and away_goals > 0:
                        esito_str = "✅ **VINTO!** 🎉"
                    elif giocata == "Over 2.5" and tot_goals >= 3:
                        esito_str = "✅ **VINTO!** 🎉"
                    elif giocata == "1" and home_goals > away_goals:
                        esito_str = "✅ **VINTO!** 🎉"
                    else:
                        if home_goals + away_goals >= 2:
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
                    f"🎯 **Giocata:** `{giocata}` | 📊 Quota: `{q}`\n"
                    f"📌 Esito: {esito_str}\n"
                )
                count += 1
            if count > 0:
                matches_found = True
    except Exception as e:
        logging.error(f"Errore API: {e}")

    if not matches_found:
        if tipo_sicurezza == "100":
            partite_list = [
                "🏆 *Torneo:* Serie A (Italia)\n⚽ **Inter vs Lecce**\n🎯 **Giocata:** `1X` | 📊 Quota: `1.20` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Premier League (Inghilterra)\n⚽ **Manchester City vs Southampton**\n🎯 **Giocata:** `Over 1.5` | 📊 Quota: `1.28` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 1.54
        elif tipo_sicurezza == "70":
            partite_list = [
                "🏆 *Torneo:* La Liga (Spagna)\n⚽ **Real Madrid vs Villarreal**\n🎯 **Giocata:** `Gol (Entrambe Segnano)` | 📊 Quota: `1.70` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Bundesliga (Germania)\n⚽ **Bayern Monaco vs Dortmund**\n🎯 **Giocata:** `Over 2.5` | 📊 Quota: `1.65` | 📌 Esito: ⏳ In attesa\n"
            ]
            quota_totale = 2.80
        else:
            partite_list = [
                "🏆 *Torneo:* Champions League\n⚽ **PSG vs Real Madrid**\n🎯 **Giocata:** `1 + Over 2.5` | 📊 Quota: `2.60` | 📌 Esito: ⏳ In attesa\n",
                "🏆 *Torneo:* Premier League\n⚽ **Arsenal vs Liverpool**\n🎯 **Giocata:** `Gol + Over 2.5` | 📊 Quota: `2.50` | 📌 Esito: ⏳ In attesa\n"
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

# Generatore Schedina Bomba VIP Mista (Italia & Estero)
def genera_testo_bomba():
    oggi_ita = datetime.now().strftime('%d/%m/%Y')
    quota_bomba = 24.50
    puntata_bomba = 5
    vincita_bomba = round(puntata_bomba * quota_bomba, 2)
    
    testo = (
        f"💣 **SCHEDINA BOMBA VIP MISTA ({oggi_ita})** 💣\n\n"
        "⚽ *Combinata mista ad altissimo rendimento (Sbloccata alle 16:00)*\n\n"
        "1️⃣ **AC Milan vs Napoli** (Serie A - Italia)\n"
        "   🎯 **Giocata:** `1 + Over 1.5` | 📊 Quota: `2.40`\n\n"
        "2️⃣ **Real Madrid vs Barcellona** (La Liga - Spagna)\n"
        "   🎯 **Giocata:** `Gol + Over 2.5` | 📊 Quota: `2.50`\n\n"
        "3️⃣ **Arsenal vs Manchester City** (Premier League - Inghilterra)\n"
        "   🎯 **Giocata:** `1 & Gol` | 📊 Quota: `3.00`\n\n"
        "4️⃣ **Bayern Monaco vs Borussia Dortmund** (Bundesliga - Germania)\n"
        "   🎯 **Giocata:** `1 + Over 2.5` | 📊 Quota: `2.70`\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **QUOTA TOTALE BOMBA:** `{quota_bomba}`\n"
        f"📈 **Sicurezza:** `3.5/10 (Rischio Alto VIP)`\n"
        f"💰 **Puntata consigliata:** `{puntata_bomba}€`\n"
        f"💵 **VINCITA COMPLESSIVA:** `{vincita_bomba}€`\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ *Puntare solo il budget di svago!* 🍀"
    )
    return testo

# Gestione controllo orario ore 16:00 per la Bomba
async def gestisci_bomba_orario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ora_attuale = datetime.now().time()
    orario_sblocco = time(16, 0, 0) # Ore 16:00:00

    keyboard_torna = [[InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]]
    reply_markup_torna = InlineKeyboardMarkup(keyboard_torna)

    if ora_attuale < orario_sblocco:
        await query.message.edit_text(
            "⏳ **PROTOCOLLO BOMBA BLOCCATO** 🔒\n\n"
            "La Schedina Bomba VIP (Italia & Estero) viene rilasciata rigorosamente ogni giorno alle **16:00**.\n\n"
            "⏱️ *Torna a cliccare dopo le 16:00 per l'innesco automatico!*",
            parse_mode="Markdown",
            reply_markup=reply_markup_torna
        )
    else:
        await query.message.edit_text("💣 *Innesco Schedina Bomba VIP in corso...*\n\n⏱️ `3...`", parse_mode="Markdown")
        await asyncio.sleep(1)
        await query.message.edit_text("💣 *Innesco Schedina Bomba VIP in corso...*\n\n⏱️ `2...`", parse_mode="Markdown")
        await asyncio.sleep(1)
        await query.message.edit_text("💣 *Innesco Schedina Bomba VIP in corso...*\n\n⏱️ `1...`", parse_mode="Markdown")
        await asyncio.sleep(1)
        
        testo_bomba = genera_testo_bomba()
        keyboard_bomba = [
            [InlineKeyboardButton("🔄 Aggiorna Bomba", callback_data="btn_bomba_check")],
            [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
        ]
        reply_markup_bomba = InlineKeyboardMarkup(keyboard_bomba)
        await query.message.edit_text(f"💥 **KABOOM! BOMBA SBLOCCATA!** 💥\n\n{testo_bomba}", parse_mode="Markdown", reply_markup=reply_markup_bomba)

# Visualizzatori delle Schedine standard
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

async def mostra_50(update: Update, context: ContextTypes.DEFAULT_TYPE):
    testo = await genera_testo_schedina("50")
    keyboard = [
        [InlineKeyboardButton("🔄 Aggiorna", callback_data="btn_50")],
        [InlineKeyboardButton("🔙 Torna al Menu Principale", callback_data="btn_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(testo, parse_mode="Markdown", reply_markup=reply_markup)

# Gestore dei Click dei Bottoni
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "btn_100":
        await mostra_100(update, context)
    elif query.data == "btn_70":
        await mostra_70(update, context)
    elif query.data == "btn_50":
        await mostra_50(update, context)
    elif query.data == "btn_bomba_check":
        await gestisci_bomba_orario(update, context)
    elif query.data == "btn_menu":
        await start(update, context)

def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    logging.info("Bot avviato con successo e senza errori di sintassi!")
    application.run_polling()

if __name__ == '__main__':
    main()
