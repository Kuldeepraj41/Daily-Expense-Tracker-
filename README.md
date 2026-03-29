# 🚀 SpendSense — AI Expense Tracker

## Quick Start

Open **PowerShell** in the project folder and run these two commands:

```powershell
# 1. Install dependencies
pip install flask flask-sqlalchemy flask-cors pandas numpy scikit-learn python-dateutil Werkzeug

# 2. Start the app
python app.py
```

Then open your browser at **http://localhost:5000**

Click **"🌱 Load Sample Data"** in the sidebar to instantly populate the app with demo expenses!

---

## File Structure

```
Daily Expence tracker/
├── app.py                          ← Flask entry point (run this)
├── config.py                       ← Configuration
├── requirements.txt                ← Python dependencies
├── database/
│   ├── db.py                       ← SQLAlchemy setup + sample data seeder
│   └── models.py                   ← Expense, Budget, Category models
├── services/
│   ├── expense_service.py          ← CRUD operations
│   ├── analytics_service.py        ← Pandas-powered analytics
│   ├── ml_service.py               ← scikit-learn ML models
│   └── rag_service.py              ← RAG system (TF-IDF + NLG)
├── routes/
│   ├── expenses.py                 ← /api/expenses/*
│   ├── analytics.py                ← /api/analytics/*
│   ├── ml.py                       ← /api/ml/*
│   └── rag.py                      ← /api/rag/*
├── templates/
│   └── index.html                  ← Single-page app UI
└── static/
    ├── css/main.css                ← Dark glassmorphism design system
    ├── css/animations.css          ← Micro-animations
    └── js/
        ├── app.js                  ← App controller
        ├── charts.js               ← Chart.js wrappers
        ├── expenses.js             ← Expense CRUD UI
        ├── rag.js                  ← RAG chat interface
        └── utils.js                ← Shared utilities
```

---

## Features

### 💳 Expense Management
- Add / Edit / Delete expenses with category, amount, date, and notes
- Search and filter by category, date range, or keyword
- Recurring expense support

### 🤖 ML Features (scikit-learn)
| Feature | Model |
|---|---|
| Auto-categorise description | TF-IDF + Naive Bayes |
| Spending forecast (30 days) | Linear Regression |
| Anomaly detection | Isolation Forest |
| Budget burn rate | Statistical projection |
| ML Insights | Rule-based pattern mining |

### 🧠 RAG System (No API key needed!)
**Pipeline:** User Query → TF-IDF Vectorise → Cosine Similarity Retrieval → Intent Detection → Template NLG → Answer

**Knowledge Base:**
- 15 pre-loaded financial rules & tips
- Your expense records as documents
- Monthly/weekly summaries
- Category breakdown documents
- Budget status documents

**Supported intents:** spending, trend, budget, recommendations, category, forecast, anomaly

### 📊 Analytics
- Spending trend (daily/weekly/monthly charts)
- Category donut chart
- Budget vs. actual bar chart
- 14-day ML forecast chart
- Monthly stacked category bar
- Anomaly detection results

---

## Tech Stack
- **Python 3.8+** with Flask
- **SQLite** (auto-created at `data/expenses.db`)
- **scikit-learn** — all ML
- **pandas + numpy** — data processing
- **Chart.js** — visualisations (CDN)
- **Vanilla CSS** — dark glassmorphism UI
