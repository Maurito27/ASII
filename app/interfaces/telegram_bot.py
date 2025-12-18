"""
Interfaz Telegram V18 (telegram_bot.py) - Comandos Tácticos V6 Enterprise
-------------------------------------------------------------------------
Adaptado para Arquitectura V6:
- Usa 'rag_engine_v6' para búsquedas directas (/manual).
- Usa 'brain_v6' para el flujo conversacional inteligente.
- Elimina dependencias obsoletas (detectar_archivo_francotirador).
"""
import os
import csv
import shutil
import uuid
import subprocess
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.error import BadRequest

# --- IMPORTACIONES V6 ---
from app.core.config import Configuracion
from app.logic.brain_v7  import generar_respuesta_inteligente
from app.logic.session_manager import gestor_sesiones
# Usamos el motor V6 para el comando /manual
from app.logic.rag_engine_v7 import buscar_manual_candidato 

# Variables Globales
FECHA_INICIO = datetime.now()
TEMP_DIR = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "temp_images")
CACHE_DIR = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "cache_docs")
LOG_FILE = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "usage_log.csv")

if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

DOWNLOAD_CACHE = {}

# --- SEGURIDAD ---
async def enviar_mensaje_seguro(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str, reply_markup=None):
    """
    Función maestra para evitar el error 'Message is too long'.
    Si el texto supera 4000 caracteres, lo divide en tramas.
    """
    LIMITE = 4000 
    chat_id = update.effective_chat.id

    if len(texto) <= LIMITE:
        try:
            await context.bot.send_message(chat_id=chat_id, text=texto, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except BadRequest:
            # Fallback a texto plano si el Markdown falla
            await context.bot.send_message(chat_id=chat_id, text=texto, reply_markup=reply_markup)
        return

    partes = []
    while texto:
        if len(texto) <= LIMITE:
            partes.append(texto)
            break
        corte = texto.rfind('\n', 0, LIMITE)
        if corte == -1: corte = LIMITE
        partes.append(texto[:corte])
        texto = texto[corte:]

    for i, parte in enumerate(partes):
        es_ultimo = (i == len(partes) - 1)
        markup = reply_markup if es_ultimo else None
        header = "" if i == 0 else f"*(...Parte {i+1})*\n"
        try:
            await context.bot.send_message(chat_id=chat_id, text=header + parte, parse_mode=ParseMode.MARKDOWN, reply_markup=markup)
        except BadRequest:
            await context.bot.send_message(chat_id=chat_id, text=header + parte, reply_markup=markup)

async def verificar_acceso(update: Update) -> bool:
    user = update.effective_user
    if Configuracion.es_usuario_permitido(user.id): return True
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text("⛔ *Acceso Denegado.* Contacte al administrador.", parse_mode=ParseMode.MARKDOWN)
    return False

def obtener_uptime():
    delta = datetime.now() - FECHA_INICIO
    return str(delta).split('.')[0]

# --- COMANDOS DE USUARIO ---

async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    msg = (
        "👋 *ASII V6 Enterprise (Online)*\n\n"
        "Comandos útiles:\n"
        "🧹 `/limpiar` - Reiniciar conversación\n"
        "🔍 `/manual [tema]` - Buscar documento específico\n"
        "👤 `/perfil [admin|sistemas]` - Cambiar modo de respuesta\n"
        "🛠 `/ayuda` - Ver todo"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def comando_limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    chat_id = str(update.effective_chat.id)
    gestor_sesiones.limpiar_sesion(chat_id)
    await update.message.reply_text("🧹 *Memoria reiniciada.*\nHe olvidado el contexto actual. ¿En qué te ayudo ahora?", parse_mode=ParseMode.MARKDOWN)

async def comando_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Búsqueda directa usando el Bibliotecario V6 (Solo fichas vigentes).
    """
    if not await verificar_acceso(update): return
    
    if not context.args:
        await update.message.reply_text("⚠️ **Sintaxis:** `/manual [nombre o tema]`", parse_mode=ParseMode.MARKDOWN)
        return

    termino = " ".join(context.args)
    await update.message.reply_text(f"🔍 Buscando manuales vigentes sobre: *{termino}*...", parse_mode=ParseMode.MARKDOWN)
    
    # --- LOGICA V6: Usamos buscar_manual_candidato ---
    candidatos = buscar_manual_candidato(termino, k=1)
    
    if candidatos:
        meta = candidatos[0] # El mejor match
        chat_id = str(update.effective_chat.id)
        
        # Preparamos la sesión para confirmar este manual
        gestor_sesiones.actualizar_metadata(chat_id, {"candidato_pendiente": meta})
        gestor_sesiones.cambiar_estado(chat_id, "ESPERANDO_CONFIRMACION") # Forzamos estado de confirmación
        
        msg = (
            f"📂 **DOCUMENTO LOCALIZADO (V6)**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📄 *Archivo:* `{meta['nombre_archivo']}`\n"
            f"📅 *Versión:* v{meta['version']} ({meta['anio']})\n"
            f"🎯 *Relevancia:* {meta['confianza']}\n\n"
            f"❓ *¿Deseas activar este manual para consultas?*"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Activar Manual", callback_data="confirmar_experto")],
            [InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_experto")]
        ]
        await enviar_mensaje_seguro(update, context, msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(f"❌ No encontré manuales vigentes para: *{termino}*", parse_mode=ParseMode.MARKDOWN)

# --- COMANDOS DE ADMIN ---

async def comando_costos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    
    if not os.path.exists(LOG_FILE):
        await update.message.reply_text("📉 No hay registros de consumo aún.")
        return

    gasto_dia = 0.0
    tokens_in = 0
    tokens_out = 0
    hoy = datetime.now().strftime("%Y-%m-%d")

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Fecha"] == hoy:
                    gasto_dia += float(row["CostoUSD"])
                    tokens_in += int(row["Input"])
                    tokens_out += int(row["Output"])
        
        msg = (
            f"💰 **REPORTE DE HOY ({hoy})**\n"
            f"💵 Gasto: `${gasto_dia:.6f} USD`\n"
            f"📥 Input: `{tokens_in}`\n"
            f"📤 Output: `{tokens_out}`"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error leyendo logs: {e}")

async def comando_flush(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    await update.message.reply_text("⚠️ En V6 la ingesta es estática. Para recargar documentos, ejecuta `python ingest_v6.py` en el servidor.")

# --- COMANDOS GENERALES ---

async def comando_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    text = (
        "🛠 *COMANDOS DISPONIBLES*\n\n"
        "👤 **Usuario:**\n"
        "`/limpiar` - Resetear memoria\n"
        "`/manual [tema]` - Búsqueda rápida de manuales\n"
        "`/inventario` - Ver documentos indexados\n\n"
        "👮‍♂️ **Admin:**\n"
        "`/costos` - Ver consumo API\n"
        "`/status` - Estado del cerebro"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def comando_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    sesion = gestor_sesiones.obtener_sesion(str(update.effective_chat.id))
    doc_activo = sesion.get('doc_activo', 'Ninguno')
    
    msg = (
        f"📊 **ESTADO DEL SISTEMA**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ *Uptime:* {obtener_uptime()}\n"
        f"🧠 *Estado:* `{sesion['estado']}`\n"
        f"👤 *Perfil:* `{sesion.get('perfil', 'ADMIN')}`\n"
        f"📑 *Manual Activo:* `{doc_activo}`\n"
        f"🔄 *Intentos Fallidos:* {sesion.get('intentos_fallidos', 0)}"
    )
    await enviar_mensaje_seguro(update, context, msg)

async def comando_inventario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    # En V6, esto idealmente consultaría a Chroma, pero por simplicidad escaneamos carpetas raw
    await update.message.reply_text("📂 *Escaneando directorio local...*", parse_mode=ParseMode.MARKDOWN)
    
    total = 0
    resumen = {}
    for r, _, f in os.walk(Configuracion.RUTA_DOCS):
        cat = os.path.relpath(r, Configuracion.RUTA_DOCS)
        if cat == ".": cat = "Raíz"
        pdfs = [x for x in f if x.lower().endswith('.pdf')]
        if pdfs:
            resumen[cat] = len(pdfs)
            total += len(pdfs)
            
    msg = f"📚 *Total PDFs Raw: {total}*\n" + "\n".join([f"• {k}: {v}" for k,v in resumen.items()])
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

async def comando_recargar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    await update.message.reply_text("🔄 Ejecutando Ingesta V6...", parse_mode=ParseMode.MARKDOWN)
    try:
        script = os.path.join(Configuracion.DIRECTORIO_BASE, "ingest_v6.py")
        # Ejecutamos el script de ingesta en un subproceso
        subprocess.run(["python", script], check=True)
        await update.message.reply_text("✅ *Ingesta Completada.* Base de datos actualizada.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error en ingesta: {e}")

# --- MANEJO DE INTERACCIONES (CALLBACKS) ---
async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(update.effective_chat.id)

    if data == "confirmar_experto":
        sesion = gestor_sesiones.obtener_sesion(chat_id)
        # Recuperamos el candidato pendiente
        candidato = sesion["metadata"].get("candidato_pendiente")
        
        if candidato:
            gestor_sesiones.cambiar_estado(chat_id, "LECTURA_PROFUNDA", doc=candidato["nombre_archivo"], meta=candidato)
            await query.edit_message_text(f"✅ **Manual Activado.**\nLeyendo: `{candidato['nombre_archivo']}`\n\n¿Qué necesitas saber sobre este tema?", parse_mode=ParseMode.MARKDOWN)
        else:
            await query.edit_message_text("⚠️ Error: No encontré el candidato en memoria.")
        return

    if data == "cancelar_experto":
        gestor_sesiones.limpiar_sesion(chat_id)
        await query.edit_message_text("❌ Selección cancelada. Volviendo a modo exploración.")
        return

    # Manejo de descargas (si existen en cache)
    if data in DOWNLOAD_CACHE:
        ruta = DOWNLOAD_CACHE[data]
        if os.path.exists(ruta):
            await context.bot.send_document(chat_id=chat_id, document=open(ruta, 'rb'), caption=f"📂 {os.path.basename(ruta)}")

# --- CEREBRO PRINCIPAL ---
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    
    # Filtro para grupos
    if update.effective_chat.type != ChatType.PRIVATE:
        bot_user = context.bot.username
        txt = update.message.caption or update.message.text or ""
        is_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
        if not (f"@{bot_user}" in txt or is_reply):
            return

    raw = update.message.caption or update.message.text or ""
    clean_text = raw.replace(f"@{context.bot.username}", "").strip()
    
    if not clean_text and not update.message.photo: return
    if not clean_text: clean_text = "Analiza esta imagen."

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    ruta_foto = None
    if update.message.photo:
        f = await update.message.photo[-1].get_file()
        ruta_foto = os.path.join(TEMP_DIR, f"{update.effective_user.id}.jpg")
        await f.download_to_drive(ruta_foto)

    # Llamada al CEREBRO V6
    # Nota: El cerebro V6 maneja su propia lógica de estados (Bibliotecario -> Lector)
    paquete = await generar_respuesta_inteligente(clean_text, session_id=str(update.effective_chat.id))
    
    if ruta_foto and os.path.exists(ruta_foto): os.remove(ruta_foto)

    # Construcción de Botones
    keyboard = []
    
    # Si el cerebro devuelve un modo de confirmación explícito (ej: encontró manual automáticamente)
    # Nota: En V6, el cerebro suele manejar el texto directamente, pero si queremos botones extras:
    if "archivos" in paquete and paquete["archivos"]:
        for nombre_doc in paquete["archivos"]:
             # Aquí podríamos implementar lógica para descargar el PDF si quisiéramos
             pass

    # ENVÍO DE RESPUESTA
    await enviar_mensaje_seguro(update, context, paquete["texto"], reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)


def iniciar_bot():
    if not Configuracion.TELEGRAM_TOKEN: return
    print(">> [Telegram] Iniciando polling...")
    app = ApplicationBuilder().token(Configuracion.TELEGRAM_TOKEN).read_timeout(30).write_timeout(30).build()
    
    # User Commands
    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("ayuda", comando_ayuda))
    app.add_handler(CommandHandler("limpiar", comando_limpiar))
    app.add_handler(CommandHandler("manual", comando_manual))
    
    # System Commands
    app.add_handler(CommandHandler("status", comando_status))
    app.add_handler(CommandHandler("inventario", comando_inventario))
    app.add_handler(CommandHandler("recargar", comando_recargar))
    
    # Admin Commands
    app.add_handler(CommandHandler("costos", comando_costos))
    app.add_handler(CommandHandler("flush", comando_flush))
    
    app.add_handler(CallbackQueryHandler(manejar_callback))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, manejar_mensaje))
    
    print(">> [ASII V6] Online y listo.")
    app.run_polling(poll_interval=2.0, drop_pending_updates=True)