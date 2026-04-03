@echo off
echo ================================================
echo   OfertaBot — Tech & Games Dashboard
echo ================================================

if not exist venv (
    echo [1/3] Criando ambiente virtual Python...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo [2/3] Instalando dependencias...
pip install -r requirements.txt -q

echo [3/3] Iniciando servidor na porta 5000...
echo.
echo   Dashboard: abra frontend\index.html no navegador
echo   API:       http://localhost:5000/api/offers
echo.
cd backend && python server.py
pause
