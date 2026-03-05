# ==================== INVITACIONES - FLUJO COMPLETO ====================
# Este archivo contiene TODA la lógica de invitaciones (Prioridad 3)
# Independiente del bot principal - Se importa desde bot_orlando.py

import random
import string
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

# === CONFIGURACIÓN ===
DB_NAME = "bacara_real.db"
URL_BIENVENIDA = "https://maddielp020-web.github.io/bacara-real/"

# === FUNCIÓN AUXILIAR ===
def generar_codigo_unico(admin_codigo):
    """
    Genera código único formato: INV-ADMIN001-XXXX-YY
    Ejemplo: INV-ADMIN001-A7K9-3F
    """
    # Limpiar el código del admin (quitar guiones bajos)
    admin_clean = admin_codigo.replace("_", "")
    
    # Generar 4 caracteres aleatorios (mayúsculas y números)
    parte_aleatoria = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Generar 2 dígitos de control
    digitos_control = ''.join(random.choices(string.digits, k=2))
    
    return f"INV-{admin_clean}-{parte_aleatoria}-{digitos_control}"

# === COMANDO /micodigo ===
async def micodigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para que el jugador obtenga su código único"""
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
            "❌ **No tienes una cuenta registrada**\n\n"
            "Para obtener un código necesitas llegar mediante un enlace de invitación.\n\n"
            "Solicita un enlace a un administrador.",
            parse_mode="Markdown"
        )
        return
    
    jugador_id, codigo_actual, admin_codigo = jugador
    
    # Si ya tiene un código, usar ese (no generar duplicado)
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
    
    # Mensaje ULTRA CLARO, paso a paso
    mensaje = (
        f"✅ **¡YA TIENES TU CÓDIGO!**\n\n"
        f"**Tu código de invitación es:**\n"
        f"`{codigo}`\n\n"
        f"📌 **IMPORTANTE:**\n"
        f"• **Copia este código** exactamente como aparece\n"
        f"• Lo necesitarás en la ventana de bienvenida\n\n"
        f"👉 **Ahora presiona el botón de abajo** para ir a la ventana de bienvenida.\n"
        f"Allí deberás pegar el código y continuar."
    )
    
    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# === CALLBACKS PARA BOTONES ===
async def callback_micodigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta /micodigo cuando se presiona el botón"""
    query = update.callback_query
    await query.answer()
    await micodigo(update, context)

async def callback_iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simula que el usuario escribió /start"""
    query = update.callback_query
    await query.answer()
    # Reutilizamos el comando start existente
    from bot_orlando import start
    await start(update, context)

# === FUNCIÓN PARA MODIFICAR EL MENSAJE DE INVITACIÓN ===
def mensaje_invitacion_con_boton(admin_codigo):
    """
    Retorna el mensaje de bienvenida para invitados CON BOTÓN
    Esta función será llamada desde bot_orlando.py
    """
    keyboard = [[InlineKeyboardButton("🎮 Presiona aquí para comenzar", callback_data="iniciar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensaje = (
        f"🎮 **¡BIENVENIDO A BACARÁ REAL!**\n\n"
        f"Has llegado mediante una invitación especial del administrador **{admin_codigo}**.\n\n"
        f"📌 **INSTRUCCIONES (muy fáciles):**\n\n"
        f"1️⃣ Presiona el botón de abajo **'Presiona aquí para comenzar'**\n"
        f"2️⃣ El bot te dará la bienvenida y te mostrará un nuevo botón\n"
        f"3️⃣ Presiona ese botón para obtener **tu código personal**\n"
        f"4️⃣ Copia el código y ve a la ventana de bienvenida\n\n"
        f"👉 **¡Es muy fácil!** Solo sigue los pasos."
    )
    
    return mensaje, reply_markup

# === FUNCIÓN PARA MODIFICAR RESPUESTA DE /start PARA JUGADORES ===
def mensaje_start_con_boton():
    """
    Retorna el mensaje para jugadores ya registrados CON BOTÓN para obtener código
    """
    keyboard = [[InlineKeyboardButton("🎟️ Obtener mi código de invitación", callback_data="micodigo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensaje = (
        f"👋 **¡HOLA DE NUEVO!**\n\n"
        f"Ya tienes una cuenta registrada en Bacará Real.\n\n"
        f"📌 **¿QUÉ SIGUE?**\n\n"
        f"1️⃣ Presiona el botón **'Obtener mi código'**\n"
        f"2️⃣ El bot generará tu código personal\n"
        f"3️⃣ Copia ese código y ve a la ventana de bienvenida\n\n"
        f"👉 **Es rápido y sencillo.** Presiona el botón."
    )
    
    return mensaje, reply_markup

# === SETUP: REGISTRAR COMANDOS Y CALLBACKS ===
def setup_invitaciones(app):
    """
    Registra todos los handlers de invitaciones en la aplicación
    Esta función se llama desde bot_orlando.py
    """
    # Comandos
    app.add_handler(CommandHandler("micodigo", micodigo))
    
    # Callbacks para botones
    app.add_handler(CallbackQueryHandler(callback_micodigo, pattern="^micodigo$"))
    app.add_handler(CallbackQueryHandler(callback_iniciar, pattern="^iniciar$"))
    
    print("✅ Módulo de invitaciones cargado correctamente")