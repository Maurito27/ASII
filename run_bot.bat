@echo off
:: Título de la ventana
title ASII - Asistente de Soporte IT

echo [INFO] Iniciando sistema...
echo [INFO] Verificando entorno virtual...

:: Verificamos si existe la carpeta venv
if not exist venv (
    echo [ERROR] No se detecta el entorno virtual 'venv'.
    echo [SOLUCION] Por favor, ejecuta primero 'install.bat'.
    pause
    exit
)

:: Activamos el entorno virtual
call venv\Scripts\activate

:: Ejecutamos el punto de entrada principal (main.py) como modulo
:: Usamos 'python -m app.main' para que reconozca las importaciones relativas
echo [INFO] Arrancando el Bot...
python -m app.main

:: Si el bot se cierra por error, pausamos para leer que paso
if %errorlevel% neq 0 (
    echo.
    echo [ALERTA] El sistema se cerro inesperadamente. Revisa el error arriba.
    pause
)