"""
Gestor de Sesiones V24 (session_manager.py) - Enterprise State Machine
----------------------------------------------------------------------
Controla el flujo de estados del asistente y el contexto del usuario.
Actualizado para soportar lógica de reintentos y manipulación granular de metadata.
"""
from typing import Dict, Optional, Any

class SessionManager:
    # Constantes de Estado
    ESTADO_EXPLORANDO = "EXPLORANDO"              # Estado inicial / Diagnóstico
    ESTADO_ESPERANDO_CONFIRMACION = "CONFIRMANDO" # Transición: Bot propone, Usuario decide
    ESTADO_LECTURA_PROFUNDA = "LEYENDO"           # Estado final: Contexto cargado y respondiendo

    def __init__(self):
        # Estructura de sesión en memoria:
        # { 
        #   "chat_id": { 
        #       "estado": str, 
        #       "perfil": str ("ADMIN"|"SISTEMAS"),
        #       "doc_activo": str|None, 
        #       "metadata": dict,             # Contexto del documento o candidato
        #       "intentos_fallidos": int,     # Circuit Breaker para loops
        #       "historial_corto": list       # (Opcional) Para lógica rápida
        #   } 
        # }
        self._sesiones: Dict[str, dict] = {}

    def obtener_sesion(self, chat_id: str) -> dict:
        """Recupera la sesión actual o crea una nueva default si no existe."""
        chat_id = str(chat_id)
        if chat_id not in self._sesiones:
            self.limpiar_sesion(chat_id)
        return self._sesiones[chat_id]

    def cambiar_estado(self, chat_id: str, nuevo_estado: str, doc: Optional[str] = None, meta: Optional[dict] = None):
        """
        Realiza una transición mayor de estado.
        Resetea el contador de intentos fallidos al cambiar de estado exitosamente.
        """
        chat_id = str(chat_id)
        sesion = self.obtener_sesion(chat_id)
        
        sesion["estado"] = nuevo_estado
        
        # Si cambiamos de estado, asumimos progreso, reseteamos contador de loops
        sesion["intentos_fallidos"] = 0

        if doc:
            sesion["doc_activo"] = doc
        if meta:
            sesion["metadata"] = meta

        print(f">> [Sesión {chat_id}] Cambio de estado -> {nuevo_estado} (Doc: {doc})")

    def actualizar_metadata(self, chat_id: str, data: Dict[str, Any]):
        """
        Actualiza parcialmente el diccionario de metadata sin alterar el estado.
        Útil para guardar candidatos pendientes o preferencias volátiles.
        """
        chat_id = str(chat_id)
        if chat_id in self._sesiones:
            if "metadata" not in self._sesiones[chat_id]:
                self._sesiones[chat_id]["metadata"] = {}
            
            # Update dict existente
            self._sesiones[chat_id]["metadata"].update(data)
            print(f">> [Sesión {chat_id}] Metadata actualizada: {list(data.keys())}")

    def registrar_intento_fallido(self, chat_id: str) -> int:
        """
        Incrementa el contador de intentos fallidos/búsquedas vacías.
        Retorna el número actual de intentos.
        """
        chat_id = str(chat_id)
        sesion = self.obtener_sesion(chat_id)
        sesion["intentos_fallidos"] = sesion.get("intentos_fallidos", 0) + 1
        return sesion["intentos_fallidos"]

    def actualizar_sesion(self, chat_id: str, **kwargs):
        """Generic updater para campos de primer nivel (ej: perfil)."""
        chat_id = str(chat_id)
        if chat_id in self._sesiones:
            for k, v in kwargs.items():
                self._sesiones[chat_id][k] = v

    def limpiar_sesion(self, chat_id: str):
        """Reseteo total a modo explorador (Hard Reset)."""
        chat_id = str(chat_id)
        # Preservamos el perfil si existía, si no default a ADMIN
        perfil_previo = "ADMIN"
        if chat_id in self._sesiones:
            perfil_previo = self._sesiones[chat_id].get("perfil", "ADMIN")

        self._sesiones[chat_id] = {
            "estado": self.ESTADO_EXPLORANDO,
            "perfil": perfil_previo,
            "doc_activo": None,
            "metadata": {},
            "intentos_fallidos": 0
        }
        print(f">> [Sesión {chat_id}] Reiniciada a Exploración (Perfil: {perfil_previo}).")

# Instancia global singleton
gestor_sesiones = SessionManager()