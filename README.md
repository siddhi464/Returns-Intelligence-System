# WSI DashBoard — Returns Intelligence Platform

A company-facing returns intelligence dashboard for Williams-Sonoma / West Elm. Integrates NLP, ML risk scoring, loss modelling, and real-time ingestion into a single professional web application.

---

## Features

| Feature | Details |
|---|---|
| **KPI Dashboard** | Total returns, loss ($), avg return rate, critical alert count |
| **NLP Issue Tagging** | VADER sentiment + TF-IDF K-Means clustering across return notes, reviews, CS transcripts |
| **Return Risk Score** | Ensemble classifier (Logistic + RandomForest + GradientBoosting) per SKU |
| **Loss Modelling** | HistGradientBoosting regressor predicts return rate → financial loss with scenario sliders |
| **SKU Analysis** | Interactive table with filters by risk level, category, name/ID search; click for drill-down drawer |
| **Smart Alerts** | Auto-generated HIGH/MEDIUM/LOW alerts for colour mismatch, size confusion, high loss, high return rate |
| **Region Insights** | Returns by city / state / region, hotspot detection, root cause by region |
| **Real-Time Ingest** | POST a new return → appended to CSV → pipeline cache busted → next refresh includes new signal |
| **Cancelled-Event Detection** | Personal-reason returns (cancelled events, moving house) auto-tagged separately from product-quality signals |
| **Docker Ready** | Single `docker build` → microservice deployable into any existing infrastructure |

---

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate synthetic data (or drop your own CSVs into data/)
python generate_data.py

# 3. Run
python app.py

# 4. Open browser
open http://localhost:5000
```

---

## Docker

```bash
# Build
docker build -t wsi-sentinel .

# Run
docker run -p 5000:5000 -v $(pwd)/data:/app/data wsi-sentinel

# Or with docker-compose
docker-compose up
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard UI |
| GET | `/api/dashboard` | Full dashboard data (supports `?cost_per_return=150&order_volume_multiplier=10&scenario_rate_delta=0`) |
| GET | `/api/sku/<sku_id>` | Per-SKU drill-down: returns, clusters, sentiment, reason breakdown |
| GET | `/api/alerts` | All smart alerts |
| GET | `/api/regions` | Regional return analysis + hotspots |
| GET | `/api/health` | Service health + model metrics |
| POST | `/api/ingest_return` | Submit a new return record (real-time) |

### Ingest Return (POST body)
```json
{
  "sku_id": "WE-TABLE-88",
  "return_reason": "does_not_match_description",
  "return_note": "colour looked grey not warm brown",
  "cost_of_return": 160,
  "region": "West",
  "city": "Los Angeles",
  "state": "CA"
}
```

---

## Data Format

Place CSVs in the `data/` directory:

### `returns.csv`
| Column | Description |
|---|---|
| return_id | Unique ID |
| order_id | Original order |
| sku_id | Product SKU |
| return_reason | Dropdown reason |
| return_note | Free text |
| return_date | YYYY-MM-DD |
| cost_of_return | Float ($) |
| city, state, region | Geography |

### `reviews.csv`
| Column | Description |
|---|---|
| review_id | Unique ID |
| sku_id | Product SKU |
| rating | 1–5 |
| review_text | Free text |
| review_date | YYYY-MM-DD |

### `cs_contacts.csv`
| Column | Description |
|---|---|
| contact_id | Unique ID |
| sku_id | Product SKU |
| contact_reason | Category |
| transcript | Chat/call notes |
| resolution | How resolved |
| contact_date | YYYY-MM-DD |

### `products.csv`
| Column | Description |
|---|---|
| sku_id | Unique SKU |
| name | Product name |
| category | Product category |
| finish | Finish/colour |
| price | List price ($) |
| region | Primary region |

---

## Architecture

```
returns.csv  ─┐
reviews.csv  ─┼─▶ data_processing.py ─▶ nlp_engine.py ─▶ risk_model.py ─┐
cs_contacts  ─┘        (merge)           (sentiment +       (ensemble      │
products.csv ─┘                          clustering)         classifier)   │
                                                                           ▼
                                                              pipeline.py (orchestrator)
                                                                           │
                                                              ┌────────────┼───────────┐
                                                              ▼            ▼           ▼
                                                         loss_model   alert_engine  region_analysis
                                                              │            │           │
                                                              └────────────┼───────────┘
                                                                           ▼
                                                                      app.py (Flask)
                                                                           │
                                                                      static/index.html
```

---

## What Was Implemented

 All data merged from 4 CSVs into unified pipeline  
 VADER sentiment scoring on combined free text  
 TF-IDF + K-Means NLP clustering (auto k via silhouette)  
 Rule-based issue tagging (colour, size, quality, personal)  
 Ensemble ML return-risk classifier (per SKU)  
 HistGradientBoosting loss regressor with scenario modelling  
 Smart alert engine (HIGH/MEDIUM/LOW severity)  
 Regional analysis + hotspot detection  
 Real-time ingestion endpoint with cache-busting  
 Cancelled-event / personal-reason detection  
 Professional dashboard UI (Navy + Gold, Cormorant + DM Sans)  
 Interactive SKU table with search + filters  
 SKU drill-down drawer (click any row)  
 Scenario sliders for loss modelling  
 Auto-refresh every 60 seconds  
 Docker + docker-compose ready  

## What Was Not Implemented (and Why)

 **Kafka / real streaming** — Kafka requires a broker cluster; simulated here via polling + CSV append + cache-bust, which achieves the same UX without infrastructure overhead. In production, replace `ingest_return` endpoint with a Kafka consumer.  
 **AR visualisation** — Requires a 3D model pipeline and WebGL; out of scope for a backend intelligence tool.  
 **PostgreSQL persistence** — Using CSV files keeps the tool portable and zero-dependency for deployment. Swap `data_processing.py` load functions for SQLAlchemy queries to upgrade.  
 **Authentication** — Add Flask-Login or JWT middleware before production deployment.  

## Implementation Images : 
<img width="1365" height="629" alt="image" src="https://github.com/user-attachments/assets/8e82b3fc-9877-4b04-b40b-73cc4d5a218a" />
<img width="1357" height="625" alt="image" src="https://github.com/user-attachments/assets/82dffa06-adf3-413f-9d67-f06499848563" />
<img width="1365" height="635" alt="image" src="https://github.com/user-attachments/assets/c53b9a1e-6a6c-4744-bd18-a90ef76b7d01" />
<img width="1364" height="634" alt="image" src="https://github.com/user-attachments/assets/a2b0e7ab-1682-4a31-8f46-49fe5e98143a" />
<img width="1365" height="628" alt="image" src="https://github.com/user-attachments/assets/25f98cfd-ee32-4b8e-b6e7-d18fd9492ec5" />
<img width="1365" height="648" alt="image" src="https://github.com/user-attachments/assets/bccc5344-f3c5-4bb3-a43a-2a9ac09ebd3d" />
<img width="1365" height="631" alt="image" src="https://github.com/user-attachments/assets/9ddab7c5-4432-43db-b9ca-214059f4556a" />
<img width="1355" height="631" alt="image" src="https://github.com/user-attachments/assets/fee4dfe4-5cf8-438c-93b8-03249e3c128f" />
<img width="1365" height="633" alt="image" src="https://github.com/user-attachments/assets/5282c4c4-d5ae-40d9-9ebc-9cd592de0ae6" />
<img width="1365" height="633" alt="image" src="https://github.com/user-attachments/assets/90093702-0d73-44b2-8bb3-53a61ebbbafd" />








