"""
Punto de Entrada Principal (main.py)
------------------------------------
Orquestador del sistema. Valida configuración e inicia la interfaz de Telegram.
"""

import sys
import asyncio
from app.core.config import Configuracion
# Importamos la función que acabamos de crear para arrancar el bot
from app.interfaces.telegram_bot import iniciar_bot

def main():
    """
    Función maestra. No es asíncrona porque 'run_polling' de Telegram
    ya maneja su propio bucle de eventos (Event Loop).
    """
    print("--- INICIANDO ASISTENTE DE SOPORTE IT (ASII) ---")
    
    try:
        # 1. Validar configuración inicial
        Configuracion.validar_configuracion()
        
        print(f">> [Sistema] Directorio de Datos: {Configuracion.RUTA_DOCS}")
        print(">> [Sistema] Verificación completada. Lanzando interfaz...")
        
        # 2. Iniciar el Bot de Telegram (Esto bloqueará la consola mientras funcione)
        iniciar_bot()
        
    except KeyboardInterrupt:
        print("\n>> [Salida] Bot detenido por el usuario.")
    except Exception as e:
        print(f"\n[!!!] ERROR CRÍTICO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()