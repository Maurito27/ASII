"""
Gestor de Caché Inteligente (cache_manager.py)
----------------------------------------------
Evita reprocesar documentos. Guarda el análisis estructural en JSON.
Usa SHA256 del contenido del archivo para invalidar caché si el PDF cambia.
"""
import os
import json
import hashlib
from app.core.config import Configuracion

class CacheManager:
    def __init__(self):
        # Carpeta donde guardaremos los cerebros procesados
        self.cache_dir = os.path.join(Configuracion.DIRECTORIO_BASE, "data", "cache_docs")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _generar_hash_archivo(self, ruta_pdf):
        """Crea un ID único basado en el CONTENIDO binario del archivo."""
        sha256_hash = hashlib.sha256()
        with open(ruta_pdf, "rb") as f:
            # Leemos en bloques por si el archivo es gigante
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def obtener_analisis_cacheado(self, ruta_pdf):
        """Intenta recuperar el JSON procesado. Retorna None si no existe."""
        if not os.path.exists(ruta_pdf):
            return None
            
        file_hash = self._generar_hash_archivo(ruta_pdf)
        ruta_json = os.path.join(self.cache_dir, f"{file_hash}.json")
        
        if os.path.exists(ruta_json):
            try:
                with open(ruta_json, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    print(f">> [Caché] HIT: Documento recuperado de memoria ({os.path.basename(ruta_pdf)})")
                    return datos
            except Exception as e:
                print(f"[Caché Error] {e}")
                return None
        
        print(f">> [Caché] MISS: El documento no está procesado ({os.path.basename(ruta_pdf)})")
        return None

    def guardar_en_cache(self, ruta_pdf, datos_procesados):
        """Guarda el diccionario de análisis en disco."""
        file_hash = self._generar_hash_archivo(ruta_pdf)
        ruta_json = os.path.join(self.cache_dir, f"{file_hash}.json")
        
        try:
            with open(ruta_json, 'w', encoding='utf-8') as f:
                json.dump(datos_procesados, f, ensure_ascii=False, indent=2)
            print(f">> [Caché] SAVE: Análisis guardado exitosamente.")
        except Exception as e:
            print(f"[Caché Error Save] {e}")

# Instancia global
gestor_cache = CacheManager()