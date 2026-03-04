import os
import logging
import time
import sqlite3
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === CONFIGURACIÓN ===
TOKEN = os.environ.get("TOKEN")
BOT_USERNAME = "@BacaraRealBot"
CREADOR_ID = int(os.environ.get("CREADOR_ID", 0))  # Variable de entorno o 0 por defecto

# === BASE DE DATOS ===
DB_NAME = "bacara_real.db"

def init_database():
    """Crea las tablas si no existen"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de administradores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS administradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_admin TEXT UNIQUE NOT NULL,
            telegram_id INTEGER,
            creado_por TEXT NOT NULL,
            fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de jugadores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            codigo_invitado TEXT,
            admin_id INTEGER,
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES administradores(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")

# === LOGS ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === COMANDO /start ===
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

# === COMANDO /crear_admin (SOLO PARA CREADOR) ===
async def crear_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Verificar que sea el creador
    if user.id != CREADOR_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return
    
    # Verificar que se proporcionó un código
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n"
            "Usa: /crear_admin CODIGO_ADMIN\n"
            "Ejemplo: /crear_admin ADMIN_001"
        )
        return
    
    codigo = context.args[0].upper()
    
    # Validar formato del código (ADMIN_XXX)
    if not codigo.startswith("ADMIN_") or len(codigo) < 7:
        await update.message.reply_text(
            "❌ El código debe tener formato ADMIN_XXX (ej: ADMIN_001)"
        )
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Verificar si el código ya existe
    cursor.execute("SELECT id FROM administradores WHERE codigo_admin = ?", (codigo,))
    if cursor.fetchone():
        conn.close()
        await update.message.reply_text(f"❌ El código {codigo} ya existe.")
        return
    
    # Insertar nuevo administrador
    cursor.execute(
        "INSERT INTO administradores (codigo_admin, telegram_id, creado_por) VALUES (?, ?, ?)",
        (codigo, user.id, "CREADOR")
    )
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Administrador {codigo} creado correctamente.")
    print(f"👑 Nuevo admin creado: {codigo} por CREADOR (ID: {user.id})")

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
    # Inicializar base de datos
    init_database()
    
    app = Application.builder().token(TOKEN).build()

    # Comandos existentes (INTACTOS)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex('^/start deposito'), start_deposito))
    
    # NUEVO COMANDO: /crear_admin
    app.add_handler(CommandHandler("crear_admin", crear_admin))

    # Errores
    app.add_error_handler(error_handler)

    print("🤖 Bot Orlando está corriendo...")
    app.run_polling()

if __name__ == "__main__":
    # Iniciar el servidor web en un hilo separado
    Thread(target=run_web).start()
    # Iniciar el bot
    main()