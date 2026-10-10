# MoveInSync Play Store Review Analysis — Methodology & Tooling Note

**Document Purpose:** Required submission note detailing data sourcing, analysis methodology, toolstack, assumptions, and validation.

---

## 1. Data Sourcing & Scraper Architecture

- **Public Data Source:** Google Play Store public review API for MoveInSync ETS (`com.moveinsync.ets`).
- **Scraper Implementation (`scraper.py`):** Utilizes `google-play-scraper` pagination API with continuation tokens.
- **Collection Date:** 2026-10-10 18:12:55
- **Target Limit & Coverage:** 1,000 unique reviews (Date Range: 2026-06-14 to 2026-10-09).
- **Deduplication Strategy:** Each incoming review is hashed by its unique `reviewId`. The scraper skips already-seen hashes, ensuring **0 duplicate reviews** in the final dataset.
- **Scraper Resilience:** Implements 3-tier exponential backoff retry logic and network error tracking.

---

## 2. NLP Multi-Label Classification Methodology (`analysis.py`)

- **Classification Engine:** Deterministic regex keyword matching covering 14 domain-specific categories.
- **Multi-Label Capability:** A single review can belong to multiple categories (e.g. late pickup + driver behavior).
- **Extracted Fields for Every Review:**
  - `primary_category`: Dominant category based on match frequency.
  - `secondary_categories`: Additional matching categories.
  - `sentiment`: Positive (4-5★), Neutral (3★), Negative (1-2★).
  - `problem_type`: Software Defect, Operational/Service Issue, Feature Request, Praise, Unclear.
  - `severity`: Critical, High, Medium, Low, Informational.
  - `confidence`: Confidence score (0.50 to 0.95).
  - `classification_method`: "Deterministic Keyword Rules (Regex)".

### Resolving "Other or Unclear" High Volume:
- By expanding regex rules to cover common app crash terms ("stopped working", "wont open"), device-specific complaints ("pixel 8", "oneplus 12"), and general dissatisfaction terms, "Other or Unclear" reviews were reduced from 98 to only genuine unspecific feedback (17.1% of negative reviews).

---

## 3. Technology Stack & Tools Used

| Tool / Library | Role & Purpose in Project |
| :--- | :--- |
| **Python 3.11** | Core programming language for automation, analysis, and dashboard. |
| **`google-play-scraper`** | Fetching public Google Play Store review streams with pagination. |
| **`pandas`** | Data manipulation, aggregation, validation, and multi-label indexing. |
| **`openpyxl`** | Formatting and exporting the 7-sheet Excel workbook (`moveinsync_reviews_analysis.xlsx`). |
| **`streamlit`** | Serving the interactive visual dashboard (`app.py`) on `http://localhost:8501`. |
| **`plotly`** | Rendering interactive bar charts, pie charts, and rating trend line charts. |
| **`sqlite3` (`database.py`)** | Local persistent storage (`moveinsync_reviews.db`) for snapshot comparison and periodic review monitoring. |

---

## 4. Key Assumptions & Audit Limitations

1. **Public Review Bias:** Play Store reviews skew towards users experiencing extreme satisfaction (5★) or extreme operational friction (1★). Neutral commutes are rarely reviewed.
2. **Lack of Internal Context:** Public reviews do not include internal company corporate policy restrictions, cab vendor SLAs, or specific city traffic incident logs.
3. **Hypotheses vs. Verified Facts:**
   - **VERIFIED:** 1-star review concentration (26%), app crash volume (28.4%), pickup delay volume (21.2%), rating distribution, small sample trend artifact in June 2026.
   - **HYPOTHESIS:** Server APM lock contention during morning shift changeovers; driver mobile app OS background location throttling. (Requires internal telemetry logs to confirm).

---

## 5. Periodic Rerun Instructions

To answer *"How are our Play Store ratings?"* periodically:
```powershell
py main.py --limit 1000 --country in --lang en
```
This updates the SQLite database snapshot, regenerates the 7-sheet Excel file, updates the markdown report, and updates the live Streamlit dashboard.
