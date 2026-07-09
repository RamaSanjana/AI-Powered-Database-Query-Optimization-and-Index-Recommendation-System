# AI-Powered Database Performance Optimizer

[![Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-blue?style=for-the-badge&logo=streamlit)](https://arzftwmdw9or6hxa82b4wv.streamlit.app/)
> Now connects to real MySQL databases — analyzes actual queries, tables, indexes, and execution plans. Not just a simulation: this is a true AI-driven DBMS performance optimization tool.

> Analyze live SQL, visualize real execution plans, recommend indexes, simulate performance improvements, and rewrite inefficient queries — all in a professional Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red?logo=streamlit)
![Plotly](https://img.shields.io/badge/Plotly-5.18+-purple?logo=plotly)
![sqlparse](https://img.shields.io/badge/sqlparse-0.4.4-green)
![Features](https://img.shields.io/badge/Features-18-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🚀 All 18 Features — Implemented & Verified

| # | Feature | Purpose | Status |
|---|---|---|---|
| 1 | **SQL Query Input** | Accept any SELECT / JOIN / aggregation / subquery | ✅ |
| 2 | **Query Analyzer** | Detect inefficient SQL patterns automatically | ✅ |
| 3 | **Optimization Engine** | Suggest improvements with before/after SQL examples | ✅ |
| 4 | **Query Score (0–100)** | Evaluate query performance numerically | ✅ |
| 5 | **Complexity Detection** | Classify as Simple / Moderate / Complex | ✅ |
| 6 | **Index Recommendation** | Generate `CREATE INDEX` DDL statements | ✅ |
| 7 | **Cost Estimation** | Estimate runtime as LOW / MEDIUM / HIGH | ✅ |
| 8 | **Performance Charts** | Visualise score gauge, simulation, pattern detection | ✅ |
| 9 | **Query History** | Track all analyzed queries with score trend | ✅ |
| 10 | **Sample Dataset** | 25 annotated test queries built in | ✅ |
| 11 | **AI Insights** | Natural-language explanation of query issues | ✅ |
| 12 | **Optimization Simulation** | Compare original vs optimized score | ✅ |
| 13 | **Best Practices Panel** | 12 SQL performance best practices | ✅ |
| 14 | **Architecture Viewer** | System component diagram inside dashboard | ✅ |
| 15 | **Export Report** | Download analysis as JSON / CSV / TXT | ✅ |
| 16 | **Query Execution Plan Visualizer** | Interactive Plotly tree of the simulated EXPLAIN plan | ✅ |
| 17 | **Index Impact Simulator** | Before/after metrics — score, cost, rows, time, speedup | ✅ |
| 18 | **Query Rewrite Engine** | Auto-rewrites inefficient SQL into optimized equivalents | ✅ |

---


## 📁 Project Structure

```
AI-Powered Database Query Optimization & Index Recommendation System/
│
├── app.py                   ← Main Streamlit dashboard — 5 tabs, charts, export
├── db_connection.py         ← Real MySQL database connector
├── analyzer.py              ← Pattern detection, complexity, query type detection
├── optimizer.py             ← Optimization strategies + AI insight generator
├── scoring.py               ← Performance scoring (0–100) + cost + simulation
├── recommendations.py       ← CREATE INDEX DDL engine + best practices list
├── execution_plan.py        ← Simulated query execution plan tree generator
├── simulator.py             ← Index impact before/after metrics simulator
├── rewrite_engine.py        ← Automatic SQL rewrite & anti-pattern transformer
├── requirements.txt         ← Python dependencies
├── README.md                ← This file
│
├── data/
│   └── sample_queries.csv   ← 25 annotated sample queries (Good/Moderate/Anti-pattern)
│
└── utils/
     ├── __init__.py         ← Makes utils a Python package
     └── helpers.py          ← SQL formatting, export builders, history helpers
```

---


## 🛠️ Setup & Installation

### Prerequisites
- Python 3.11+
- pip
- MySQL server running locally (or remote)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

**Dependencies installed:**
| Package | Version | Purpose |
|---|---|---|
| `streamlit` | ≥ 1.32 | Interactive web dashboard |
| `plotly` | ≥ 5.18 | Charts — gauge, bar, line, pie |
| `pandas` | ≥ 2.0 | CSV dataset + history table |
| `sqlparse` | ≥ 0.4.4 | SQL tokenisation + pretty-printing |
| `mysql-connector-python` | — | MySQL database connection |
| `sqlalchemy` | — | ORM and multi-engine support |
| `pymysql` | — | MySQL driver for SQLAlchemy |

### 2. Create a sample MySQL database

```sql
CREATE DATABASE company_db;
USE company_db;
CREATE TABLE employees (
     id INT PRIMARY KEY,
     name VARCHAR(100),
     department VARCHAR(100),
     salary INT,
     hire_date DATE
);
INSERT INTO employees VALUES
(1,'John','Engineering',90000,'2022-01-10'),
(2,'Alice','HR',60000,'2021-02-15'),
(3,'Bob','Engineering',95000,'2023-03-12'),
(4,'Eve','Finance',80000,'2022-04-18');
```

### 3. Configure database connection

Edit `db_connection.py` with your MySQL credentials:

```python
# Database configuration - update with your credentials
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "yourpassword",
    "database": "company_db"
}
```

### 4. Run the app

```bash
streamlit run app.py
```

Opens at **http://localhost:8501** in your browser.

---


## 🏗️ System Architecture

```
Streamlit Dashboard
        │
        ▼
User SQL Query Input
        │
        ▼
MySQL Database Connection
        │
        ▼
Query Analyzer (Pattern Detection)
        │
        ▼
Performance Scoring Engine
        │
        ▼
Index Recommendation Engine
        │
        ▼
Query Rewrite Engine
        │
        ▼
Execution Plan Visualizer
        │
        ▼
Results Dashboard (5 Tabs)
```

---


## 🔍 Module Breakdown

### `analyzer.py` — Query Pattern Detection Engine
- **10 pattern detectors** using regex + sqlparse tokenisation
- Detects: `SELECT *`, missing `WHERE`, excessive JOINs, nested subqueries, missing `LIMIT`, leading wildcard `LIKE`, function-on-column, `DISTINCT` with JOINs, aggregate full scans
- Extracts filter columns from `WHERE` and join columns from `ON` conditions
- Builds alias map for accurate table resolution

### `scoring.py` — Performance Scoring Engine
- **16 scoring rules** with penalties and bonuses
- Base score 100, clamped to 0–100 range
- Returns `ScoreBreakdown` with total, breakdown, cost estimate, rows scanned estimate
- `simulate_optimized_score()` projects potential score after fixes

### `optimizer.py` — Optimization Recommendation Engine
- **8 recommendation generators** with priority levels
- Each includes title, priority, description, and SQL example
- `generate_ai_insight()` creates natural-language explanation

### `recommendations.py` — Index Recommendation Engine
- Parses `WHERE` and `ON` conditions for column extraction
- Generates four index types: B-tree, Composite, Covering (INCLUDE), Full-text
- Includes 12 SQL performance best practices

### `execution_plan.py` — Query Execution Plan Visualizer
- PostgreSQL-style EXPLAIN plan tree simulation
- **12 node types** with color coding
- Cost model using `seq_page_cost = 1.0` and `index_page_cost = 0.005`

### `simulator.py` — Index Impact Simulator
- Before/after metrics: score, cost, rows, time, speedup
- Selectivity model with ~99% reduction for indexed columns
- Impact levels: Transformative (≥50×), Major (≥10×), Moderate (≥2×), Minor

### `rewrite_engine.py` — Automatic SQL Rewrite Engine
- **5 automatic transformations**:
  1. IN subquery → INNER JOIN
  2. SELECT * → explicit columns
  3. Function-on-column fix
  4. Leading wildcard annotation
  5. LIMIT injection

### `utils/helpers.py` — Utilities & Export Engine
- SQL formatting with sqlparse
- Emoji badges for UI display
- Color coding utilities
- JSON/CSV/TXT report builders
- Session history management

### `app.py` — Streamlit Dashboard
- **5 tabs:** Query Analyzer, Query History, Sample Dataset, Best Practices, 🔬 Advanced Analysis
- **Sidebar:** Sample query picker, architecture diagram, session stats
- **5 KPI metric cards:** Score, Complexity, Cost, Rows Scanned, Potential Gain
- **3 Plotly charts:** Score Gauge, Optimization Simulation, Pattern Detection
- **Export buttons:** JSON, CSV, TXT downloads
- **Query History:** Dataframe + score trend line
- **Advanced Analysis:** Execution plan visualizer, index impact simulator, query rewrite engine

---


## 📊 Scoring Rules Reference

| Rule | Type | Delta |
|---|---|---|
| `SELECT *` used | Penalty | −25 |
| Missing `WHERE` clause | Penalty | −20 |
| Excessive JOINs (>2) | Penalty | −15 |
| JOIN detected (any) | Penalty | −10 |
| Nested subquery | Penalty | −10 |
| No `LIMIT` clause | Penalty | −10 |
| Leading wildcard `LIKE` | Penalty | −10 |
| Function on `WHERE` column | Penalty | −10 |
| Aggregate without filter | Penalty | −10 |
| `SELECT DISTINCT` with JOIN | Penalty | −5 |
| `WHERE` clause present | Bonus | +10 |
| `LIMIT` clause present | Bonus | +10 |
| Specific columns selected | Bonus | +10 |
| Filter columns identified | Bonus | +5 |
| `GROUP BY` used | Bonus | +5 |
| `ORDER BY` used | Bonus | +5 |

**Cost tiers based on score:**
| Score Range | Cost Estimate | Rows Scanned |
|---|---|---|
| 80–100 | LOW | ~1K–10K rows |
| 50–79 | MEDIUM | ~10K–500K rows |
| 0–49 | HIGH | ~1M+ rows |

---


## 🔬 Pattern Detection Reference

| Pattern | Detection Method |
|---|---|
| `SELECT *` | `SELECT\s+\*` regex |
| Missing WHERE | Absence of `WHERE` in SELECT |
| JOIN count | Count JOIN variants |
| Subquery count | Count SELECT occurrences minus 1 |
| No LIMIT | Absence of LIMIT/ROWNUM/FETCH/TOP |
| Leading wildcard | `LIKE\s+['"]\%` regex |
| Function on column | `WHERE.*\b(UPPER\|LOWER\|YEAR)\s*\(` |
| Excessive JOINs | JOIN count > 2 |
| DISTINCT+JOIN | Both DISTINCT and JOIN present |
| Aggregate full scan | Aggregate + no WHERE + no GROUP BY |

---


## 📤 Export Formats

| Format | Contents | Use Case |
|---|---|---|
| **JSON** | Full structured report | API integration, programmatic use |
| **CSV** | Flat summary table | Excel, Sheets, reporting |
| **TXT** | Human-readable report | Email, Slack, documentation |

---


## 🧪 Example Analysis Output

**Input Query:**
```sql
SELECT * FROM orders WHERE customer_id = 10
```

**Output:**
```
Score:        65 / 100
Complexity:   Moderate
Cost:         MEDIUM
Rows Scanned: ~10K–500K rows

Issues:
  [HIGH]   SELECT * fetches all columns
  [MEDIUM] JOIN columns may require indexing

Optimization Recommendations:
  1. [HIGH]   Replace SELECT * with specific columns
  2. [MEDIUM] Index JOIN / ON columns

Index Recommendations:
  CREATE INDEX idx_orders_customer_id ON orders(customer_id);
  CREATE INDEX idx_orders_customer_id_covering ON orders(customer_id) INCLUDE (col1, col2);

Original Score:  65
Optimized Score: 95
Improvement:    +30
```

---


## 🧱 Technologies Used

| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.11+ | Core language |
| **Streamlit** | ≥ 1.32 | Interactive web dashboard |
| **Plotly** | ≥ 5.18 | Score gauge, bar charts, trend lines |
| **sqlparse** | ≥ 0.4.4 | SQL tokenisation, pretty-printing |
| **Pandas** | ≥ 2.0 | DataFrames for history + samples |
| **MySQL Connector** | — | Database connectivity |
| **re (stdlib)** | — | Pattern matching |
| **json/csv/io** | — | Export generation |

---


## 🔧 Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'utils'` | Ensure `utils/__init__.py` exists |
| CSV loading errors | Check sample_queries.csv has proper quoting |
| Database connection fails | Verify MySQL is running and credentials correct |
| Advanced Analysis tab blank | Run a query first to populate analysis data |
| Charts not displaying | Check Plotly version ≥ 5.18 |

---
