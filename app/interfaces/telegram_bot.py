"""
Interfaz Telegram V8.1 (telegram_bot.py)
----------------------------------------
Actualizado: Arquitectura limpia (Facade) y manejo seguro de archivos.
"""
import os
import shutil
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatType, ParseMode
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.error import BadRequest

from app.core.config import Configuracion
from app.logic.session_manager import gestor_sesiones
# IMPORTACIÓN ÚNICA: El Bot solo habla con el Cerebro
from app.logic.brain_v8 import generar_respuesta_inteligente, buscar_manual_experto

# Variables
TEMP_DIR = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "temp_images")
if not os.path.exists(TEMP_DIR): os.makedirs(TEMP_DIR)

# --- UTILIDADES ---
async def enviar_mensaje_seguro(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str, reply_markup=None):
    chat_id = update.effective_chat.id
    try:
        await context.bot.send_message(chat_id=chat_id, text=texto, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    except BadRequest:
        # Fallback si el Markdown está roto
        await context.bot.send_message(chat_id=chat_id, text=texto, reply_markup=reply_markup)

async def verificar_acceso(update: Update) -> bool:
    user = update.effective_user
    if Configuracion.es_usuario_permitido(user.id): return True
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text("⛔ Acceso Denegado.")
    return False

# --- COMANDOS ---
async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    await update.message.reply_text("👋 *ASII V8.1 Online*\nEnvíame texto o fotos.", parse_mode=ParseMode.MARKDOWN)

async def comando_limpiar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    gestor_sesiones.limpiar_sesion(str(update.effective_chat.id))
    await update.message.reply_text("🧹 Memoria limpia.")

async def comando_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    if not context.args:
        await update.message.reply_text("⚠️ Uso: `/manual [texto]`", parse_mode=ParseMode.MARKDOWN)
        return
    
    termino = " ".join(context.args)
    # USAMOS EL WRAPPER DEL CEREBRO, NO EL RAG DIRECTAMENTE
    candidatos = buscar_manual_experto(termino, k=1)
    
    if candidatos:
        meta = candidatos[0]
        chat_id = str(update.effective_chat.id)
        gestor_sesiones.actualizar_metadata(chat_id, {"candidato_pendiente": meta})
        gestor_sesiones.cambiar_estado(chat_id, "ESPERANDO_CONFIRMACION")
        
        msg = f"📂 **Manual Encontrado**\n`{meta['nombre_archivo']}`\n\n¿Activar?"
        kb = [[InlineKeyboardButton("✅ Sí", callback_data="confirmar_experto"), InlineKeyboardButton("❌ No", callback_data="cancelar_experto")]]
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("❌ No encontrado.")

# --- MANEJO DE MENSAJES ---
async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await verificar_acceso(update): return
    
    chat_id = str(update.effective_chat.id)
    texto = update.message.caption or update.message.text or ""
    texto = texto.replace(f"@{context.bot.username}", "").strip()
    
    ruta_foto = None
    
    try:
        # 1. Descarga de Imagen
        if update.message.photo:
            if not texto: texto = "Analiza esta imagen y dime qué hacer."
            archivo_foto = await update.message.photo[-1].get_file()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta_foto = os.path.join(TEMP_DIR, f"{update.effective_user.id}_{timestamp}.jpg")
            await archivo_foto.download_to_drive(ruta_foto)
            await update.message.reply_text("👁️ *Analizando...*", parse_mode=ParseMode.MARKDOWN)

        if not texto and not ruta_foto: return

        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # 2. Procesamiento
        paquete = await generar_respuesta_inteligente(texto, ruta_imagen=ruta_foto, session_id=chat_id)
        
        await enviar_mensaje_seguro(update, context, paquete["texto"])

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error inesperado: {str(e)}")
        
    finally:
        # 3. Limpieza Segura (Siempre se ejecuta)
        if ruta_foto and os.path.exists(ruta_foto):
            try:
                os.remove(ruta_foto)
            except: pass

# --- MAIN ---
async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(update.effective_chat.id)
    
    if query.data == "confirmar_experto":
        sesion = gestor_sesiones.obtener_sesion(chat_id)
        cand = sesion["metadata"].get("candidato_pendiente")
        if cand:
            gestor_sesiones.cambiar_estado(chat_id, "LECTURA_PROFUNDA", doc=cand["nombre_archivo"], meta=cand)
            await query.edit_message_text(f"✅ Activado: {cand['nombre_archivo']}")
    elif query.data == "cancelar_experto":
        gestor_sesiones.limpiar_sesion(chat_id)
        await query.edit_message_text("❌ Cancelado.")

def iniciar_bot():
    if not Configuracion.TELEGRAM_TOKEN: return
    print(">> [ASII V8.1 Enterprise] Online.")
    app = ApplicationBuilder().token(Configuracion.TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("limpiar", comando_limpiar))
    app.add_handler(CommandHandler("manual", comando_manual))
    app.add_handler(CallbackQueryHandler(manejar_callback))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, manejar_mensaje))
    
    app.run_polling()
