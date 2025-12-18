@echo off
echo [INFO] Iniciando instalacion del Asistente de Soporte IT...
echo [INFO] Creando entorno virtual Python...

:: Crea el entorno virtual llamado "venv"
python -m venv venv

:: Activa el entorno e instala dependencias
echo [INFO] Instalando librerias desde requirements.txt...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [EXITO] Instalacion completa. 
echo Ya puedes ejecutar 'run_bot.bat' (cuando lo configuremos).
pause