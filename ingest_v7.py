"""
Ingesta V7.0 - Embeddings Enterprise & Semantic Chunking
--------------------------------------------------------
Mejoras sobre V6:
1. Modelo: intfloat/multilingual-e5-large (1024 dim, experto en español).
2. Chunking: Ventanas más grandes (1500 chars) para capturar procedimientos completos.
3. Separadores: Prioriza cortes lógicos (\\n\\n) sobre arbitrarios.
4. Batching: Guarda en lotes pequeños para feedback visual constante.
"""
import os
import sys
import shutil
import re
import hashlib
from datetime import datetime

# --- FIX DE RUTAS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
# --------------------

import pymupdf4llm 
import fitz 
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.core.config import Configuracion

# --- CONFIGURACIÓN DE MODELO ---
# Usamos E5-Large. Requiere aprox 1-2GB de RAM solo para cargar el modelo.
MODEL_NAME = "intfloat/multilingual-e5-large" 

# Rutas
DB_LIBRARY = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "chroma_library")
DB_CONTENT = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "chroma_content")
RAW_DOCS = Configuracion.RUTA_DOCS

# --- UTILIDADES ---

def generar_hash_archivo(ruta_pdf):
    """Crea un ID único (SHA256) basado en el CONTENIDO binario."""
    sha256_hash = hashlib.sha256()
    with open(ruta_pdf, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def normalizar_nombre(nombre_archivo):
    """Elimina versiones y fechas para encontrar la 'familia' del documento."""
    nombre = nombre_archivo.lower()
    nombre = os.path.splitext(nombre)[0]
    nombre = re.sub(r'[_ ]?20\d{2}(\d{2})?[_ ]?', '', nombre)
    nombre = re.sub(r'[_ ]?v\.?\d+(\.\d+)?[_ ]?', '', nombre)
    return nombre.strip()

# --- LÓGICA DE VERSIONADO ---

def analizar_versiones(lista_archivos):
    """Analiza todos los archivos y determina cuál es el 'master' de cada familia."""
    familias = {} 
    print(">> 🔍 Analizando versiones...")
    
    for ruta in lista_archivos:
        nombre = os.path.basename(ruta)
        familia = normalizar_nombre(nombre)
        doc_id = generar_hash_archivo(ruta)
        
        match_anio = re.search(r'(20\d{2})', nombre)
        anio = int(match_anio.group(1)) if match_anio else 2000
        
        match_ver = re.search(r'[vV]\.?(\d+\.?\d*)', nombre)
        version_str = match_ver.group(1) if match_ver else "1.0"
        try:
            version_num = float(version_str)
        except:
            version_num = 1.0

        item = {
            "ruta": ruta,
            "doc_id": doc_id,
            "anio": anio,
            "version_num": version_num,
            "version_str": version_str,
            "nombre": nombre,
            "familia": familia
        }
        
        if familia not in familias:
            familias[familia] = []
        familias[familia].append(item)
    
    mapa_final = {}
    for familia, docs in familias.items():
        # Ordenar por Año DESC, luego Versión DESC
        docs.sort(key=lambda x: (x['anio'], x['version_num']), reverse=True)
        ganador = docs[0]
        
        print(f"   🏆 Familia '{familia}': Ganador -> {ganador['nombre']} (v{ganador['version_str']})")
        
        for d in docs:
            mapa_final[d['ruta']] = {
                "doc_id": d['doc_id'],
                "es_mas_reciente": (d == ganador),
                "anio": d['anio'],
                "version": d['version_str'],
                "familia": familia,
                "nombre_archivo": d['nombre']
            }
                
    return mapa_final

# --- PROCESAMIENTO ---

def extraer_ficha_tecnica(ruta_pdf, meta_analisis):
    """Genera la ficha para el Bibliotecario (Chroma Library)."""
    try:
        doc = fitz.open(ruta_pdf)
        toc = doc.get_toc()
        toc_text = "\n".join([f"{'  '*(lvl-1)}- {title}" for lvl, title, page in toc])
        
        if len(toc_text) < 50:
            toc_text = "Resumen Intro: " + doc[0].get_text()[:1200]

        doc.close()

        estado_ver = "✅ VIGENTE" if meta_analisis['es_mas_reciente'] else "⚠️ OBSOLETO"
        
        # Enriquecemos la ficha para que el embedding E5 capture mejor el contexto semántico
        contenido_ficha = (
            f"DOCUMENTO TÉCNICO SOFTLAND ERP\n"
            f"TÍTULO: {meta_analisis['nombre_archivo']}\n"
            f"ESTADO: {estado_ver}\n"
            f"AÑO: {meta_analisis['anio']} | VERSIÓN: {meta_analisis['version']}\n"
            f"TEMARIO Y ESTRUCTURA:\n{toc_text}"
        )
        
        return Document(
            page_content=contenido_ficha,
            metadata={
                "doc_id": meta_analisis['doc_id'],
                "nombre_archivo": meta_analisis['nombre_archivo'],
                "familia_id": meta_analisis['familia'],
                "es_mas_reciente": meta_analisis['es_mas_reciente'],
                "anio": meta_analisis['anio'],
                "version": meta_analisis['version'],
                "tipo": "ficha_biblioteca"
            }
        )
    except Exception as e:
        print(f"⚠️ Error ficha {meta_analisis['nombre_archivo']}: {e}")
        return None

def procesar_contenido_profundo(ruta_pdf, meta_analisis):
    """Genera chunks estructurados para el Lector."""
    chunks_finales = []
    
    try:
        doc = fitz.open(ruta_pdf)
        
        headers_to_split_on = [("#", "h1"), ("##", "h2"), ("###", "h3")]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        
        # MEJORA V7: Chunking Semántico más grande
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500, 
            chunk_overlap=300,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        for i, page in enumerate(doc):
            num_pagina = i + 1
            try:
                md_page = pymupdf4llm.to_markdown(ruta_pdf, pages=[i])
            except:
                continue
            
            if not md_page.strip(): continue

            header_splits = markdown_splitter.split_text(md_page)
            page_chunks = text_splitter.split_documents(header_splits)
            
            for chunk in page_chunks:
                h1 = chunk.metadata.get("h1", "General")
                h2 = chunk.metadata.get("h2", "")
                
                if len(chunk.page_content.strip()) < 50: continue

                # Inyección de contexto en el contenido del chunk
                contenido_enriquecido = f"MANUAL: {meta_analisis['nombre_archivo']}\nSECCIÓN: {h1} > {h2}\n\n{chunk.page_content}"
                chunk.page_content = contenido_enriquecido

                chunk.metadata.update({
                    "doc_id": meta_analisis['doc_id'],
                    "nombre_archivo": meta_analisis['nombre_archivo'],
                    "pagina_inicio": num_pagina,
                    "origen": "contenido_profundo",
                    "tipo_chunk": "texto" if "|" not in chunk.page_content else "tabla",
                    "h1": h1,
                    "h2": h2,
                    "nivel_profundidad": 2 if h2 else 1,
                    "es_mas_reciente": meta_analisis['es_mas_reciente'],
                    "anio": meta_analisis['anio']
                })
                chunks_finales.append(chunk)
                
        doc.close()
        return chunks_finales

    except Exception as e:
        print(f"⚠️ Error procesando contenido de {meta_analisis['nombre_archivo']}: {e}")
        return []

def guardar_en_chroma_con_progreso(docs, embeddings, directorio, etiqueta="Docs"):
    """
    Guarda documentos en lotes pequeños para mostrar progreso en consola.
    Evita la sensación de 'congelamiento' con modelos pesados.
    """
    if not docs: return
    print(f">> Iniciando indexación de {len(docs)} {etiqueta} en {directorio}...")
    
    # Instanciamos la DB una vez
    db = Chroma(embedding_function=embeddings, persist_directory=directorio)
    
    # Tamaño del lote (50 es seguro para CPU/Memoria)
    BATCH_SIZE = 50
    total = len(docs)
    
    for i in range(0, total, BATCH_SIZE):
        lote = docs[i : i + BATCH_SIZE]
        db.add_documents(lote)
        
        # Feedback visual
        progreso = min(i + BATCH_SIZE, total)
        print(f"   [{etiqueta}] Guardando {progreso}/{total} ({(progreso/total)*100:.1f}%)")

def ingest_v7():
    print(f"--- INICIANDO INGESTA V7.0 (MODELO: {MODEL_NAME}) ---")
    
    # 1. Limpieza
    if os.path.exists(DB_LIBRARY): shutil.rmtree(DB_LIBRARY)
    if os.path.exists(DB_CONTENT): shutil.rmtree(DB_CONTENT)
    
    # 2. Escaneo
    archivos_pdf = []
    if not os.path.exists(RAW_DOCS):
        print(f"❌ Error: No existe el directorio {RAW_DOCS}")
        return

    for root, dirs, files in os.walk(RAW_DOCS):
        for file in files:
            if file.lower().endswith(".pdf"):
                archivos_pdf.append(os.path.join(root, file))
    
    if not archivos_pdf:
        print("❌ No hay PDFs en data/raw_docs")
        return

    # 3. Análisis de Versiones
    mapa_versiones = analizar_versiones(archivos_pdf)
    
    docs_biblio = []
    docs_cont = []
    
    # 4. Procesamiento
    print(">> 🧠 Cargando modelo de Embeddings (puede tardar)...")
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    
    for ruta in archivos_pdf:
        meta = mapa_versiones[ruta]
        print(f"   ⚙️  Ingestando: {meta['nombre_archivo']}")
        
        # A. Ficha Biblioteca
        ficha = extraer_ficha_tecnica(ruta, meta)
        if ficha: docs_biblio.append(ficha)
        
        # B. Contenido Profundo
        chunks = procesar_contenido_profundo(ruta, meta)
        docs_cont.extend(chunks)

    # 5. Guardado por Lotes
    if docs_biblio:
        guardar_en_chroma_con_progreso(docs_biblio, embeddings, DB_LIBRARY, "Fichas")
        guardar_en_chroma_con_progreso(docs_cont, embeddings, DB_CONTENT, "Fragmentos")
        
        print("✅ INGESTA V7 COMPLETADA. (Base de datos optimizada)")
    else:
        print("❌ Error crítico: No se generaron documentos.")

if __name__ == "__main__":
    ingest_v7()