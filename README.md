┌─────────────────────────────────────────────────────────────┐
│                    INTERFAZ DE USUARIO                       │
│                    (Telegram Bot API)                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  CEREBRO CONVERSACIONAL                      │
│                  (brain_v7.py)                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Máquina de   │  │  Gestor de   │  │   Profile    │     │
│  │   Estados    │  │   Sesiones   │  │   Manager    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│               MOTOR RAG JERÁRQUICO (V7)                      │
│                 (rag_engine_v7.py)                          │
│  ┌──────────────────────────────────────────────────┐       │
│  │  FASE 1: BIBLIOTECARIO (Identificación)         │       │
│  │  • Búsqueda en chroma_library                    │       │
│  │  • Re-ranking con Cross-Encoder                  │       │
│  │  • Filtro por vigencia                           │       │
│  └──────────────────────────────────────────────────┘       │
│  ┌──────────────────────────────────────────────────┐       │
│  │  FASE 2: LECTOR (Recuperación de Evidencia)     │       │
│  │  • Búsqueda en chroma_content filtrada por doc_id│       │
│  │  • Re-ranking de fragmentos                      │       │
│  │  • Extracción de contexto jerárquico            │       │
│  └──────────────────────────────────────────────────┘       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              CAPA DE ALMACENAMIENTO                          │
│                                                              │
│  ┌─────────────────────┐      ┌─────────────────────┐      │
│  │  chroma_library     │      │  chroma_content     │      │
│  │  (Catálogo)         │      │  (Contenido)        │      │
│  │                     │      │                     │      │
│  │  • Fichas técnicas  │      │  • Chunks texto     │      │
│  │  • TOC + Resumen    │      │  • Metadata rica    │      │
│  │  • Detección versión│      │  • Jerarquía H1/H2  │      │
│  └─────────────────────┘      └─────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                     ▲
                     │
┌─────────────────────────────────────────────────────────────┐
│              PIPELINE DE INGESTA (V7)                        │
│                 (ingest_v7.py)                              │
│                                                              │
│  PDF → Markdown → Chunking Semántico → Embeddings E5       │
│                                                              │
│  • Detección de versiones (Soberanía)                       │
│  • Generación de doc_id (SHA256)                            │
│  • Extracción de jerarquía (H1, H2, H3)                     │
│  • Enriquecimiento de metadata                              │
└─────────────────────────────────────────────────────────────┘
