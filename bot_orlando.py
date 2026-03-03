import os
import logging
import time
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === CONFIGURACIÓN ===
TOKEN = os.environ.get("TOKEN")
BOT_USERNAME = "@BacaraRealBot"

# === LOGS (para ver errores en Render) ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === MENSAJE DE BIENVENIDA ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🎰 Bienvenido, {user.first_name}.\n\n"
        "Este es el bot oficial de Bacará Real.\n"
        "Usa los botones del lobby para navegar."
    )

# === COMANDO /start deposito ===
async def start_deposito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Aquí podrías guardar en BD más adelante
    print(f"🧾 Solicitud de compra de {user.first_name} (ID: {user_id})")

    await update.message.reply_text(
        "💰 **COMPRA DE FICHAS**\n\n"
        "Has solicitado comprar fichas para jugar.\n\n"
        "Para continuar, necesitas:\n\n"
        "1. Transferir el dinero a esta tarjeta (pronto te daré los datos definitivos, por ahora son de prueba)\n"
        "2. Enviar el comprobante en PDF aquí mismo\n"
        "3. Esperar la confirmación\n\n"
        "Este es un mensaje temporal. Pronto actualizaremos con las instrucciones reales.\n\n"
        "Gracias por tu paciencia.",
        parse_mode="Markdown"
    )

# === MANEJADOR DE ERRORES ===
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error: {context.error}")

# === SERVIDOR WEB FALSO PARA RENDER ===
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running"

def run_web():
    app_flask.run(host='0.0.0.0', port=10000)

# === MAIN: INICIAR BOT ===
def main():
    app = Application.builder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_deposito", start_deposito))

    # Errores
    app.add_error_handler(error_handler)

    print("🤖 Bot Orlando está corriendo...")
    app.run_polling()

if __name__ == "__main__":
    # Iniciar el servidor web en un hilo separado
    Thread(target=run_web).start()
    # Iniciar el bot
    main()