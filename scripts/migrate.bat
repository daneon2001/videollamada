@echo off
setlocal

cd /d D:\services\videollamada-python

if exist .venv\Scripts\activate.bat (
  call .venv\Scripts\activate.bat
)

alembic upgrade head

endlocal
