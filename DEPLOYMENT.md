# 🚀 Guía de Despliegue - ASII V7.0

## Instalación Local

### Prerrequisitos
- Python 3.11+
- 4GB RAM mínimo (8GB recomendado)
- Git

### Pasos
```bash
# 1. Clonar
git clone https://github.com/Maurito27/ASII.git
cd ASII

# 2. Entorno virtual
python -m venv venv
venv\Scripts\activate  # Windows

# 3. Dependencias
pip install -r requirements.txt

# 4. Configurar
copy .env.example .env
# Editar .env con tus API keys

# 5. Agregar PDFs
# Copiar documentos a data/raw_docs/

# 6. Ingesta
python data/ingest_v7.py

# 7. Ejecutar
python run_bot.bat
```

## Variables de Entorno Requeridas
```bash
GOOGLE_API_KEY=tu_clave_gemini
TELEGRAM_BOT_TOKEN=tu_token_bot
```

Obtener keys:
- Gemini: https://ai.google.dev/
- Telegram: @BotFather

## Troubleshooting

**Error: ModuleNotFoundError**
```bash
pip install -r requirements.txt
```

**Bot no responde**
- Verificar token en .env
- Verificar que run_bot.bat esté corriendo

**Ingesta falla**
- Verificar PDFs en data/raw_docs/
- Mínimo 4GB RAM libre
