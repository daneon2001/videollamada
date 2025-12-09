@echo off
cd /d D:\services\videollamada-python

REM Activar venv (versión para .bat/cmd)
call .venv\Scripts\activate.bat

REM Inicializar DB (solo crea tablas si no existen)
python -c "from app.main import bootstrap; bootstrap()"

REM Levantar uvicorn desde la venv
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --proxy-headers

