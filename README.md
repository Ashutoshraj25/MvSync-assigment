# MoveInSync Google Play Reviews Collection & Analysis Tool

A complete, production-grade Python project designed to scrape public Google Play Store reviews for the **MoveInSync (ETS)** application (`com.moveinsync.ets`), perform NLP rule-based multi-label review classification, analyze rating trends and complaint drivers, and export structured outputs into a 4-sheet formatted Excel workbook (`moveinsync_reviews_analysis.xlsx`), an evidence-based markdown analysis report (`MoveInSync_Review_Analysis_Report.md`), and an interactive Streamlit analytics dashboard.

Built as part of the **Forward Deployed Engineer (FDE)** candidate assignment.

---

## 🌟 Key Features

1. **Robust Public Review Scraper (`scraper.py`)**
   - Continuously fetches reviews using pagination / continuation tokens.
   - User-selectable review limits: 500, 1,000, 2,000, or maximum available.
   - Configurable language (`en`) and country (`in`, `us`, etc.) settings.
   - Dual sorting options (`newest` and `most_relevant`).
   - Deduplication using unique `reviewId` hashes.
   - Exponential backoff retry logic for handling network timeouts and rate limits.
   - Real-time progress updates and comprehensive metadata logging.

2. **Multi-Label Category & Problem Taxonomy Classification (`analysis.py`)**
   - Rule-based regex keyword classification engine supporting 12+ domain-specific categories:
     - *Login & Authentication*, *Booking & Cancellation*, *Shuttle or Cab Availability*, *Pickup Timing & Delays*, *GPS & Live Tracking*, *App Crashes & Performance*, *User Interface & Usability*, *Notifications & Reminders*, *Driver Behavior & Safety*, *Customer Support*, *Attendance & Check-in*, *Positive Feedback*, *Other or Unclear*.
   - Categorizes problems into high-level taxonomies: **Software Bug / App Defect**, **Operational / Service Issue**, **Feature Request**, **Positive / Praise**, or **Unclear**.

3. **Formatted 4-Sheet Excel Export (`exporter.py`)**
   Generates `moveinsync_reviews_analysis.xlsx` featuring executive styling (`openpyxl` dark blue headers, frozen panes, auto-fit columns, filters, and cell formatting):
   - **Sheet 1: All Reviews** — Full raw dataset with classification binary flags and problem types.
   - **Sheet 2: Rating Summary** — Star rating distribution breakdown, total counts, percentages, and sample average.
   - **Sheet 3: Complaint Analysis** — Frequency breakdown of negative feedback, operational impact descriptions, and representative review ID excerpts.
   - **Sheet 4: Data Quality** — Scraping metadata, timestamps, date range, limit audit, and error logs.

4. **Evidence-Based Analysis & Roadmap Report (`report_generator.py`)**
   - Generates `MoveInSync_Review_Analysis_Report.md` containing observed evidence, rating breakdown, recent vs. older trend comparisons, app version performance, qualitative user quotes, root cause hypotheses, and a **Prioritized Product Improvement Roadmap** mapped to employee commute journey stages with Mermaid diagrams.

5. **Interactive Streamlit Dashboard (`app.py`)**
   - Interactive UI with sidebar controls, live scraping progress bar, KPI metric cards, Plotly charts, category deep-dive filters, interactive search tables, and 1-click Excel/Markdown download buttons.

---

## 📁 Project Structure

```text
d:\Mvsync assigment\
│
├── app.py                      # Streamlit web dashboard entry point
├── main.py                     # CLI script for headless batch execution
├── scraper.py                  # Google Play review scraper & deduplication engine
├── analysis.py                 # Multi-label classification & summary analytics
├── exporter.py                 # openpyxl Excel exporter (4 sheets)
├── report_generator.py         # Markdown analysis report & roadmap generator
├── requirements.txt            # Python dependencies specification
├── README.md                   # Complete documentation & setup instructions
├── moveinsync_reviews_analysis.xlsx   # Output Excel workbook
└── MoveInSync_Review_Analysis_Report.md # Output Markdown analysis report
```

---

## 🛠️ Windows Installation & Setup Guide

### Step 1: Verify Python Installation
Open PowerShell or Command Prompt and verify Python 3.9+ is installed:
```powershell
py --version
```

### Step 2: Install Required Dependencies
Navigate to the project root directory and install dependencies via `pip`:
```powershell
py -m pip install -r requirements.txt
```

*Required dependencies include: `google-play-scraper`, `pandas`, `openpyxl`, `streamlit`, and `plotly`.*

---

## 🚀 How to Run the Tool

### Option A: Headless CLI Execution (No Browser Needed)
To run the automated collection, classification, Excel export, and report generation directly from the command line:

```powershell
py main.py --limit 1000 --country in --lang en --sort newest
```

**CLI Flags & Arguments:**
- `--package`: Target app package ID (default: `com.moveinsync.ets`)
- `--limit`: Maximum reviews to fetch (e.g. `500`, `1000`, `2000`, or `0` for all available)
- `--country`: Country code (e.g. `in`, `us`, `gb`)
- `--lang`: Language code (default: `en`)
- `--sort`: Sort order (`newest` or `most_relevant`)
- `--excel`: Custom path for Excel workbook output (default: `moveinsync_reviews_analysis.xlsx`)
- `--report`: Custom path for Markdown report output (default: `MoveInSync_Review_Analysis_Report.md`)

---

### Option B: Interactive Streamlit Dashboard
To launch the interactive visual dashboard in your browser:

```powershell
py -m streamlit run app.py
```

Once executed, Streamlit will open automatically in your browser at `http://localhost:8501`.

**Dashboard Features:**
- Adjust parameters (Package ID, Country, Language, Review Limit) dynamically.
- Click **"Collect & Analyze Reviews"** to trigger live extraction.
- View rating distribution bar charts and complaint breakdown heatmaps.
- Search and filter reviews by keyword, star rating, or complaint category.
- Download the generated `.xlsx` and `.md` reports directly.

---

## 🔄 Periodical Rerun & Maintenance Instructions

To monitor app performance and track complaint reduction over time:

1. **Automated Scheduled Scraping (Windows Task Scheduler):**
   Set up a recurring weekly task in Windows Task Scheduler running:
   `py.exe "D:\Mvsync assigment\main.py" --limit 1000 --excel "moveinsync_reviews_analysis.xlsx"`

2. **Tracking Rating Trends:**
   Compare the `Average Rating` metric and `Share of Negative Reviews (%)` across monthly Excel exports.

---

## 🔒 Security & Data Integrity
- No hardcoded API keys or personal credentials are required.
- Review collection relies strictly on public Play Store data.
- Deduplication prevents double-counting of reviews.
