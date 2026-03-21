# Pénzügyi Asszisztens v2 — Technikai Dokumentáció

## Áttekintés

Magyar nyelvű, lokális AI-alapú text-to-SQL rendszer, amely természetes nyelven feltett pénzügyi kérdésekből SQL lekérdezéseket generál és formázott választ ad. Az adatok soha nem hagyják el az infrastruktúrát (zero data leakage).

**Válaszidő**: ~2-5s (L4 GPU, warm state)
**Pontosság**: DDL séma + 30 few-shot + 30 pre-kalkulált CFO metrika
**Nyelv**: Magyar kérdés → PostgreSQL SQL → Magyar válasz

---

## Architektúra

```
Felhasználó kérdése
  ↓
[Few-shot példák betöltése] (30 hardcoded pár)
  ↓
[Prompt összeállítás] DDL séma + üzleti szabályok + few-shot + kérdés
  ↓
[qwen3:14b] SQL generálás (Ollama /api/chat, think=false)
  ↓
[SQL validáció] SELECT-only, tiltott kulcsszavak, single statement
  ↓
[SQL futtatás] PostgreSQL (async)
  ↓
[Ha hiba → retry loop] max 3x, hibaüzenettel visszaküldés
  ↓
[Válasz formázás] Python kód (0ms, determinisztikus)
  ↓
[Audit log] audit_logs tábla (user_id, question, sql, timing)
  ↓
ChatResponse (answer, sql, row_count, timing, retry_count, model)
```

---

## Fájl struktúra

### Backend — Chat modul
```
backend/app/api/v1/chat/
├── __init__.py
├── router.py              # POST /chat/ask endpoint
├── schemas.py             # ChatRequest, ChatResponse (timing+retry mezők)
├── service.py             # Fő logika: prompt build, Ollama hívás, retry loop, audit
├── semantic_schema.py     # DDL séma + üzleti szabályok + 30 few-shot példa
├── formatter.py           # Kód-alapú válasz formázás (markdown tábla, számok)
└── qdrant_store.py        # Phase 2: Qdrant RAG előkészítés (nem aktív)
```

### Backend — CFO Metrikák
```
backend/app/models/cfo_metric.py           # CfoMetric SQLAlchemy modell
backend/app/workers/tasks/calculate_metrics.py  # 30 metrika kalkuláció (Celery task)
backend/app/api/v1/dashboard/router.py     # GET /cfo-metrics, POST /cfo-metrics/calculate
```

### Backend — GPU vezérlés
```
backend/app/api/v1/admin/gpu.py  # GPU start/stop/status (AWS EC2 boto3)
```

### Frontend
```
frontend/src/features/chat/pages/ChatPage.tsx     # Chat UI + pipeline log panel
frontend/src/features/admin/pages/GpuControlPage.tsx  # GPU Control Center
frontend/src/services/api/chat.ts                 # ChatResponse interface
```

### Konfiguráció
```
backend/app/config.py   # SQL_MODEL, ANSWER_MODEL, SQL_MAX_RETRIES, OLLAMA_URL
.env.prod               # GPU_PRIVATE_IP, DB_PASSWORD, JWT_SECRET
```

---

## Modellek

| Modell | Méret | Szerep | Ollama név |
|--------|-------|--------|------------|
| qwen3:14b | 9.3 GB | SQL generálás + answer fallback | `qwen3:14b` |
| qwen2.5vl:7b | 6.0 GB | Számla OCR + adat kinyerés | `qwen2.5vl:7b` |

### Korábbi kísérletek
- `a-kore/Arctic-Text2SQL-R1-7B` — R1 reasoning modell, nem lehet kikapcsolni a gondolkodást, lassú (~6-15s)
- `mannix/defog-llama3-sqlcoder-8b` — gyors (0.6s), de nem érti a magyar nyelvet és a komplex üzleti kontextust

### Döntés indoklása
A `qwen3:14b` lett a végleges SQL modell mert:
- Érti a magyar nyelvet
- Érti az üzleti kontextust (EBITDA, feldolgozott számla, budget eltérés)
- Generalizál: éves aggregáció, period LIKE '2024%' — nem kell minden esetre few-shot
- `think=false` paraméterrel nem gondolkodik, közvetlenül SQL-t ad
- L4 GPU-n ~2-3s válaszidő

---

## GPU Infrastruktúra

### Jelenlegi: g6.xlarge (NVIDIA L4)
- **GPU**: NVIDIA L4, 24 GB GDDR6, 7424 CUDA cores, Compute 8.9
- **Instance**: g6.xlarge, eu-central-1
- **Ár**: $0.98/hr
- **VRAM**: 24 GB — egy modell egyszerre, Ollama swap-eli
- **Inference**: ~2-3s (qwen3:14b, warm state)
- **OLLAMA_KEEP_ALIVE**: 30 perc (modell VRAM-ban marad)

