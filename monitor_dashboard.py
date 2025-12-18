"""
ASII MONITOR DASHBOARD (monitor_dashboard.py)
---------------------------------------------
Panel de control de costos en tiempo real.
Maneja el bloqueo de API y reportes.
"""
import os
import time
import csv
import msvcrt
from datetime import datetime

# CONFIGURACIÓN
LIMITE_PRESUPUESTO = 50.00  # USD
DIR_DATA = os.path.join("data")
FILE_LOG = os.path.join(DIR_DATA, "usage_log.csv")
FILE_LOCK = os.path.join(DIR_DATA, "API_LOCKED")

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def leer_estadisticas():
    if not os.path.exists(FILE_LOG):
        return 0, 0, 0.0, []

    total_in = 0
    total_out = 0
    total_cost = 0.0
    ultimos_movimientos = []

    try:
        with open(FILE_LOG, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            for row in rows:
                total_in += int(row["Input"])
                total_out += int(row["Output"])
                total_cost += float(row["CostoUSD"])
            
            ultimos_movimientos = rows[-5:] # Últimos 5
    except:
        pass

    return total_in, total_out, total_cost, ultimos_movimientos

def exportar_reporte():
    if not os.path.exists(FILE_LOG):
        print(">> No hay datos para exportar.")
        time.sleep(2)
        return

    # Agrupar por día
    reporte = {}
    with open(FILE_LOG, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fecha = row["Fecha"]
            if fecha not in reporte:
                reporte[fecha] = 0.0
            reporte[fecha] += float(row["CostoUSD"])

    # Escribir archivo
    nombre_reporte = f"reporte_consumo_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    with open(nombre_reporte, 'w', encoding='utf-8') as f:
        f.write("REPORTE DE CONSUMOS ASII\n")
        f.write("========================\n\n")
        for fecha, gasto in reporte.items():
            f.write(f"📅 {fecha}: ${gasto:.6f} USD\n")
        f.write(f"\nGenerado el: {datetime.now()}")
    
    print(f">> ✅ Reporte exportado: {nombre_reporte}")
    time.sleep(2)

def alternar_api(forzar_stop=False):
    if forzar_stop or not os.path.exists(FILE_LOCK):
        with open(FILE_LOCK, 'w') as f:
            f.write("LOCKED_BY_USER")
    else:
        try:
            os.remove(FILE_LOCK)
        except: pass

def main():
    mostrar_detalle = False
    
    while True:
        t_in, t_out, t_cost, ultimos = leer_estadisticas()
        api_pausada = os.path.exists(FILE_LOCK)
        
        # Auto-Stop si supera presupuesto
        if t_cost >= LIMITE_PRESUPUESTO and not api_pausada:
            alternar_api(forzar_stop=True)
            api_pausada = True

        limpiar_pantalla()
        print("========================================")
        print("   ASII MONITOR - CONTROL DE COSTOS")
        print("========================================")
        print(f"💰 PRESUPUESTO:   ${LIMITE_PRESUPUESTO:.2f} USD")
        print(f"💵 GASTO ACTUAL:  ${t_cost:.6f} USD")
        print(f"📊 ESTADO API:    {'🔴 DETENIDA' if api_pausada else '🟢 ACTIVA'}")
        print("----------------------------------------")
        print(f"📥 Total Input:   {t_in:,} tokens")
        print(f"📤 Total Output:  {t_out:,} tokens")
        print("----------------------------------------")
        
        if mostrar_detalle:
            print("📜 ÚLTIMAS 5 TRANSACCIONES:")
            for m in ultimos:
                print(f"   [{m['Timestamp'].split()[1]}] In:{m['Input']} Out:{m['Output']} ${m['CostoUSD']}")
            print("----------------------------------------")

        print("\nOPCIONES:")
        print(" [1] 🛑 DETENER API (Pánico)")
        print(" [2] ▶️  INICIAR API")
        print(" [3] 💾 DESCARGAR REPORTE (TXT)")
        print(" [6] 👁️  VER DETALLE ON/OFF")
        print(" [Q] SALIR DEL MONITOR")
        print("\n>> Presione tecla...")

        # Espera no bloqueante (actualiza cada 1s si no tocas nada)
        start_time = time.time()
        while time.time() - start_time < 1.0:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                
                if key == '1': alternar_api(forzar_stop=True)
                elif key == '2': alternar_api(forzar_stop=False) # Solo reactiva si el usuario quiere, ojo con el limite
                elif key == '3': exportar_reporte()
                elif key == '6': mostrar_detalle = not mostrar_detalle
                elif key == 'q': return
                break
            time.sleep(0.1)

if __name__ == "__main__":
    main()