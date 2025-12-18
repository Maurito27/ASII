"""
Motor RAG V8.0 - Vision-Aware Retrieval
---------------------------------------
Sincronizado con Ingesta V8.
Modelo: intfloat/multilingual-e5-large
Mejoras: Capacidad de recuperar chunks basados en texto OCR oculto.
"""
import os
import sys

# Fix de rutas
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../.."))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from app.core.config import Configuracion
from app.core.contracts import SCORE_THRESHOLD 

# --- CONFIGURACIÓN (Debe coincidir con ingest_v8.py) ---
MODEL_NAME = "intfloat/multilingual-e5-large"
_embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)

# Modelo de Re-Ranking (Validación de calidad)
_reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def get_db_library():
    return Chroma(persist_directory=os.path.join(Configuracion.DIRECTORIO_BASE, "data", "chroma_library"), embedding_function=_embeddings)

def get_db_content():
    return Chroma(persist_directory=os.path.join(Configuracion.DIRECTORIO_BASE, "data", "chroma_content"), embedding_function=_embeddings)

def buscar_manual_candidato(query: str, k: int = 5):
    """
    Fase 1: Bibliotecario.
    """
    db = get_db_library()
    filtro_vigencia = {"es_mas_reciente": True}
    
    try:
        # E5 requiere prefijo "query: "
        query_e5 = f"query: {query}"
        resultados_crudos = db.similarity_search_with_score(query_e5, k=10, filter=filtro_vigencia)
    except Exception as e:
        print(f"[RAG Error] Biblioteca: {e}")
        return []
    
    if not resultados_crudos: return []

    # Re-Ranking
    pares = [(query, doc.page_content) for doc, _ in resultados_crudos]
    scores_rerank = _reranker.predict(pares)

    candidatos_rankeados = []
    for (doc, original_score), rerank_score in zip(resultados_crudos, scores_rerank):
        candidatos_rankeados.append({
            "doc_id": doc.metadata.get("doc_id"),
            "nombre_archivo": doc.metadata.get("nombre_archivo"),
            "anio": doc.metadata.get("anio"),
            "version": doc.metadata.get("version"),
            "score": original_score,
            "rerank_score": rerank_score,
            "resumen": doc.page_content[:500]
        })

    candidatos_rankeados.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidatos_rankeados[:k]

def buscar_contenido_profundo(query: str, doc_id: str, k: int = 8):
    """
    Fase 2: Lector con Visión.
    Busca en texto normal Y en texto extraído de imágenes (OCR).
    """
    db = get_db_content()
    filtro_archivo = {"doc_id": doc_id}
    
    try:
        query_e5 = f"query: {query}"
        # Traemos más candidatos (k=20) porque ahora hay más 'ruido' visual que filtrar
        resultados_crudos = db.similarity_search_with_score(query_e5, k=20, filter=filtro_archivo)
    except Exception as e:
        print(f"[RAG Error] Contenido: {e}")
        return []
    
    if not resultados_crudos: return []

    # Re-Ranking
    pares = [(query, doc.page_content) for doc, _ in resultados_crudos]
    scores_rerank = _reranker.predict(pares)
    
    evidencias = []
    for (doc, original_score), rerank_score in zip(resultados_crudos, scores_rerank):
        if rerank_score < -4.0: continue 

        # Detectamos si viene de OCR para indicarlo en el chat (Opcional)
        es_ocr = "[CONTENIDO VISUAL" in doc.page_content
        origen_tag = " (Diagrama/Img)" if es_ocr else ""

        evidencias.append({
            "texto": doc.page_content,
            "pagina": doc.metadata.get("pagina_inicio", "N/A"), 
            "seccion": f"{doc.metadata.get('h1', '')} > {doc.metadata.get('h2', '')}{origen_tag}",
            "tipo": doc.metadata.get("tipo_chunk", "texto"),
            "rerank_score": rerank_score
        })
    
    evidencias.sort(key=lambda x: x["rerank_score"], reverse=True)
    return evidencias[:k]