### Tervezett upgrade: g6e.xlarge (NVIDIA L40S)
- **GPU**: NVIDIA L40S, 48 GB GDDR6, 18176 CUDA cores
- **Bandwidth**: 864 GB/s (2.9x L4)
- **Ár**: $1.86/hr
- **VRAM**: 48 GB — mindhárom modell egyszerre betölthető
- **Becsült inference**: ~0.5-1s
- **Státusz**: Frankfurt-ban nincs kapacitás, eu-west-1 (Írország) elérhető

### Régi (leállítva): g4dn.xlarge (NVIDIA T4)
- Instance ID: `i-0c51ff7bb68200543` — **stopped**
- 16 GB VRAM, ~5-15s válaszidő

---

## 30 CFO Metrika

### Tábla: `cfo_metrics`
```sql
CREATE TABLE cfo_metrics (
    id VARCHAR(36) PRIMARY KEY,
    metric_key VARCHAR(80) NOT NULL,
    period VARCHAR(7) NOT NULL,        -- 'YYYY-MM'
    value FLOAT NOT NULL,
    currency VARCHAR(3) DEFAULT 'HUF',
    calculated_at TIMESTAMP NOT NULL,
    UNIQUE(metric_key, period)
);
```

### Metrika lista

| # | metric_key | Kategória | Leírás |
|---|-----------|-----------|--------|
| 1 | invoice_total_count | Számla | Összes számla darabszám |
| 2 | invoice_processed_count | Számla | Feldolgozott számlák száma |
| 3 | invoice_unprocessed_count | Számla | Feldolgozatlan számlák száma |
| 4 | invoice_rejected_count | Számla | Elutasított számlák száma |
| 5 | invoice_total_gross_amount | Számla | Összes bruttó összeg (HUF) |
| 6 | invoice_processed_gross_amount | Számla | Feldolgozott bruttó összeg (HUF) |
| 7 | budget_planned_total | Budget | Tervezett költségvetés (HUF) |
| 8 | budget_actual_total | Budget | Tényleges költés (HUF) |
| 9 | budget_variance | Budget | Eltérés: terv - tény (HUF) |
| 10 | budget_overage_line_count | Budget | Túlköltött budget sorok száma |
| 11 | overdue_invoice_count | Cash Flow | Lejárt határidejű számlák száma |
| 12 | overdue_invoice_amount | Cash Flow | Lejárt számlák összege (HUF) |
| 13 | upcoming_due_7d_amount | Cash Flow | 7 napon belül esedékes (HUF) |
| 14 | upcoming_due_30d_amount | Cash Flow | 30 napon belül esedékes (HUF) |
| 15 | top_supplier_amount | Partner | Legnagyobb beszállító összege (HUF) |
| 16 | active_supplier_count | Partner | Aktív beszállítók száma |
| 17 | supplier_concentration_top5_pct | Partner | Top 5 beszállító aránya (%) |
| 18 | avg_invoice_amount | Partner | Átlagos számlaérték (HUF) |
| 19 | avg_processing_time_hours | Hatékonyság | Átlagos feldolgozási idő (óra) |
| 20 | avg_approval_time_hours | Hatékonyság | Átlagos jóváhagyási idő (óra) |
| 21 | duplicate_invoice_count | Hatékonyság | Duplikátum számlák száma |
| 22 | error_rate_pct | Hatékonyság | Hibás feldolgozás aránya (%) |
| 23 | pnl_revenue | P&L | Bevétel tervezett összege (HUF) |
| 24 | pnl_ebitda | P&L | EBITDA (HUF) |
| 25 | pnl_net_income | P&L | Nettó eredmény (HUF) |
| 26 | dept_highest_spend_amount | Osztály | Legnagyobb költő részleg (HUF) |
| 27 | dept_count_over_budget | Osztály | Budget felett költő részlegek |
| 28 | po_open_count | Megrendelés | Nyitott megrendelések száma |
| 29 | po_open_amount | Megrendelés | Nyitott megrendelések összege (HUF) |
| 30 | invoice_amount_mom_change_pct | Trend | Havi változás (%) |

### Kalkuláció futtatása
```bash
# Celery task — egy hónapra
docker exec invoice-backend python -c "
from app.workers.tasks.calculate_metrics import calculate_cfo_metrics
calculate_cfo_metrics('2024-01')
"

# Összes hónap (2024 + 2025 + 2026)
docker exec invoice-backend python -c "
from app.workers.tasks.calculate_metrics import calculate_cfo_metrics
for y in [2024, 2025, 2026]:
    for m in range(1, 13):
        calculate_cfo_metrics(f'{y}-{m:02d}')
"
```

### TODO: Celery Beat scheduling (automatikus óránkénti frissítés)

---

## SQL Parser

A `parse_sql_response()` az alábbi formátumokat kezeli:

