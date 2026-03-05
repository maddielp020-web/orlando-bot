# ==================== INVITACIONES - FLUJO COMPLETO ====================
# Archivo independiente con toda la lógica de invitaciones
# Prioridad 3 - Flujo completo para jugadores
# Versión corregida por arquitecto

import random
import string
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

# === CONFIGURACIÓN ===
DB_NAME = "bacara_real.db"
URL_BIENVENIDA = "https://maddielp020-web.github.io/bacara-real/"

# Variable global para la función start (evita dependencia circular)
_start_function = None

def set_start_function(func):
    """Guarda referencia a la función start del bot principal"""
    global _start_function
    _start_function = func
    print("✅ Función start registrada en módulo de invitaciones")

# ============================================
# FUNCIÓN AUXILIAR: GENERAR CÓDIGO ÚNICO
# ============================================
def generar_codigo_unico(admin_codigo):
    """
    Genera un código único con formato: INV-ADMIN001-XXXX-YY
    - ADMIN001: código del admin que invitó (sin guiones bajos)
    - XXXX: 4 caracteres aleatorios (mayúsculas + números)
    - YY: 2 dígitos de control
    """
    # Limpiar el código del admin (quitar guiones bajos si los hay)
    admin_clean = admin_codigo.replace("_", "")
    
    # Generar 4 caracteres aleatorios (mayúsculas y números)
    parte_aleatoria = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    # Generar 2 dígitos de control
    digitos_control = ''.join(random.choices(string.digits, k=2))
    
    return f"INV-{admin_clean}-{parte_aleatoria}-{digitos_control}"

# ============================================
# MENSAJE PARA INVITADO NUEVO (CON BOTÓN /start)
# ============================================
def mensaje_invitacion_con_boton(admin_codigo):
    """
    Mensaje que ve el jugador cuando llega por primera vez mediante un enlace de invitación.
    Incluye un botón para presionar /start.
    """
    texto = (
        f"🎮 **¡BIENVENIDO A BACARÁ REAL!**\n\n"
        f"Has llegado mediante una invitación especial del administrador **{admin_codigo}**.\n\n"
        f"📌 **PASO 1:**\n"
        f"Presiona el botón **/start** que aparece abajo para comenzar el proceso.\n\n"
        f"👇👇👇"
    )
    
    keyboard = [[InlineKeyboardButton("🎮 PRESIONA /start PARA COMENZAR", callback_data="invitacion_iniciar")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return texto, reply_markup

# ============================================
# MENSAJE DESPUÉS DE /start (PARA PEDIR CÓDIGO)
# ============================================
def mensaje_start_con_boton():
    """
    Mensaje que ve el jugador después de presionar /start.
    Le pide que obtenga su código personal.
    """
    texto = (
        f"✅ **¡PERFECTO!**\n\n"
        f"Ya has dado el primer paso.\n\n"
        f"📌 **PASO 2:**\n"
        f"Ahora presiona el botón **'Obtener mi código'** para que Orlando genere tu código personal de invitación.\n\n"
        f"👇👇👇"
    )
    
    keyboard = [[InlineKeyboardButton("🎟️ OBTENER MI CÓDIGO", callback_data="invitacion_micodigo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return texto, reply_markup

# ============================================
# COMANDO /micodigo (GENERA Y MUESTRA EL CÓDIGO)
# ============================================
async def micodigo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando que genera el código único del jugador y lo muestra
    con instrucciones claras para copiarlo e ir a la ventana de bienvenida.
    """
    # Determinar si viene de callback o comando directo
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user = query.from_user
        mensaje_func = query.message.reply_text
        print(f"🎟️ micodigo llamado vía callback por {user.id}")
    else:
        user = update.effective_user
        mensaje_func = update.message.reply_text
        print(f"🎟️ micodigo llamado vía comando por {user.id}")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Buscar al jugador en la base de datos
    cursor.execute('''
        SELECT j.id, j.codigo_invitado, a.codigo_admin 
        FROM jugadores j
        LEFT JOIN administradores a ON j.admin_id = a.id
        WHERE j.telegram_id = ?
    ''', (user.id,))
    
    jugador = cursor.fetchone()
    
    if not jugador:
        conn.close()
        # Verificar si es admin
        cursor.execute("SELECT codigo_admin FROM administradores WHERE telegram_id = ?", (user.id,))
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            await mensaje_func(
                "👑 **Eres administrador**\n\n"
                "Los administradores no necesitan código de invitación.\n"
                "Comparte tu enlace con otros jugadores usando /mi_enlace"
            )
        else:
            await mensaje_func(
                "❌ **No tienes una cuenta registrada.**\n\n"
                "Para obtener un código necesitas llegar mediante un enlace de invitación.\n"
                "Contacta a un administrador para que te envíe un enlace."
            )
        return
    
    jugador_id, codigo_actual, admin_codigo = jugador
    
    # Si ya tiene un código, lo reutilizamos
    if codigo_actual:
        codigo = codigo_actual
        print(f"🎟️ Código reutilizado para {user.id}: {codigo}")
    else:
        # Generar nuevo código
        codigo = generar_codigo_unico(admin_codigo)
        
        # Guardar en base de datos
        cursor.execute(
            "UPDATE jugadores SET codigo_invitado = ? WHERE id = ?",
            (codigo, jugador_id)
        )
        conn.commit()
        print(f"🎟️ Nuevo código generado para {user.id}: {codigo}")
    
    conn.close()
    
    # Mensaje con el código y botón a ventana de bienvenida
    texto = (
        f"✅ **¡CÓDIGO GENERADO!**\n\n"
        f"🎟️ **Tu código de invitación es:**\n\n"
        f"```\n{codigo}\n```\n\n"
        f"📌 **PASO 3:**\n"
        f"**Copia este código** (tal como está, con mayúsculas y guiones).\n\n"
        f"📌 **PASO 4:**\n"
        f"Presiona el botón **'Ir a ventana de bienvenida'** y pega el código allí.\n\n"
        f"👇👇👇"
    )
    
    keyboard = [[InlineKeyboardButton("🚪 IR A VENTANA DE BIENVENIDA", url=URL_BIENVENIDA)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await mensaje_func(
        texto,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ============================================
# MANEJADOR DE CALLBACKS (PARA BOTONES)
# ============================================
async def invitaciones_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja todos los callbacks de los botones de invitaciones.
    """
    query = update.callback_query
    await query.answer()
    
    if query.data == "invitacion_iniciar":
        print(f"🔄 Botón 'iniciar' presionado por {query.from_user.id}")
        if _start_function:
            # Crear un mensaje falso para que start funcione
            # Esto es un workaround, lo ideal es que start acepte callbacks
            await _start_function(update, context)
        else:
            await query.message.reply_text("❌ Error interno: función start no disponible")
    
    elif query.data == "invitacion_micodigo":
        print(f"🔄 Botón 'micodigo' presionado por {query.from_user.id}")
        await micodigo(update, context)

# ============================================
# FUNCIÓN DE CONFIGURACIÓN PARA main()
# ============================================
def setup_invitaciones(app):
    """
    Añade los handlers de invitaciones a la aplicación principal.
    Debe llamarse desde main() en bot_orlando.py
    """
    # Añadir comando /micodigo
    app.add_handler(CommandHandler("micodigo", micodigo))
    
    # Añadir manejador de callbacks
    app.add_handler(CallbackQueryHandler(invitaciones_callback_handler, pattern="^(invitacion_iniciar|invitacion_micodigo)$"))
    
    print("✅ Sistema de invitaciones configurado correctamente")