"""
Contratos de Datos - ASII V8 Enterprise (contracts.py)
------------------------------------------------------
Actualizado para Cross-Encoder (Logits) y Embeddings E5.
"""

from typing import TypedDict, Literal, Optional

# --- CONSTANTES DE NEGOCIO ---

# UMBRALES PARA CROSS-ENCODER (Logits de MS-MARCO)
# > 3.0: Certeza casi absoluta
# > 1.0: Relevancia alta
# > -1.0: Relevancia posible/media
# < -1.0: Irrelevante / Ruido
SCORE_THRESHOLD = {
    "HIGH_CONFIDENCE": 2.5,  # Auto-selección
    "MEDIUM_CONFIDENCE": -1.0, # Confirmar con usuario
    "MIN_RELEVANCE": -4.0    # Descarte absoluto
}

# --- ESQUEMAS DE METADATOS ---

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
    es_mas_reciente: bool
    anio: int
    tiene_ocr: bool
