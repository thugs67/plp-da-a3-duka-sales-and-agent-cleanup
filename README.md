# Project Summary: Duka Electronics & Mobile Money Agent Network

## 1. Summary of Both Engagements

* **Engagement 1 — Duka Electronics Commercial & Channel Analytics (`duka_sales.csv`):**
  * **Scope:** Audited and analyzed **1,000** retail electronics orders across **5** Kenyan branches (`Nairobi`, `Mombasa`, `Nakuru`, `Kisumu`, `Eldoret`), **5** SKUs (`Laptop`, `Tablet`, `Phone`, `Headphones`, `Charger`), and **3** sales channels (`In-store`, `Online`, `Phone order`) from `2026-01-01` through `2026-06-29`.
  * **Deliverables:** Engineered revenue, calendar (`month`, `weekday`, `is_weekend`), and `price_band` (`Premium` $\ge$ KES 28,000 vs. `Value`) features; ranked branch, product, and weekday/weekend performance; exported the **83** high-value Nairobi/Mombasa Premium online orders to `premium_online_coast_capital.csv`; and built a reconciled Excel workbook (`excel/duka_branch_summary.xlsx`) using live `SUMIFS`, `COUNTIFS`, `XLOOKUP`, `RANK`, and a branch-by-channel summary matrix verified against `pandas`.

* **Engagement 2 — Mobile Money Agent Network Data Quality & Reconciliation (`agents.csv` & `agent_transactions.csv`):**
  * **Scope:** Audited a **20-row** registered agent directory (`AG001`–`AG020`) and a **612-row** raw transaction log (`2026-03-01` through `2026-04-29`) seeded with duplicates, mixed string casing/whitespace, mixed date delimiters, missing/invalid amounts (`""` and `"N/A"`), extreme `KES 250,000` outliers, and unregistered agent IDs (`AG099`).
  * **Deliverables:** Packaged a deterministic, rule-based cleaning pipeline (`clean_agent_data(txns, agents)`) into `cleaning_pipeline.py` returning `(clean_df, log)`, quarantined orphan records via a diagnostic `left` join, produced county-by-transaction-type summaries and a weekly county volume pivot table, and documented personal data protections under the **Kenya Data Protection Act, 2019**.


---

