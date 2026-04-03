# 🤖 OfertaBot — Tech & Games (Railway)

Dashboard web para monitorar ofertas de tecnologia e jogos em tempo real.

## 🚀 Deploy no Railway (passo a passo)

### 1. Suba o código no GitHub

```bash
git init
git add .
git commit -m "primeiro commit"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/oferta-bot.git
git push -u origin main
```

### 2. Crie o projeto no Railway

1. Acesse railway.app e faça login com o GitHub
2. Clique em "New Project"
3. Escolha "Deploy from GitHub repo"
4. Selecione o repositório oferta-bot
5. Railway detecta automaticamente o Python e faz o build

### 3. Acesse o dashboard

1. Após o deploy, vá em Settings → Networking
2. Clique em "Generate Domain"
3. Pronto! Seu dashboard estará em https://oferta-bot-xxxx.up.railway.app

---

## Estrutura

```
oferta-bot/
├── backend/
│   ├── scraper.py      # Scrapers de cada plataforma
│   └── server.py       # API Flask + serve o frontend
├── frontend/
│   └── index.html      # Dashboard web
├── data/               # Cache local (ignorado no git)
├── Procfile            # Comando de start para o Railway
├── nixpacks.toml       # Configuração de build
├── railway.json        # Config do Railway
├── requirements.txt    # Dependências Python
└── .gitignore
```

## Endpoints da API

- GET  /api/offers   — Lista ofertas (filtros: category, source, min_discount, q, sort, page)
- GET  /api/stats    — Estatísticas gerais
- POST /api/refresh  — Dispara nova coleta
- GET  /api/sources  — Lista as fontes

## Para rodar local também

```bash
pip install -r requirements.txt
python backend/server.py
```

Acesse http://localhost:5000
