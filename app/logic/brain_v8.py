"""
Cerebro V8.1 - Arquitectura Multimodal & Visión (Refactored)
------------------------------------------------------------
Mejoras:
1. Prompt Vision Few-Shot: Experto en errores Softland.
2. Manejo de Errores: Validación de tamaño y excepciones en visión.
3. Facade Pattern: Expone funciones para que el Bot no toque el RAG.
4. Calibración: Usa umbrales de logits correctos.
"""
import os
import base64
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import SQLChatMessageHistory

# --- IMPORTACIONES ---
from app.core.config import Configuracion
from app.core.contracts import SCORE_THRESHOLD
from app.logic.rag_engine_v8 import buscar_manual_candidato, buscar_contenido_profundo
from app.logic.session_manager import gestor_sesiones

# Configuración del LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp", 
    temperature=0.0, 
    google_api_key=Configuracion.GOOGLE_API_KEY
)

# --- PROMPTS ---
SYSTEM_PROMPTS = {
    "SISTEMAS": """
    Eres un Arquitecto de Software Senior experto en Softland ERP.
    Responde con precisión técnica, usando bloques de código para tablas/SQL.
    Formato: Markdown limpio, títulos con emojis, sin rodeos.
    """,
    "ADMIN": """
    Eres un Consultor Funcional Senior de Softland ERP.
    Explica paso a paso, usa negritas para menús y botones.
    Formato: Didáctico, listas numeradas, cita la fuente al final.
    """
}

def obtener_historial(session_id: str):
    try:
        history = SQLChatMessageHistory(session_id=session_id, connection_string=Configuracion.RUTA_HISTORIAL_CHAT)
        return history, "\n".join([f"{m.type.upper()}: {m.content}" for m in history.messages[-4:]])
    except: return None, ""

