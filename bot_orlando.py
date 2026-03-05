import os
import logging
import time
import sqlite3
import random
import string
from datetime import datetime
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# === CONFIGURACIÓN ===
TOKEN = os.environ.get("TOKEN")
BOT_USERNAME = "@BacaraRealBot"
CREADOR_ID = int(os.environ.get("CREADOR_ID", 0))
URL_BIENVENIDA = "https://maddielp020-web.github.io/bacara-real/"

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
    
    # Tabla de jugadores (con campo codigo_invitado)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jugadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            codigo_invitado TEXT UNIQUE,
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

# === FUNCIONES AUXILIARES ===
def generar_codigo_unico(admin_codigo):
    """Genera código único formato: INV-ADMIN001-XXXX-YY"""
    # Limpiar el código del admin (quitar guiones bajos si los hay)
    admin_clean = admin_codigo.replace("_", "")
    
    # Generar 4 caracteres aleatorios (mayúsculas y números)
    parte_aleatoria = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Generar 2 dígitos de control
    digitos_control = ''.join(random.choices(string.digits, k=2))
    
    return f"INV-{admin_clean}-{parte_aleatoria}-{digitos_control}"

# === COMANDO /start (CON SOPORTE PARA INVITACIONES Y BOTONES) ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    # Caso 1: Hay argumentos y es una invitación
    if args and args[0].startswith('invite_'):
        codigo_admin = args[0].replace('invite_', '')
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Buscar el admin por su código
        cursor.execute("SELECT id, codigo_admin FROM administradores WHERE codigo_admin = ?", (codigo_admin,))
        admin = cursor.fetchone()
        
        if admin:
            admin_id = admin[0]
            admin_codigo = admin[1]
            
            # Verificar si el jugador ya está registrado
            cursor.execute("SELECT id FROM jugadores WHERE telegram_id = ?", (user.id,))
            jugador_existente = cursor.fetchone()
            
            if jugador_existente:
                conn.close()
                # Jugador ya registrado - ofrecer obtener código
                keyboard = [[InlineKeyboardButton("🎟️ Obtener mi código de invitación", callback_data="micodigo")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"👋 Bienvenido de nuevo, {user.first_name}.\n\n"
                    f"Ya tienes una cuenta registrada en Bacará Real.\n"
                    f"Presiona el botón para obtener tu código de invitación.",
                    reply_markup=reply_markup
                )
                return
            else:
                # Nuevo jugador - guardar con el admin que lo invitó
                cursor.execute('''
                    INSERT INTO jugadores (telegram_id, admin_id, fecha_registro)
                    VALUES (?, ?, ?)
                ''', (user.id, admin_id, datetime.now()))
                conn.commit()
                conn.close()
                
                # Botón para que presione /start
                keyboard = [[InlineKeyboardButton("🎮 /start", callback_data="iniciar")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"🎮 **Bienvenido al bot de Bacará Real**\n\n"
                    f"Has llegado mediante una invitación especial.\n\n"
                    f"Para comenzar, presiona el botón **/start**.",
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                print(f"✅ Nuevo jugador registrado: {user.first_name} (ID: {user.id}) invitado por {admin_codigo}")
                return
        else:
            conn.close()
            await update.message.reply_text(
                "❌ **Código de invitación inválido**\n\n"
                "El código de administrador que has usado no existe.\n"
                "Por favor, contacta al administrador para obtener un enlace válido.",
                parse_mode="Markdown"
            )
            return
    
    # Caso 2: /start normal (sin argumentos o sin invitación)
    # Verificar si el usuario ya está registrado como jugador
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM jugadores WHERE telegram_id = ?", (user.id,))
    jugador = cursor.fetchone()
    conn.close()
    
    if jugador:
        # Usuario ya registrado - ofrecer obtener código
        keyboard = [[InlineKeyboardButton("🎟️ Obtener mi código de invitación", callback_data="micodigo")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🎰 Bienvenido, {user.first_name}.\n\n"
            f"Este es el bot oficial de Bacará Real.\n"
            f"Presiona el botón para obtener tu código de invitación.",
            reply_markup=reply_markup
        )
    else:
        # Usuario no registrado - mensaje genérico
        await update.message.reply_text(
            f"🎰 Bienvenido, {user.first_name}.\n\n"
            "Este es el bot oficial de Bacará Real.\n"
            "Para jugar necesitas un enlace de invitación de un administrador."
        )

# === COMANDO /micodigo (NUEVO) ===
async def micodigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Verificar si el jugador está registrado
    cursor.execute('''
        SELECT j.id, j.codigo_invitado, a.codigo_admin 
        FROM jugadores j
        LEFT JOIN administradores a ON j.admin_id = a.id
        WHERE j.telegram_id = ?
    ''', (user.id,))
    jugador = cursor.fetchone()
    
    if not jugador:
        conn.close()
        await update.message.reply_text(
            "❌ No tienes una cuenta registrada.\n\n"
            "Para obtener un código necesitas llegar mediante un enlace de invitación."
        )
        return
    
    jugador_id, codigo_actual, admin_codigo = jugador
    
    # Si ya tiene un código, usar ese
    if codigo_actual:
        codigo = codigo_actual
    else:
        # Generar nuevo código
        codigo = generar_codigo_unico(admin_codigo)
        
        # Guardar en base de datos
        cursor.execute(
            "UPDATE jugadores SET codigo_invitado = ? WHERE id = ?",
            (codigo, jugador_id)
        )
        conn.commit()
    
    conn.close()
    
    # Crear botón para ir a la ventana de bienvenida
    keyboard = [[InlineKeyboardButton("🚪 Ir a ventana de bienvenida", url=URL_BIENVENIDA)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ **Tu código de invitación es:**\n\n"
        f"`{codigo}`\n\n"
        f"**Copia este código.** Lo necesitarás en la ventana de bienvenida.\n\n"
        f"Luego presiona el botón para continuar.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# === COMANDO /mi_enlace (NUEVO - SOLO CREADOR) ===
async def mi_enlace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Solo el creador puede usar este comando
    if user.id != CREADOR_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Buscar el código del admin del creador
    cursor.execute("SELECT codigo_admin FROM administradores WHERE telegram_id = ?", (user.id,))
    admin = cursor.fetchone()
    conn.close()
    
    if not admin:
        await update.message.reply_text(
            "❌ No tienes un código de administrador asociado.\n"
            "Primero debes crearlo con /crear_admin ADMIN_001"
        )
        return
    
    codigo_admin = admin[0]
    enlace = f"https://t.me/{BOT_USERNAME[1:]}?start=invite_{codigo_admin}"
    
    await update.message.reply_text(
        f"🔗 **Tu enlace de invitación es:**\n\n"
        f"{enlace}\n\n"
        f"Comparte este enlace para que nuevos jugadores se registren.",
        parse_mode="Markdown"
    )

# === COMANDO /start deposito (INTACTO) ===
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

# === COMANDO /crear_admin (INTACTO) ===
async def crear_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id != CREADOR_ID:
        await update.message.reply_text("❌ No tienes permiso para usar este comando.")
        return
    
    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n"
            "Usa: /crear_admin CODIGO_ADMIN\n"
            "Ejemplo: /crear_admin ADMIN_001"
        )
        return
    
    codigo = context.args[0].upper()
    
    if not codigo.startswith("ADMIN_") or len(codigo) < 7:
        await update.message.reply_text(
            "❌ El código debe tener formato ADMIN_XXX (ej: ADMIN_001)"
        )
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM administradores WHERE codigo_admin = ?", (codigo,))
    if cursor.fetchone():
        conn.close()
        await update.message.reply_text(f"❌ El código {codigo} ya existe.")
        return
    
    cursor.execute(
        "INSERT INTO administradores (codigo_admin, telegram_id, creado_por) VALUES (?, ?, ?)",
        (codigo, user.id, "CREADOR")
    )
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Administrador {codigo} creado correctamente.")
    print(f"👑 Nuevo admin creado: {codigo} por CREADOR (ID: {user.id})")

# === MANEJADOR DE CALLBACKS (para botones inline) ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "micodigo":
        # Ejecutar comando /micodigo
        await micodigo(update, context)
    elif query.data == "iniciar":
        # Simular que el usuario escribió /start
        await start(update, context)

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
    init_database()
    
    app = Application.builder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("micodigo", micodigo))
    app.add_handler(CommandHandler("mi_enlace", mi_enlace))
    app.add_handler(MessageHandler(filters.Regex('^/start deposito'), start_deposito))
    app.add_handler(CommandHandler("crear_admin", crear_admin))
    
    # Manejador de callbacks para botones inline
    app.add_handler(CallbackQueryHandler(button_callback))

    app.add_error_handler(error_handler)

    print("🤖 Bot Orlando está corriendo con Prioridad 3 completada...")
    app.run_polling()

if __name__ == "__main__":
    Thread(target=run_web).start()
    main()