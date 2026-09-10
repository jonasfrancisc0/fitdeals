@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if not exist ".env" (
    copy ".env.example" ".env"
    echo.
    echo Arquivo .env criado. Edite-o antes de conectar ao Mercado Livre.
)
echo.
echo Iniciando FitDeals V4...
python -m uvicorn app.main:app --reload
pause
