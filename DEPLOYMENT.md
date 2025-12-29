# Adizon V2 - Railway Deployment Guide

## 📋 Übersicht

Dieses Dokument beschreibt den Deployment-Prozess für Adizon V2 auf Railway.

### Projekt-Struktur auf Railway

```
📦 Railway Project: adizon-demo
├── 🐘 PostgreSQL (User-Management)
├── 🔴 Redis (Caching)
├── 🏢 Twenty CRM (Demo CRM)
├── 🐍 Adizon V2 Backend (FastAPI)
└── ⚛️  Adizon V2 Frontend (React Admin UI)
```

---

## 🚀 Schritt 1: Railway Projekt erstellen

1. Gehe zu [railway.app](https://railway.app)
2. Klicke auf "New Project"
3. Wähle "Empty Project"
4. Benenne es: **adizon-demo**

---

## 🗄️ Schritt 2: PostgreSQL hinzufügen

1. Im Projekt: **"+ New"** → **"Database"** → **"Add PostgreSQL"**
2. Warte bis deployed
3. **Wichtig:** Railway erstellt automatisch `DATABASE_URL`

### PostgreSQL Settings (optional):
- **Name:** `user-management-db`
- **Memory:** 256 MB (ausreichend)

---

## 🔴 Schritt 3: Redis hinzufügen

1. Im Projekt: **"+ New"** → **"Database"** → **"Add Redis"**
2. Warte bis deployed
3. **Wichtig:** Railway erstellt automatisch `REDIS_URL`

### Redis Settings (optional):
- **Name:** `cache`
- **Memory:** 128 MB

---

## 🏢 Schritt 4: Twenty CRM deployen

### Option A: Via GitHub Template
1. Im Projekt: **"+ New"** → **"GitHub Repo"**
2. Suche nach: `twentyhq/twenty`
3. Deploy Branch: `main`

### Option B: Via Docker Image
1. Im Projekt: **"+ New"** → **"Docker Image"**
2. Image: `twentycrm/twenty:latest`
3. Port: `3000`

### Twenty Environment-Variablen:
```bash
SERVER_URL=https://twenty-<your-domain>.up.railway.app
FRONT_BASE_URL=https://twenty-<your-domain>.up.railway.app

# PostgreSQL (Twenty braucht eine eigene DB)
PG_DATABASE_URL=<erstelle eine zweite PostgreSQL für Twenty>

# Auth
ACCESS_TOKEN_SECRET=<generiere: openssl rand -hex 32>
LOGIN_TOKEN_SECRET=<generiere: openssl rand -hex 32>
REFRESH_TOKEN_SECRET=<generiere: openssl rand -hex 32>
FILE_TOKEN_SECRET=<generiere: openssl rand -hex 32>
```

**Wichtig:** Twenty braucht eine **eigene PostgreSQL-Datenbank**. Füge eine zweite PostgreSQL hinzu (siehe Schritt 2) und nenne sie `twenty-db`.

---

## 🐍 Schritt 5: Adizon V2 Backend deployen

1. Im Projekt: **"+ New"** → **"GitHub Repo"**
2. Verbinde dein `adizon-v2` Repository
3. Root Directory: `/` (leer lassen)

### Backend Environment-Variablen:

```bash
# Database (wird automatisch von Railway gesetzt)
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Telegram
TELEGRAM_BOT_TOKEN=<dein-demo-bot-token>

# Admin
ADMIN_API_TOKEN=<generiere: openssl rand -base64 32>
ADMIN_TELEGRAM_ID=<deine-telegram-user-id>

# Twenty CRM
TWENTY_API_URL=https://twenty-<your-domain>.up.railway.app/graphql
TWENTY_API_TOKEN=<erstelle in Twenty: Settings → API → Create Token>

# CRM Config
CRM_SYSTEM=twenty
ENVIRONMENT=demo
DEMO_COMPANY_NAME=Voltage-Solutions

# Server
PORT=${{PORT}}
```

### Deploy Settings:
- **Start Command:** (wird automatisch von `railway.json` gesetzt)
- **Watch Paths:** `/` (Backend wird bei jeder Änderung neu deployed)

---

## ⚛️ Schritt 6: Adizon V2 Frontend deployen

1. Im Projekt: **"+ New"** → **"GitHub Repo"**
2. Wähle wieder dein `adizon-v2` Repository
3. **Root Directory:** `/frontend` ⚠️ **WICHTIG!**

### Frontend Environment-Variablen:

```bash
# API Connection
VITE_API_URL=https://adizon-backend-<your-domain>.up.railway.app
VITE_ADMIN_TOKEN=${{adizon-backend.ADMIN_API_TOKEN}}

# Server
PORT=${{PORT}}
```

### Deploy Settings:
- **Start Command:** (wird automatisch von `railway.json` gesetzt)
- **Root Directory:** `/frontend` ⚠️
- **Watch Paths:** `/frontend/**` (nur bei Frontend-Änderungen neu deployen)

---

## 🔗 Schritt 7: Services verknüpfen

Railway verknüpft Services automatisch via `${{ServiceName.VARIABLE}}` Syntax.

### Backend verknüpfen:
```bash
DATABASE_URL=${{user-management-db.DATABASE_URL}}
REDIS_URL=${{cache.REDIS_URL}}
```

### Frontend verknüpfen:
```bash
VITE_API_URL=https://${{adizon-backend.RAILWAY_PUBLIC_DOMAIN}}
VITE_ADMIN_TOKEN=${{adizon-backend.ADMIN_API_TOKEN}}
```

---

## 🔐 Schritt 8: Domains konfigurieren

Railway generiert automatisch Domains. Du kannst auch Custom Domains hinzufügen:

### Backend:
1. Service Settings → **Networking** → **Generate Domain**
2. Domain: `adizon-backend-demo.up.railway.app`
3. (Optional) Custom Domain: `api.adizon-demo.com`

### Frontend:
1. Service Settings → **Networking** → **Generate Domain**
2. Domain: `adizon-demo.up.railway.app`
3. (Optional) Custom Domain: `app.adizon-demo.com`

### Twenty:
1. Service Settings → **Networking** → **Generate Domain**
2. Domain: `twenty-demo.up.railway.app`
3. Trage diese Domain in Twenty's `SERVER_URL` ein!

---

## 🗄️ Schritt 9: Datenbank initialisieren

Nach dem ersten Deploy:

1. Backend sollte automatisch Migrationen ausführen (`alembic upgrade head`)
2. Überprüfe die Logs: Backend Service → **Logs**
3. Erwartete Logs:
   ```
   INFO  [alembic.runtime.migration] Running upgrade  -> c36d123f1f35
   INFO:     Application startup complete.
   ```

### Falls Migrationen nicht automatisch laufen:

1. Backend Service → **Settings** → **Deployments**
2. Klicke auf den aktuellen Deployment
3. **"View Logs"**
4. Wenn Fehler: Führe manuell aus:

**In Railway CLI:**
```bash
railway run alembic upgrade head
```

Oder **One-off Command:**
1. Service → **Settings** → **Run a one-off command**
2. Command: `alembic upgrade head`

---

## 🧪 Schritt 10: Testen

### Backend testen:
```bash
curl https://adizon-backend-demo.up.railway.app/health
# Erwartete Antwort: {"status": "healthy"}
```

### Admin API testen:
```bash
curl -H "Authorization: Bearer <ADMIN_API_TOKEN>" \
  https://adizon-backend-demo.up.railway.app/api/users/stats
# Erwartete Antwort: {"total": 0, "approved": 0, "pending": 0}
```

### Frontend testen:
1. Öffne: `https://adizon-demo.up.railway.app`
2. Sollte das Dashboard anzeigen

### Telegram Bot testen:
1. Schreibe deinem Demo-Bot: `/start`
2. Bot sollte antworten (wenn noch nicht authorized: Registrierungs-Nachricht)

---

## 🔧 Troubleshooting

### Problem: Backend startet nicht

**Lösung 1:** Überprüfe Logs
```
Service → Logs → Suche nach Fehlern
```

**Lösung 2:** Environment-Variablen überprüfen
```
Settings → Variables → DATABASE_URL sollte gesetzt sein
```

**Lösung 3:** Migrationen manuell ausführen
```bash
railway run alembic upgrade head
```

### Problem: Frontend zeigt 500 Fehler

**Ursache:** `VITE_API_URL` ist falsch oder Backend läuft nicht

**Lösung:**
1. Überprüfe `VITE_API_URL` in Frontend Settings
2. Teste Backend direkt mit curl (siehe oben)
3. Überprüfe CORS Settings im Backend (`main.py`)

### Problem: Telegram Bot antwortet nicht

**Ursache:** Webhook nicht gesetzt oder falsch

**Lösung:**
```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -d "url=https://adizon-backend-demo.up.railway.app/webhook/telegram"
```

### Problem: Twenty CRM lädt nicht

**Ursache:** `SERVER_URL` stimmt nicht mit der Railway-Domain überein

**Lösung:**
1. Kopiere die generierte Domain von Twenty Service
2. Setze in Twenty ENV: `SERVER_URL=https://<copied-domain>`
3. Restart Twenty Service

---

## 📊 Monitoring

### Logs ansehen:
1. Service auswählen
2. **"Logs"** Tab
3. Live-Logs oder Filter nach Errors

### Metriken:
1. Service auswählen
2. **"Metrics"** Tab
3. CPU, Memory, Network Usage

### Alerts einrichten:
1. Project Settings → **Integrations**
2. Slack, Discord, oder Email Notifications

---

## 💰 Kosten-Schätzung

**Railway Pricing (ca.):**
- PostgreSQL (2x): $5-10/Monat
- Redis: $5/Monat
- Backend Service: $5-10/Monat
- Frontend Service: $5/Monat
- Twenty CRM: $5-10/Monat

**Gesamt: ~$25-40/Monat** (abhängig von Traffic)

**Tipp:** Railway bietet $5 Free Credits pro Monat für Hobby-Plan.

---

## 🔄 Updates deployen

Railway deployed automatisch bei jedem Push zu GitHub!

### Backend Update:
```bash
git add .
git commit -m "Update backend"
git push origin main
# Railway deployed automatisch
```

### Frontend Update:
```bash
cd frontend
# Änderungen machen
git add .
git commit -m "Update frontend"
git push origin main
# Railway deployed automatisch (nur Frontend, weil Watch Path: /frontend/**)
```

---

## 🎯 Nächste Schritte

Nach dem Deployment:

1. ✅ **Ersten Admin-User erstellen** (via Frontend oder API)
2. ✅ **Telegram-Bot testen**
3. ✅ **Twenty CRM erkunden**
4. ✅ **Demo-Firma "Voltage-Solutions" in Twenty erstellen**
5. ✅ **CRM-Integration testen** (Kontakt erstellen via Telegram)

---

## 📝 Wichtige URLs merken

Nach dem Deployment notiere dir:

```bash
# Backend API
https://adizon-backend-demo.up.railway.app

# Admin UI
https://adizon-demo.up.railway.app

# Twenty CRM
https://twenty-demo.up.railway.app

# Telegram Bot
https://t.me/<dein-demo-bot-username>
```

---

## 🆘 Support

Bei Problemen:
1. Railway Logs überprüfen
2. Railway Docs: https://docs.railway.app
3. GitHub Issues: https://github.com/<your-repo>/issues

---

**Happy Deploying! 🚀**

