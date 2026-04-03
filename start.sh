#!/bin/bash
echo "================================================"
echo "  OfertaBot — Tech & Games Dashboard"
echo "================================================"

# Cria ambiente virtual se não existir
if [ ! -d "venv" ]; then
  echo "[1/3] Criando ambiente virtual Python..."
  python3 -m venv venv
fi

# Ativa o ambiente
source venv/bin/activate

# Instala dependências
echo "[2/3] Instalando dependências..."
pip install -r requirements.txt -q

# Inicia o servidor
echo "[3/3] Iniciando servidor na porta 5000..."
echo ""
echo "  🌐 Dashboard: abra frontend/index.html no navegador"
echo "  🔌 API:       http://localhost:5000/api/offers"
echo ""
cd backend && python server.py