def codificar_imagen(ruta_imagen):
    """Lee y codifica en Base64 con validación básica."""
    # Validación de tamaño (aprox 4MB)
    if os.path.getsize(ruta_imagen) > 4 * 1024 * 1024:
        raise ValueError("Imagen demasiado grande (Máx 4MB)")
        
    with open(ruta_imagen, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# --- MÓDULO DE VISIÓN (Few-Shot) ---

async def analizar_imagen_tecnica(ruta_imagen):
    """
    Usa Gemini Vision con Few-Shot Prompting para extraer datos técnicos estructurados.
    """
    try:
        img_b64 = codificar_imagen(ruta_imagen)
    except Exception as e:
        print(f"❌ Error codificando imagen: {e}")
        return f"[Error al procesar imagen: {str(e)}]"

    prompt_vision = """
    Eres un experto en Soporte Técnico de Softland ERP (Logic/Business).
    Tu tarea es analizar esta captura de pantalla y extraer metadatos para búsqueda.

    EJEMPLOS DE ANÁLISIS IDEAL:
    - Si ves "ORA-00942: table or view does not exist" -> "Error Base de Datos: ORA-00942 Tabla inexistente".
    - Si ves una ventana con título "Ingreso de Comprobantes" -> "Módulo: Compras/Ventas, Ventana: Ingreso de Comprobantes".
    - Si ves un diagrama de flujo -> "Diagrama de proceso: Flujo de aprobación".

    AHORA ANALIZA LA IMAGEN Y EXTRAE:
    1. Código de error exacto (si existe).
    2. Nombre del Módulo y Ventana visible.
    3. Mensaje de error textual completo.
    """
    
    mensaje = HumanMessage(
        content=[
            {"type": "text", "text": prompt_vision},
            {"type": "image_url", "image_url": f"data:image/jpeg;base64,{img_b64}"}
        ]
    )
    
    try:
        resp = await llm.ainvoke([mensaje])
        print(f">> [Brain V8] Visión extrajo: {resp.content[:100]}...")
        return resp.content
    except Exception as e:
        print(f"❌ Error en llamada a LLM Vision: {e}")
        return "Error analizando la imagen."

# --- FACADE (Wrapper para el Bot) ---

def buscar_manual_experto(termino: str, k: int = 1):
    """
    Función pública para que el Bot busque manuales sin importar 'rag_engine'.
    """
    return buscar_manual_candidato(termino, k)

# --- FASES ---

async def fase_bibliotecario(pregunta, session_id, perfil):
    print(f">> [Brain V8] Buscando manual para: '{pregunta}'")
    
    candidatos = buscar_manual_candidato(pregunta)
    
    if not candidatos:
        return ("❌ No encontré manuales vigentes. Intenta ser más específico.", "ESPERANDO_INPUT", None)

    mejor = candidatos[0]
    score = mejor.get("rerank_score", -99.0) # Default bajo si falla
    
    print(f"   📊 Top Candidate: {mejor['nombre_archivo']} (Score: {score:.2f})")
    # Logging para calibración futura
    try:
        from datetime import datetime
        log_dir = os.path.join(Configuracion.DIRECTORIO_BASE, "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, "rag_scores.log")
        with open(log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp}|{pregunta[:50]}|{mejor['nombre_archivo']}|{score:.4f}\n")
    except Exception as e:
        # Si falla el logging, no bloqueamos el flujo
        pass
    # Lógica de Umbrales Correcta (Logits MS-MARCO)
    if score > SCORE_THRESHOLD["HIGH_CONFIDENCE"]: 
        return (None, "LECTURA_PROFUNDA", mejor)
        
    elif score > SCORE_THRESHOLD["MEDIUM_CONFIDENCE"]:
        msg = f"🔎 ¿Te refieres al manual **{mejor['nombre_archivo']}**?"
        gestor_sesiones.actualizar_metadata(session_id, {"candidato_pendiente": mejor})
        return (msg, "ESPERANDO_CONFIRMACION", None)
        
    else:
        return ("🤔 Encontré documentos, pero la relevancia es baja. Por favor reformula tu consulta.", "ESPERANDO_INPUT", None)

async def fase_lector(pregunta, manual_meta, perfil, historial_txt, imagen_b64=None):
    doc_id = manual_meta.get("doc_id")
    evidencias = buscar_contenido_profundo(pregunta, doc_id)
    
    if not evidencias:
        return (f"📂 Leí el manual, pero no encontré referencias específicas.", [])

    contexto_str = ""
    for i, ev in enumerate(evidencias):
        contexto_str += f"--- FRAGMENTO {i+1} ---\n{ev['texto']}\n\n"

    system_prompt = SYSTEM_PROMPTS.get(perfil, SYSTEM_PROMPTS["ADMIN"])
    
    bloque_contenido = [
        {"type": "text", "text": f"CONTEXTO TÉCNICO:\n{contexto_str}\n\nHISTORIAL:\n{historial_txt}\n\nPREGUNTA:\n{pregunta}"}
    ]
    
    if imagen_b64:
        bloque_contenido.append({"type": "text", "text": "REFERENCIA VISUAL:"})
        bloque_contenido.append({"type": "image_url", "image_url": f"data:image/jpeg;base64,{imagen_b64}"})

    bloque_contenido.append({"type": "text", "text": "Responde usando SOLO el contexto. Formato visual rico."})

    mensajes = [SystemMessage(content=system_prompt), HumanMessage(content=bloque_contenido)]
    respuesta = await llm.ainvoke(mensajes)
    
    return (respuesta.content + f"\n\n_Fuente: {manual_meta['nombre_archivo']}_", [manual_meta])

# --- ORQUESTADOR ---

async def generar_respuesta_inteligente(pregunta: str, ruta_imagen: str = None, session_id: str = "default") -> dict:
    
    sesion = gestor_sesiones.obtener_sesion(session_id)
    estado = sesion.get("estado", "INICIO")
    perfil = sesion.get("perfil", "ADMIN")
    
    # Lógica Multimodal
    busqueda_aumentada = pregunta
    img_b64 = None
    
    if ruta_imagen:
        print(">> [Brain V8] Procesando entrada visual...")
        descripcion_visual = await analizar_imagen_tecnica(ruta_imagen)
        busqueda_aumentada = f"{pregunta}\n[Contexto Visual: {descripcion_visual}]"
        try:
            img_b64 = codificar_imagen(ruta_imagen)
        except: 
            pass # Ya se logueó el error en analizar_imagen_tecnica

    # Comandos
    if pregunta.startswith("/perfil"):
        nuevo = "SISTEMAS" if "sistemas" in pregunta.lower() else "ADMIN"
        gestor_sesiones.actualizar_sesion(session_id, perfil=nuevo)
        return {"texto": f"✅ Perfil: **{nuevo}**", "archivos": []}
    
    if pregunta.lower() in ["salir", "cancelar", "/limpiar"]:
        gestor_sesiones.limpiar_sesion(session_id)
        return {"texto": "🧹 Memoria reiniciada.", "archivos": []}

    # Máquina de Estados
    if estado == "ESPERANDO_CONFIRMACION":
        if any(x in pregunta.lower() for x in ["si", "sí", "claro"]):
            cand = sesion["metadata"]["candidato_pendiente"]
            gestor_sesiones.cambiar_estado(session_id, "LECTURA_PROFUNDA", doc=cand["nombre_archivo"], meta=cand)
            return {"texto": f"👍 Abriendo **{cand['nombre_archivo']}**.", "archivos": []}
        else:
            gestor_sesiones.limpiar_sesion(session_id)
            return await generar_respuesta_inteligente(pregunta, ruta_imagen, session_id) # Reintentar como búsqueda nueva

    if estado == "LECTURA_PROFUNDA":
        hist_obj, hist_txt = obtener_historial(session_id)
        resp_txt, archs = await fase_lector(busqueda_aumentada, sesion["metadata"], perfil, hist_txt, img_b64)
        if hist_obj: 
            hist_obj.add_user_message(pregunta)
            hist_obj.add_ai_message(resp_txt)
        return {"texto": resp_txt, "archivos": []}

    # Inicio
    msg, nuevo_estado, meta = await fase_bibliotecario(busqueda_aumentada, session_id, perfil)
    
    if nuevo_estado == "LECTURA_PROFUNDA":
        gestor_sesiones.cambiar_estado(session_id, "LECTURA_PROFUNDA", doc=meta["nombre_archivo"], meta=meta)
        hist_obj, hist_txt = obtener_historial(session_id)
        resp_txt, archs = await fase_lector(busqueda_aumentada, meta, perfil, hist_txt, img_b64)
        if hist_obj: 
            hist_obj.add_user_message(pregunta)
            hist_obj.add_ai_message(resp_txt)
        return {"texto": resp_txt, "archivos": []}
        
    elif nuevo_estado == "ESPERANDO_CONFIRMACION":
        gestor_sesiones.cambiar_estado(session_id, "ESPERANDO_CONFIRMACION")
        return {"texto": msg, "archivos": []}
    
    return {"texto": msg, "archivos": []}
