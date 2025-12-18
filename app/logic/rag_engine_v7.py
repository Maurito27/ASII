"""
Motor RAG V7.0 - Embeddings E5 + Cross-Encoder Re-Ranking
---------------------------------------------------------
Mejoras:
1. Usa 'intfloat/multilingual-e5-large' para búsqueda semántica profunda.
2. Implementa 'CrossEncoder' para re-ordenar resultados y eliminar falsos positivos.
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
# Importamos CrossEncoder para el re-ranking
from sentence_transformers import CrossEncoder
from app.core.config import Configuracion
from app.core.contracts import SCORE_THRESHOLD 

# 1. MODELO DE EMBEDDINGS (El mismo de la ingesta V7)
MODEL_NAME = "intfloat/multilingual-e5-large"
_embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)

# 2. MODELO DE RE-RANKING (Pequeño pero potente para validar pares query-doc)
_reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

def get_db_library():
    return Chroma(persist_directory=os.path.join(Configuracion.DIRECTORIO_BASE, "data", "chroma_library"), embedding_function=_embeddings)

def get_db_content():
    return Chroma(persist_directory=os.path.join(Configuracion.DIRECTORIO_BASE, "data", "chroma_content"), embedding_function=_embeddings)

def buscar_manual_candidato(query: str, k: int = 5):
    """
    Busca manuales y aplica Re-Ranking para asegurar que el TOP 1 sea el mejor.
    """
    db = get_db_library()
    filtro_vigencia = {"es_mas_reciente": True}
    
    # 1. Retrieval (Traemos más candidatos de lo normal, k=10, para que el reranker filtre)
    try:
        # Nota: E5 requiere el prefijo "query: " para funcionar óptimamente
        query_e5 = f"query: {query}"
        resultados_crudos = db.similarity_search_with_score(query_e5, k=10, filter=filtro_vigencia)
    except Exception as e:
        print(f"[RAG Error] Biblioteca: {e}")
        return []
    
    if not resultados_crudos: return []

    # 2. Re-Ranking (Cross-Encoder)
    # Preparamos pares [query, document_text]
    pares = [(query, doc.page_content) for doc, _ in resultados_crudos]
    scores_rerank = _reranker.predict(pares)

    candidatos_rankeados = []
    for (doc, original_score), rerank_score in zip(resultados_crudos, scores_rerank):
        # Mantenemos el score original para los umbrales viejos, pero usamos rerank para ordenar
        candidatos_rankeados.append({
            "doc_id": doc.metadata.get("doc_id"),
            "nombre_archivo": doc.metadata.get("nombre_archivo"),
            "anio": doc.metadata.get("anio"),
            "version": doc.metadata.get("version"),
            "score": original_score, # Mantenemos L2 para compatibilidad
            "rerank_score": rerank_score, # Nuevo score de inteligencia
            "resumen": doc.page_content[:500]
        })

    # Ordenar por el cerebro del CrossEncoder (Mayor es mejor)
    candidatos_rankeados.sort(key=lambda x: x["rerank_score"], reverse=True)
    
    # Debug para ver si el reranker está funcionando
    top = candidatos_rankeados[0]
    print(f">> [RAG V7] Top Match: {top['nombre_archivo']} (Rerank Score: {top['rerank_score']:.4f})")

    return candidatos_rankeados[:k]

def buscar_contenido_profundo(query: str, doc_id: str, k: int = 8):
    """
    Busca contenido dentro de un manual específico con Re-Ranking.
    """
    db = get_db_content()
    filtro_archivo = {"doc_id": doc_id}
    
    try:
        query_e5 = f"query: {query}"
        # Traemos 15 candidatos para que el reranker elija los mejores
        resultados_crudos = db.similarity_search_with_score(query_e5, k=15, filter=filtro_archivo)
    except Exception as e:
        print(f"[RAG Error] Contenido: {e}")
        return []
    
    if not resultados_crudos: return []

    # Re-Ranking
    pares = [(query, doc.page_content) for doc, _ in resultados_crudos]
    scores_rerank = _reranker.predict(pares)
    
    evidencias = []
    for (doc, original_score), rerank_score in zip(resultados_crudos, scores_rerank):
        # Filtro de calidad del Reranker: Descartar negativos fuertes
        if rerank_score < -4.0: continue 

        evidencias.append({
            "texto": doc.page_content,
            "pagina": doc.metadata.get("pagina_inicio", "N/A"), 
            "seccion": f"{doc.metadata.get('h1', '')} > {doc.metadata.get('h2', '')}",
            "tipo": doc.metadata.get("tipo_chunk", "texto"),
            "score": original_score,
            "rerank_score": rerank_score
        })
    
    # Ordenar por relevancia real
    evidencias.sort(key=lambda x: x["rerank_score"], reverse=True)
    return evidencias[:k]