1. ` ```sql ... ``` ` code fences (prefix szöveggel is, pl. "SQL:\n```sql...")
2. `<answer>...</answer>` XML blokkok
3. Záró ` ``` ` levágás (assistant prefill esetén)
4. `SQL:` prefix eltávolítás
5. `<think>`, `<plan>` XML blokkok eltávolítása

---

## SQL Validáció

Minden retry-ban fut:
- Csak `SELECT` utasítás engedélyezett
- Tiltott kulcsszavak: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT, REVOKE, EXEC, COPY, PG_
- Csak egyetlen statement (`;` ellenőrzés string literal-okon kívül)

---

## Válasz Formázás (formatter.py)

Determinisztikus, ~0ms, LLM nélkül:
- **0 sor** → "A lekérdezés nem adott vissza eredményt."
- **1 sor, 1 oszlop** (COUNT/SUM) → formázott szám ("41 497 Ft")
- **1 sor, N oszlop** → bullet lista
- **N sor** → markdown táblázat (max 100 sor)

Magyar szám formázás: szóközök ezreselválasztóként, "Ft" pénznem, vesszős tizedes.

---

## Frontend — Chat Page

Két paneles layout:
- **Bal**: Chat buborékok (user/assistant), SQL collapsible, timing/retry badge-ek
- **Jobb**: **Pipeline Log** — terminál stílusú panel:
  - `[Q]` kérdés
  - `[SQL]` generált SQL
  - `[INFO]` modell neve, megjegyzések
  - `[TIME]` SQL generálás + teljes válaszidő ms-ben
  - `[RES]` eredmény sorok száma
  - `[ERR]` hibák

---

## Audit Log

Minden chat kérdés logolva az `audit_logs` táblába:
```json
{
  "action": "chat_query",
  "entity_type": "chat",
  "details": {
    "question": "Hány számla van?",
    "sql": "SELECT COUNT(*) ...",
    "success": true,
    "response_time_ms": 2500
  }
}
```

---

## Deploy

### Fájlok szinkronizálása
```bash
rsync -avz -e "ssh -i ~/.ssh/invoice-portal-key.pem" \
  backend/app/api/v1/chat/ ec2-user@18.194.246.133:~/invoice-manager/backend/app/api/v1/chat/
```

### Backend rebuild
```bash
ssh ec2-user@18.194.246.133 "sg docker -c 'docker compose -f ~/invoice-manager/docker-compose.prod.yml --env-file ~/invoice-manager/.env up -d --build backend'"
```

### GPU szerver — Ollama konfiguráció
```bash
# /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_KEEP_ALIVE=30m"
```

### Modellek letöltése
```bash
ollama pull qwen3:14b
ollama pull qwen2.5vl:7b
```

---

## AWS Infrastruktúra

| Komponens | Instance | IP | Megjegyzés |
|-----------|----------|----|----|
| App szerver | t3-szerű, eu-central-1 | 18.194.246.133 | Docker: backend, frontend, nginx, postgres, redis |
| GPU szerver (L4) | g6.xlarge, eu-central-1 | Private: 172.31.33.64 | Ollama + modellek |
| GPU szerver (T4, leállítva) | g4dn.xlarge | - | i-0c51ff7bb68200543, stopped |
| Domain | - | invoice.rhcdemoaccount2.com | SSL/certbot |

### Security Group szabályok (GPU)
- SSH (22): 0.0.0.0/0
- Ollama (11434): csak az app szerver SG-jéből (sg-0d0fa5f19bc4dc071)

---

## Ismert limitációk és TODO

### Jelenlegi limitációk
- Első kérés lassú (~40s) — model cold load az L4 VRAM-ba
- A qwen3 néha `SQL:` prefixet vagy ` ```sql ``` ` fences-t ad — a parser kezeli, de nem 100%
- A `cfo_metrics` manuálisan kell frissíteni (nincs Celery Beat scheduling)
- A GPU admin oldalon a start/stop a g6.xlarge-ra hardcoded

### Phase 2 tervek
- [ ] Qdrant RAG: sikeres kérdés-SQL párok vektoros tárolása, dinamikus few-shot
- [ ] Celery Beat: óránkénti metrika frissítés
- [ ] Prompt caching: statikus system message cache-elés
- [ ] Keyword matcher: gyakori CFO kérdések LLM nélkül (cfo_metrics direkt lookup)
- [ ] g6e.xlarge (L40S) upgrade eu-west-1-ben — ~0.5-1s válaszidő

### Phase 3 tervek
- [ ] Rate limiting (Redis, per user)
- [ ] Health check + monitoring (Prometheus/Grafana)
- [ ] Admin felület a few-shot példák kezeléséhez
- [ ] Multi-language support (EN/HU)
- [ ] Streaming válaszok (SSE)

---

## Teljesítmény összehasonlítás

| Konfiguráció | Válaszidő (warm) | Modell |
|-------------|-----------------|--------|
| v1: T4 + qwen3 (2x LLM hívás) | 60-90s | qwen3:14b |
| v2: T4 + Arctic R1 | 6-15s | Arctic-Text2SQL-R1-7B |
| v2: T4 + sqlcoder | 0.6s (egyszerű) / 15s (cold) | defog-llama3-sqlcoder-8b |
| **v2: L4 + qwen3 (jelenlegi)** | **2-5s** | **qwen3:14b** |
| v2: L40S + qwen3 (tervezett) | ~0.5-1s | qwen3:14b |
