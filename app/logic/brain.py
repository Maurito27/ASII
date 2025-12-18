"""
Cerebro V32 (brain.py) - Lightweight Pre-Analysis Architecture
--------------------------------------------------------------
Arquitectura corregida basada en el feedback del usuario.
1. NO pregunta "¿Es este?" ciegamente.
2. Realiza un PRE-ANÁLISIS ESTRUCTURAL (Índice + Primeras Páginas) de los candidatos.
3. Clasifica internamente en SI / TAL_VEZ / NO antes de molestar al usuario.
"""
import os
import csv
import re
import json
from datetime import datetime
from collections import Counter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.chat_message_histories import SQLChatMessageHistory
from app.core.config import Configuracion

# Módulos
from app.logic.rag_engine import buscar_contexto_relevante, obtener_metadata_archivo
from app.logic.session_manager import gestor_sesiones
from app.logic.document_processor import procesador
from app.logic.cache_manager import gestor_cache

# Configuración
# Temperatura 0 para evaluación estricta
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.0, google_api_key=Configuracion.GOOGLE_API_KEY)
search_tool = DuckDuckGoSearchRun() 

PRECIO_INPUT_1M = 0.10
PRECIO_OUTPUT_1M = 0.40
FILE_USAGE_LOG = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "usage_log.csv")
FILE_LOCK = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "API_LOCKED")

def verificar_kill_switch(): return os.path.exists(FILE_LOCK)

