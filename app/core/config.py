"""
Módulo de Configuración (config.py)
-----------------------------------
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Configuracion:
    # --- Credenciales ---
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # --- Rutas ---
    DIRECTORIO_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    RUTA_CHROMA = os.path.join(DIRECTORIO_BASE, "data", "chroma_db")
    RUTA_DOCS = os.path.join(DIRECTORIO_BASE, "data", "raw_docs")
    
    # CORRECCIÓN PARA WINDOWS: Formato correcto de SQLite
    # Usamos f-string para asegurar que el prefijo sqlite:/// quede bien pegado
    _db_path = os.path.join(DIRECTORIO_BASE, "data", "chat_history.db")
    RUTA_HISTORIAL_CHAT = f"sqlite:///{_db_path}"

    # --- SEGURIDAD ---
    _allowed_users_str = os.getenv("ALLOWED_USER_IDS", "")
    ALLOWED_USER_IDS = [int(id.strip()) for id in _allowed_users_str.split(",") if id.strip().isdigit()]

    @staticmethod
    def es_usuario_permitido(user_id: int) -> bool:
        if not Configuracion.ALLOWED_USER_IDS: return False
        return user_id in Configuracion.ALLOWED_USER_IDS

    @staticmethod
    def validar_configuracion():
        if not Configuracion.TELEGRAM_TOKEN:
            raise ValueError("ERROR FATAL: Falta 'TELEGRAM_TOKEN'")
        print(">> [Config] Configuración cargada.")