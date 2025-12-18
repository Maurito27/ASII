"""
Cerebro V7.0 - Máquina de Estados Enterprise
--------------------------------------------
Orquesta la interacción con el usuario mediante estados definidos:
1. PERFILADO: Identifica el rol del usuario.
2. DIAGNÓSTICO: Analiza la consulta sin buscar respuesta final.
3. SELECCIÓN: Consulta al Bibliotecario (RAG Fase 1).
4. LECTURA: Consulta al Lector (RAG Fase 2).
"""
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import SQLChatMessageHistory

# Importaciones V7
from app.core.config import Configuracion
from app.core.contracts import SCORE_THRESHOLD
from app.logic.rag_engine_v7 import buscar_manual_candidato, buscar_contenido_profundo
from app.logic.session_manager import gestor_sesiones

# Configuración del LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp", 
    temperature=0.0,
    google_api_key=Configuracion.GOOGLE_API_KEY
)

# --- PROMPTS DINÁMICOS POR PERFIL ---
SYSTEM_PROMPTS = {
    "SISTEMAS": """
    Eres un Arquitecto de Software Senior experto en Softland ERP.
    Tu usuario es técnico (Sistemas/IT).
    - Ve al grano. No uses saludos largos.
    - Si hay tablas o nombres de campos técnicos, úsalos tal cual (SQL).
    - Asume que el usuario sabe navegar en Windows.
    - Prioriza la precisión técnica sobre la pedagogía.
    """,
    "ADMIN": """
    Eres un Consultor Funcional Senior de Softland ERP.
    Tu usuario es administrativo (Ventas/RRHH/Contabilidad).
    - Explica paso a paso con paciencia.
    - Usa analogías si es necesario.
    - Avisa siempre si una acción es irreversible.
    - Tono: Profesional, empático y claro.
    """
}

def obtener_historial(session_id: str):
    try:
        history = SQLChatMessageHistory(
            session_id=session_id, 
            connection_string=Configuracion.RUTA_HISTORIAL_CHAT
        )
        return history, "\n".join([f"{m.type.upper()}: {m.content}" for m in history.messages[-4:]])
    except: 
        return None, ""

# --- FASE 1: DIAGNÓSTICO & SELECCIÓN ---

async def fase_bibliotecario(pregunta, session_id, perfil):
    """
    Consulta la biblioteca para identificar el manual correcto.
    """
    print(f">> [Brain V7] Fase Bibliotecario: Buscando manual para '{pregunta}'")
    
    candidatos = buscar_manual_candidato(pregunta)
    
    if not candidatos:
        return (
            "❌ No encontré ningún manual vigente que coincida con tu consulta.\n"
            "Por favor, intenta con el nombre del módulo (ej: 'Ventas', 'Sueldos').",
            "ESPERANDO_INPUT", 
            None
        )

    mejor_candidato = candidatos[0]
    score = mejor_candidato["score"]
    
    # Reglas de Oro
    if score < SCORE_THRESHOLD["AUTO_SELECT"]:
        print(f"   ✅ Auto-selección: {mejor_candidato['nombre_archivo']} (Score: {score:.3f})")
        return (None, "LECTURA_PROFUNDA", mejor_candidato)
        
    elif score < SCORE_THRESHOLD["CONFIRM"]:
        msg = (
            f"🔎 Encontré este manual relacionado: **{mejor_candidato['nombre_archivo']}**\n"
            f"_(Versión {mejor_candidato['version']} - Año {mejor_candidato['anio']})_\n\n"
            "¿Es este el manual correcto?"
        )
        gestor_sesiones.actualizar_metadata(session_id, {"candidato_pendiente": mejor_candidato})
        return (msg, "ESPERANDO_CONFIRMACION", None)
        
    else:
        opciones = "\n".join([f"- {c['nombre_archivo']}" for c in candidatos[:3]])
        msg = (
            "🤔 Encontré opciones lejanas:\n"
            f"{opciones}\n\n"
            "Por favor, sé más específico."
        )
        return (msg, "ESPERANDO_INPUT", None)

# --- FASE 2: LECTURA & RESPUESTA ---