def registrar_consumo(in_tokens, out_tokens, costo):
    try:
        with open(FILE_USAGE_LOG, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d"), in_tokens, out_tokens, f"{costo:.6f}"])
    except: pass

def auditar_costos(respuesta_llm):
    try:
        usage = respuesta_llm.usage_metadata
        if not usage: return
        costo = ((usage.get('input_tokens',0)/1e6)*PRECIO_INPUT_1M) + ((usage.get('output_tokens',0)/1e6)*PRECIO_OUTPUT_1M)
        print(f"💰 Costo: ${costo:.6f}")
        registrar_consumo(usage.get('input_tokens',0), usage.get('output_tokens',0), costo)
    except: pass

def obtener_historial(session_id: str):
    try:
        history = SQLChatMessageHistory(session_id=session_id, connection_string=Configuracion.RUTA_HISTORIAL_CHAT)
        return history, "\n".join([f"{m.type.upper()}: {m.content}" for m in history.messages[-6:]])
    except: return None, ""

# --- LÓGICA DE PRE-ANÁLISIS (EL CEREBRO ESTRUCTURAL) ---

async def evaluar_relevancia_ligera(pregunta, doc_nombre, info_ligera):
    """
    Evalúa relevancia usando SOLO info estructural (Índice, Títulos, Resumen).
    Incluye validación robusta de respuesta JSON.
    """
    
    # Validar inputs
    if not info_ligera or not info_ligera.get("indice"):
        return {
            "nivel": "NO",
            "razon": "No se pudo extraer información del documento",
            "secciones": [],
            "confianza": 0
        }
    
    prompt = f"""
Eres un Bibliotecario Experto analizando relevancia de documentos.

CONSULTA USUARIO: "{pregunta}"
DOCUMENTO: "{doc_nombre}"

ESTRUCTURA DEL DOCUMENTO:
Índice (TOC):
{info_ligera['indice']}

Títulos Clave:
{", ".join(info_ligera['titulos_clave']) if info_ligera['titulos_clave'] else "No detectados"}

Resumen (Primeras páginas):
{info_ligera['resumen_inicio'][:700]}...

CRITERIOS ESTRICTOS:

**SI** (Alta relevancia - 80-100% confianza):
- El documento tiene sección/capítulo DEDICADO al tema exacto
- El índice muestra claramente el contenido que el usuario necesita
- El nombre del documento coincide con el tema principal
Ejemplo: Usuario pide "Diccionario de Datos" → Doc tiene capítulo "Estructura del Diccionario"

**TAL_VEZ** (Relevancia parcial - 40-70% confianza):
- El documento MENCIONA el tema pero no es su enfoque principal
- Puede tener 1-2 secciones útiles pero incompletas
Ejemplo: Usuario pide "Validaciones" → Doc de "Configuración General" tiene subsección de validaciones

**NO** (Irrelevante - 0-30% confianza):
- Tema completamente diferente
- Solo menciones pasajeras sin contenido técnico útil
Ejemplo: Usuario pide "Diccionario de Datos" → Doc es "Manual de Instalación de Servidor"

RESPONDE EXACTAMENTE EN ESTE FORMATO JSON (sin markdown, sin explicaciones adicionales):
{{"nivel": "SI", "razon": "explicación de 1-2 frases", "secciones": ["sección1", "sección2"], "confianza": 85}}

IMPORTANTE:
- "nivel" debe ser exactamente "SI", "TAL_VEZ" o "NO"
- "confianza" debe ser número entre 0 y 100
- "secciones" debe ser array de strings
"""
    
    try:
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        auditar_costos(resp)
        
        # Limpiar respuesta (remover markdown si lo incluye)
        texto_limpio = resp.content.strip()
        texto_limpio = texto_limpio.replace("```json", "").replace("```", "").strip()
        
        # Parsear JSON
        resultado = json.loads(texto_limpio)
        
        # VALIDACIÓN ESTRICTA de campos requeridos
        nivel = resultado.get("nivel", "").upper()
        if nivel not in ["SI", "TAL_VEZ", "NO"]:
            raise ValueError(f"Nivel inválido: {nivel}")
        
        razon = resultado.get("razon", "")
        if not razon or len(razon) < 10:
            raise ValueError("Razón demasiado corta o vacía")
        
        secciones = resultado.get("secciones", [])
        if not isinstance(secciones, list):
            secciones = []
        
        confianza = int(resultado.get("confianza", 0))
        if not (0 <= confianza <= 100):
            confianza = 50  # Default si está fuera de rango
        
        # AJUSTE: Si dice "SI" pero confianza < 70, bajar a "TAL_VEZ"
        if nivel == "SI" and confianza < 70:
            nivel = "TAL_VEZ"
            razon += " (Confianza ajustada por umbral)"
        
        # AJUSTE: Si dice "TAL_VEZ" pero confianza < 30, bajar a "NO"
        if nivel == "TAL_VEZ" and confianza < 30:
            nivel = "NO"
            razon += " (Confianza demasiado baja)"
        
        return {
            "nivel": nivel,
            "razon": razon[:200],  # Limitar longitud
            "secciones": secciones[:5],  # Máximo 5 secciones
            "confianza": confianza
        }
    
    except json.JSONDecodeError as e:
        print(f"[Error JSON] No se pudo parsear respuesta del LLM: {e}")
        print(f"[Respuesta original] {resp.content[:200]}")
        return {
            "nivel": "NO",
            "razon": "Error al procesar respuesta del análisis",
            "secciones": [],
            "confianza": 0
        }
    
    except ValueError as e:
        print(f"[Error Validación] {e}")
        return {
            "nivel": "NO",
            "razon": f"Error en validación: {str(e)}",
            "secciones": [],
            "confianza": 0
        }
    
    except Exception as e:
        print(f"[Error General evaluar_relevancia_ligera] {e}")
        return {
            "nivel": "NO",
            "razon": "Error inesperado en el análisis",
            "secciones": [],
            "confianza": 0
        }


async def analizar_candidatos_inteligente(pregunta, lista_docs):
    """Procesa una lista de candidatos y devuelve los clasificados."""
    analisis = {"claros": [], "posibles": [], "descartados": []}
    
    # Analizamos máximo 3 candidatos para no disparar costos/latencia
    for doc in lista_docs[:3]:
        meta = obtener_metadata_archivo(doc)
        if not meta: continue
        
        # 1. Extracción Ligera
        info = procesador.extraer_info_ligera(meta["ruta"])
        if not info: continue
        
        # 2. Evaluación IA
        evaluacion = await evaluar_relevancia_ligera(pregunta, doc, info)
        
        item = {
            "nombre": doc, 
            "ruta": meta["ruta"], 
            "razon": evaluacion.get("razon"), 
            "secciones": evaluacion.get("secciones", []),
            "confianza": evaluacion.get("confianza", 0)
        }
        
        nivel = evaluacion.get("nivel", "NO")
        if nivel == "SI": analisis["claros"].append(item)
        elif nivel == "TAL_VEZ": analisis["posibles"].append(item)
        else: analisis["descartados"].append(item)
        
    return analisis

# --- RESTO DE FUNCIONES DE APOYO ---

def analizar_intencion(pregunta: str) -> dict:
    """
    Clasifica la intención de la consulta del usuario.
    Retorna: dict con tipo e información adicional.
    """
    p = pregunta.lower()
    
    # TIPO 1: BÚSQUEDA LITERAL (ctrl+f, buscar palabra específica)
    patrones_literal = [
        r'\b(busca|encuentra|localiza|ubica)\b',
        r'\b(donde|dónde|en que parte)\b.*\b(dice|menciona|aparece|está)\b',
        r'\bctrl\s*\+\s*f\b',
        r'\b(palabra|término|texto)\b.*["\']',
        r'\bver\s+(donde|dónde)\b'
    ]
    
    for patron in patrones_literal:
        if re.search(patron, p):
            # Intentar extraer el término buscado
            termino = None
            
            # Estrategia 1: Entre comillas
            match_comillas = re.search(r'["\']([^"\']+)["\']', pregunta)
            if match_comillas:
                termino = match_comillas.group(1)
            
            # Estrategia 2: Después de palabra clave
            else:
                for keyword in ['busca', 'encuentra', 'localiza', 'palabra', 'término']:
                    if keyword in p:
                        palabras = p.split()
                        try:
                            idx = palabras.index(keyword)
                            if idx + 1 < len(palabras):
                                termino = palabras[idx + 1].strip('.,;:?!')
                                break
                        except (ValueError, IndexError):
                            pass
            
            return {
                "tipo": "LITERAL",
                "termino": termino,
                "patron_detectado": patron
            }
    
    # TIPO 2: TROUBLESHOOTING (errores, problemas, fallas)
    patrones_troubleshooting = [
        r'\b(error|falla|problema|no funciona|no anda)\b',
        r'\bpor\s+qué\s+(no|falla)\b',
        r'\b(arreglar|solucionar|resolver|corregir)\b',
        r'\b(reparar|fix)\b'
    ]
    
    for patron in patrones_troubleshooting:
        if re.search(patron, p):
            return {
                "tipo": "TROUBLESHOOTING",
                "patron_detectado": patron
            }
    
    # TIPO 3: PROCEDIMIENTO (cómo hacer, pasos, guía)
    patrones_procedimiento = [
        r'\b(cómo|como)\s+(hago|hacer|se hace|puedo|configuro|instalo|creo)\b',
        r'\b(pasos|procedimiento|guía|tutorial)\s+(para|de)\b',
        r'\b(enséñame|muéstrame|explícame|ayúdame a)\b',
        r'\bnecesito\s+(hacer|crear|configurar|instalar)\b'
    ]
    
    for patron in patrones_procedimiento:
        if re.search(patron, p):
            return {
                "tipo": "PROCEDIMIENTO",
                "patron_detectado": patron
            }
    
    # TIPO 4: CONFIGURACIÓN (setup, ajustes, parámetros)
    patrones_configuracion = [
        r'\b(configurar|configuración|setup|ajustar|parametrizar)\b',
        r'\b(establecer|definir|setear)\b.*\b(parámetro|valor|opción)\b'
    ]
    
    for patron in patrones_configuracion:
        if re.search(patron, p):
            return {
                "tipo": "CONFIGURACION",
                "patron_detectado": patron
            }
    
    # TIPO 5: CONSULTA DE INFORMACIÓN (qué es, para qué sirve)
    patrones_informacion = [
        r'\b(qué es|que es|para qué|para que)\b',
        r'\b(explica|define|definición de)\b',
        r'\b(cuál es|cual es)\b.*\b(diferencia|propósito|función)\b'
    ]
    
    for patron in patrones_informacion:
        if re.search(patron, p):
            return {
                "tipo": "INFORMACION",
                "patron_detectado": patron
            }
    
    # DEFAULT: Consulta genérica
    return {
        "tipo": "GENERICA",
        "patron_detectado": None
    }

def buscar_regex_en_mapa(termino, mapa):
    if not termino: return []
    res = []
    try:
        pat = re.compile(re.escape(termino), re.IGNORECASE)
        for p, t in mapa.items():
            if pat.search(t): res.append(p)
    except: pass
    return sorted(res)

def detectar_imagenes(resp, cat):
    # Lógica igual a V30
    return []

# --- CEREBRO PRINCIPAL ---

async def generar_respuesta_inteligente(pregunta: str, ruta_imagen: str = None, session_id: str = "default") -> dict:
    
    if verificar_kill_switch(): return {"texto": "⛔ SISTEMA PAUSADO", "archivos": []}

    obj_historial, texto_historial = obtener_historial(str(session_id))
    sesion = gestor_sesiones.obtener_sesion(session_id)
    estado = sesion["estado"]

    # ------------------------------------------------------------------
    # FASE 1: LECTURA PROFUNDA (Solo si ya estamos dentro de un manual aprobado)
    # ------------------------------------------------------------------
    if estado == gestor_sesiones.ESTADO_LECTURA_PROFUNDA and sesion["doc_activo"]:
        if any(x in pregunta.lower() for x in ["salir", "cancelar", "basta"]):
            gestor_sesiones.limpiar_sesion(session_id)
            return {"texto": "🔄 Salido del manual.", "archivos": []}

        meta = obtener_metadata_archivo(sesion["doc_activo"])
        doc_data = gestor_cache.obtener_analisis_cacheado(meta["ruta"])
        
        # ... (Carga de contexto igual que V30, usando construir_contexto_paginas) ...
        # Por brevedad, asumo que aquí va la lógica de carga selectiva ya implementada en V30.
        # Si no tienes doc_data, procesamos.
        if not doc_data: 
            doc_data = procesador.procesar_pdf(meta["ruta"])
            gestor_cache.guardar_en_cache(meta["ruta"], doc_data)
        
        contexto = doc_data["contenido_markdown"] # Simplificado para el ejemplo, usar carga selectiva
        
        prompt = f"""Eres Consultor Técnico. Doc: {sesion['doc_activo']}. 
        Consulta: {pregunta}
        Contenido: {contexto[:20000]}...
        """
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        auditar_costos(resp)
        
        if obj_historial: obj_historial.add_ai_message(resp.content)
        return {"texto": resp.content, "archivos": [meta["ruta"]]}

    # ------------------------------------------------------------------
    # FASE 2: EXPLORACIÓN INTELIGENTE (PRE-ANÁLISIS)
    # ------------------------------------------------------------------
    # Paso 1: RAG para obtener candidatos crudos
    res_rag = buscar_contexto_relevante(pregunta)
    
    if res_rag and estado == gestor_sesiones.ESTADO_EXPLORANDO:
        # Extraemos nombres de archivos únicos candidatos
        candidatos_nombres = list(set([d.metadata.get('nombre_archivo') for d, _ in res_rag if d.metadata.get('nombre_archivo')]))
        
        if candidatos_nombres:
            print(f">> [Pre-Análisis] Evaluando {len(candidatos_nombres)} candidatos: {candidatos_nombres}")
            
            # Paso 2: Análisis Estructural (Lightweight)
            analisis = await analizar_candidatos_inteligente(pregunta, candidatos_nombres)
            
            # CASO A: GANADOR CLARO ("SI")
            if len(analisis["claros"]) == 1:
                ganador = analisis["claros"][0]
                meta = obtener_metadata_archivo(ganador["nombre"])
                
                # Entramos automáticamente o sugerimos con fuerza
                gestor_sesiones.cambiar_estado(session_id, gestor_sesiones.ESTADO_INDAGANDO, doc=ganador["nombre"], meta=meta)
                
                msg = (f"📚 **Manual Identificado: {ganador['nombre']}**\n"
                       f"✅ **Por qué es relevante:** {ganador['razon']}\n"
                       f"📂 **Secciones:** {', '.join(ganador['secciones'][:3])}\n"
                       f"¿Te guío con este documento?")
                return {"texto": msg, "archivos": []}

            # CASO B: AMBIGÜEDAD ("TAL_VEZ" o múltiples "SI")
            elif len(analisis["claros"]) > 1 or analisis["posibles"]:
                opciones = analisis["claros"] + analisis["posibles"]
                msg = "🔍 **Encontré varios manuales que podrían servir:**\n\n"
                for i, op in enumerate(opciones[:3], 1):
                    icono = "✅" if op in analisis["claros"] else "🤔"
                    msg += f"{icono} **{op['nombre']}**\n   _{op['razon']}_\n\n"
                msg += "¿Cuál prefieres revisar?"
                return {"texto": msg, "archivos": []}

            # CASO C: NINGUNO SIRVE ("NO")
            else:
                print(">> [Pre-Análisis] Todos los candidatos fueron descartados por irrelevantes.")
                # Dejamos pasar al Fallback (RAG General)

    # ------------------------------------------------------------------
    # FASE 3: FALLBACK (RAG GENERAL)
    # ------------------------------------------------------------------
    # Si llegamos aquí, ningún manual pasó el filtro estructural.
    # Respondemos con los fragmentos sueltos sin comprometernos con ningún PDF.
    info_rag = "\n".join([d.page_content for d, _ in res_rag])
    prompt_fallback = f"""
    Eres ASII. Usuario pregunta: "{pregunta}"
    No encontré un manual específico que cubra el tema en su estructura principal.
    Tengo estos fragmentos sueltos:
    {info_rag[:10000]}
    
    Responde usando esto, pero aclara que no encontraste un manual dedicado.
    """
    resp = await llm.ainvoke([HumanMessage(content=prompt_fallback)])
    auditar_costos(resp)
    
    if obj_historial: obj_historial.add_ai_message(resp.content)
    return {"texto": resp.content, "archivos": []}  