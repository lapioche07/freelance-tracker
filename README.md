# 🎬 Freelance Tracker — Setup Guide

A local Streamlit app to manage your clients, projects, expenses and visualize your income.

---

## ⚡ Quick Start (first time only)

### 1. Make sure Python is installed
```bash
python --version   # should be 3.9+
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`

---

## 🔁 Every time after that

Just run:
```bash
streamlit run app.py
```

---

## 📁 File structure

```
freelance_tracker_app/
├── app.py              ← the main app
├── requirements.txt    ← dependencies
├── README.md           ← this file
└── data/               ← auto-created on first run
    ├── clients.json
    ├── projects.json
    └── expenses.json
```

Your data is saved locally in the `data/` folder as simple JSON files.
No internet required, no account, no cloud.

---

## 💡 Features

- **Dashboard** — Income/Expenses bar chart, Profit Margin trend, Unpaid invoice alerts
- **Clients** — Add, edit, delete clients with status tracking
- **Projects** — Add work with income, toggle Paid/Unpaid, filter by status or client
- **Expenses** — Log monthly spending by category with stacked bar chart