async def fase_lector(pregunta, manual_meta, perfil, historial_txt):
    """
    Lee el contenido dentro del manual seleccionado y genera la respuesta.
    """
    nombre_doc = manual_meta.get("nombre_archivo", "Desconocido")
    doc_id = manual_meta.get("doc_id")
    version_doc = manual_meta.get("version", "N/A")
    
    if not doc_id:
        print(f"❌ ERROR CRÍTICO: Metadata corrupta, falta doc_id: {manual_meta}")
        return ("⚠️ Error interno: El índice del manual está dañado. Recomienda al admin ejecutar `ingest_v7.py`.", [])

    print(f">> [Brain V7] Fase Lector: Leyendo ID {doc_id[:8]}... ({nombre_doc})")
    
    # 1. Búsqueda Profunda
    evidencias = buscar_contenido_profundo(pregunta, doc_id)
    
    if not evidencias:
        return (
            f"📂 Abrí el manual **{nombre_doc}**, pero no encontré referencias exactas a '{pregunta}'.\n"
            "Intenta reformular la pregunta con términos más específicos.",
            []
        )

    # 2. Construcción del Contexto
    contexto_str = ""
    for i, ev in enumerate(evidencias):
        contexto_str += f"--- FRAGMENTO {i+1} (Pág {ev['pagina']} - {ev['seccion']}) ---\n{ev['texto']}\n\n"

    # 3. System Prompt según perfil
    system_prompt = SYSTEM_PROMPTS.get(perfil, SYSTEM_PROMPTS["ADMIN"])
    
    # 4. Prompt de Usuario con Instrucciones de Formato
    prompt_usuario = f"""
CONTEXTO (Manual: {nombre_doc}, v{version_doc}):
{contexto_str}

HISTORIAL:
{historial_txt}

PREGUNTA:
"{pregunta}"

INSTRUCCIONES DE FORMATO PARA TELEGRAM:
1. **Contenido:** Responde SOLO con info del contexto. Si falta algo, di "No está documentado en este manual".

2. **Jerarquía Visual:**
   - Usa emojis para títulos principales (📌 ⚙️ 📋 ⚠️)
   - Usa negrita limpia para subtítulos: **Título**
   
3. **Códigos Técnicos:**
   - TODO nombre de tabla, campo, objeto debe ir en monoespaciado: `GRTQVH`, `FCRMVH`
   - Ejemplos SQL en bloques de código

4. **Listas:**
   - Usa viñetas Unicode: • (bullet)
   - NO uses asteriscos (*)
   - Formato: • **Concepto:** Explicación

5. **Citas de Fuente:**
   - NO repitas (pág. X) en cada oración
   - Agrúpalas al final de cada sección importante: _(Ref: Págs 3, 5, 7)_

6. **Espaciado:**
   - Separa secciones con línea en blanco
   
7. **Rutas de navegación:**
   - Formato: _Menú_ → _Submenu_ → _Opción_

IMPORTANTE: El formato debe ser limpio y escaneable visualmente.
"""
    
    # 5. Invocación del LLM
    mensajes = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt_usuario)
    ]
    
    respuesta_llm = await llm.ainvoke(mensajes)
    
    # 6. Footer con trazabilidad
    footer = f"\n\n_Fuente: {nombre_doc} (v{version_doc})_"
    
    return (respuesta_llm.content + footer, [manual_meta])

# --- CONTROLADOR PRINCIPAL (MÁQUINA DE ESTADOS) ---

async def generar_respuesta_inteligente(pregunta: str, session_id: str = "default") -> dict:
    """
    Orquestador principal del cerebro conversacional.
    """
    # 1. Recuperar Sesión
    sesion = gestor_sesiones.obtener_sesion(session_id)
    estado_actual = sesion.get("estado", "INICIO")
    perfil = sesion.get("perfil", "ADMIN")
    
    # Comandos rápidos
    if pregunta.startswith("/perfil"):
        nuevo = "SISTEMAS" if "sistemas" in pregunta.lower() else "ADMIN"
        gestor_sesiones.actualizar_sesion(session_id, perfil=nuevo)
        return {"texto": f"✅ Perfil actualizado a: **{nuevo}**", "archivos": []}
        
    if pregunta.lower() in ["salir", "cancelar", "reset", "/limpiar", "/start"]:
        gestor_sesiones.limpiar_sesion(session_id)
        return {"texto": "🧹 Memoria limpiada. ¿En qué puedo ayudarte?", "archivos": []}

    # --- MÁQUINA DE ESTADOS ---
    
    # CASO A: Esperando confirmación de manual
    if estado_actual == "ESPERANDO_CONFIRMACION":
        if any(x in pregunta.lower() for x in ["si", "sí", "claro", "es ese", "correcto", "ok"]):
            candidato = sesion["metadata"]["candidato_pendiente"]
            gestor_sesiones.cambiar_estado(
                session_id, 
                "LECTURA_PROFUNDA", 
                doc=candidato["nombre_archivo"], 
                meta=candidato
            )
            return {
                "texto": f"👍 Perfecto. Abriendo **{candidato['nombre_archivo']}**. ¿Qué necesitas saber?", 
                "archivos": []
            }
        else:
            # Usuario rechazó
            gestor_sesiones.limpiar_sesion(session_id)
            return {
                "texto": "Entendido, descartamos ese manual. ¿Qué tema específico buscamos?", 
                "archivos": []
            }

    # CASO B: Ya estamos dentro de un manual (Modo Profundo)
    if estado_actual == "LECTURA_PROFUNDA":
        hist_obj, hist_txt = obtener_historial(session_id)
        manual = sesion["metadata"]
        
        resp_txt, archs = await fase_lector(pregunta, manual, perfil, hist_txt)
        
        if hist_obj:
            hist_obj.add_user_message(pregunta)
            hist_obj.add_ai_message(resp_txt)
            
        return {"texto": resp_txt, "archivos": [manual.get("nombre_archivo")]}

    # CASO C: Búsqueda Nueva (Modo Bibliotecario)
    msg_biblio, nuevo_estado, meta_manual = await fase_bibliotecario(pregunta, session_id, perfil)
    
    if nuevo_estado == "LECTURA_PROFUNDA":
        # Auto-selección exitosa -> Leemos inmediatamente
        gestor_sesiones.cambiar_estado(
            session_id, 
            "LECTURA_PROFUNDA", 
            doc=meta_manual["nombre_archivo"], 
            meta=meta_manual
        )
        
        hist_obj, hist_txt = obtener_historial(session_id)
        resp_txt, archs = await fase_lector(pregunta, meta_manual, perfil, hist_txt)
        
        if hist_obj:
            hist_obj.add_user_message(pregunta)
            hist_obj.add_ai_message(resp_txt)
            
        return {"texto": resp_txt, "archivos": [meta_manual.get("nombre_archivo")]}
        
    elif nuevo_estado == "ESPERANDO_CONFIRMACION":
        gestor_sesiones.cambiar_estado(session_id, "ESPERANDO_CONFIRMACION")
        return {"texto": msg_biblio, "archivos": []}
        
    else:
        # Fallo o ambigüedad
        return {"texto": msg_biblio, "archivos": []}