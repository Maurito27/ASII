"""
Contratos de Datos - ASII V6 Enterprise (contracts.py)
------------------------------------------------------
Define la estructura estricta de los metadatos y constantes del sistema.
Cumple con el DET V6.0 para asegurar consistencia entre Ingesta, RAG y Cerebro.
"""

from typing import TypedDict, Literal, Optional

# --- CONSTANTES DE NEGOCIO ---

# Umbrales de Confianza (Scoring L2 de Chroma)
# Menor distancia = Mayor similitud
SCORE_THRESHOLD = {
    "AUTO_SELECT": 0.55, # Seremos más estrictos al principio
    "CONFIRM": 0.85,     
    "DISCARD": 1.0       
}

# --- ESQUEMAS DE METADATOS (Tipado estático para referencia) ---

class LibraryMetadata(TypedDict):
    doc_id: str
    nombre_archivo: str
    familia_id: str
    version: str
    anio: int
    es_mas_reciente: bool
    tipo: Literal["ficha_biblioteca"]
    resumen: str
    
class ContentMetadata(TypedDict):
    doc_id: str
    nombre_archivo: str
    tipo_chunk: Literal["texto", "tabla", "imagen_descrita"]
    h1: Optional[str]
    h2: Optional[str]
    nivel_profundidad: int
    pagina_inicio: int
    origen: Literal["contenido_profundo"]
    # Agregamos campo para debugging de relevancia
    es_mas_reciente: bool 
    anio: int