# AI_INSTRUCTIONS.md

# Project: Self-Hosted DMARC Analyzer

## 1. Context & Architecture

**Goal:** A personal, self-hosted tool to receive, parse, store, and visualize DMARC reports from multiple domains.

**Deployment:** Single-user (Admin), Multi-tenant data structure (Grouped by Domain/Organization).

**Infrastructure:** Docker Compose (Local Homelab).

### The Stack

- **Backend:** Django 5.x (Python 3.11)
- **Database:** PostgreSQL 14 + **TimescaleDB** (Hypertable for time-series data)
- **Ingress:** Custom Django Management Command using `parsedmarc` (IMAP fetch).
- **Frontend:** Django Templates + **HTMX** (Interactivity) + **Tailwind CSS** (CDN) + **Apache ECharts**.
- **Authentication:** Relies on Django Superuser + Environment Variables.

## 2. Current Status

- **Infrastructure:**
  - `docker-compose.yaml` handles `web` and `db`.
  - **Timezone:** Configured to `America/Los_Angeles`.
  - **Secrets:** Loaded from `.env`.
- **Database:**
  - `DmarcReport`: TimescaleDB Hypertable.
  - **Fields:** Includes `report_id` (deduplication) and `is_acknowledged` (workflow).
- **Ingress Logic:**
  - **Library:** Reverted to standard `parsedmarc.get_dmarc_reports_from_mailbox` for maximum stability with attachments (ZIP/XML).
  - **Date Parsing:** Highly robust `parse_date` function added to handle Timestamp (float), String (ISO), and Datetime objects indiscriminately.
  - **Ordering:** Ingestion relies on IMAP default order. **Operational Note:** To process newer emails faster, archive older processed emails in the mailbox.
- **Frontend (UI/UX):**
  - **Dashboard:** "View All Reports" link added.
  - **Pagination:** Implemented on the "All Reports" list (50 items per page).
  - **Visuals:** Country Flags, 12-hour date formats, and "Active Threats" view.

## 3. Operational Commands (PowerShell)

- **Start Dev Server:** `.\manage.ps1 dev`
- **Run Ingest (Manual):** `.\manage.ps1 ingest` (Default limit: 10 emails)
  - _Tip:_ Use `--limit 50` to process larger batches if the inbox is backed up.
- **Reset DB:** `.\manage.ps1 reset`

## 4. Development Philosophy (CRITICAL)

1.  **Simplicity First:** Always prioritize the simplest, most durable solution.
2.  **Consent for Complexity:** Explain WHY before adding complex logic.
3.  **Visual Clarity:** UI should cleanly separate "Technical Details" from "Layman Summaries".

## 5. Next Steps / Roadmap

1.  **Deployment:** Deploy current `report_list` and ingestion fixes to Production (`prod-dock1`).
2.  **Data Management:**
    - **Historic Upload:** Add a feature to manually upload past DMARC XML/ZIP files via the browser.
3.  **Refinement:**
    - Polish mobile view for tables.

## 6. Constraints & Rules

- **Windows Compatibility:** Do NOT use Emoji flags (🇺🇸). Use `flagcdn.com`.
- **JSON Serialization:** Use `json.dumps()` in views.
- **HTMX:** Always ensure `hx-headers` include the CSRF token.
- **Environment:** Keep secrets in `.env`; do not hardcode.
