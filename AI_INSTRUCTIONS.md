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
  - **Security:** - Secrets (`SECRET_KEY`, `DB_PASSWORD`, `EMAIL_PASSWORD`) are now loaded from `.env`.
    - `DEBUG` mode is toggleable via `.env`.
    - `ALLOWED_HOSTS` is configurable via `.env` (supports Reverse Proxy).
- **Database:**
  - `DmarcReport`: TimescaleDB Hypertable.
  - **Fields:** Added `report_id` (deduplication) and `is_acknowledged` (boolean for manual workflow).
- **Ingress:**
  - **Logic:** Robust date parsing added to handle both Timestamp (float) and String (ISO) date formats from various DMARC reporters.
  - **Manual Trigger:** "Check for Updates" button on Dashboard triggers `ingest_dmarc` via HTMX.
- **Frontend (UI/UX):**
  - **Visuals:** Added **Country Flags** (via `flagcdn.com`) next to Source IPs.
  - **Formatting:** Dates updated to **12-hour format**.
  - **Active Threats:** Dedicated view (`/threats/`) for unacknowledged failures.

## 3. Operational Commands (PowerShell)

- **Start Dev Server:** `.\manage.ps1 dev`
- **Run Ingest (Manual):** `.\manage.ps1 ingest` (Or use the GUI button)
- **Reset DB:** `.\manage.ps1 reset`

## 4. Development Philosophy (CRITICAL)

1.  **Simplicity First:** Always prioritize the simplest, most durable solution.
2.  **Consent for Complexity:** Explain WHY before adding complex logic.
3.  **Visual Clarity:** UI should cleanly separate "Technical Details" from "Layman Summaries".

## 5. Next Steps / Roadmap

1.  **Migration to Production:** - Deploy to `prod-dock1`.
    - Configure `.env` with secure secrets.
2.  **Data Management:**
    - **Historic Upload:** Add a feature to manually upload past DMARC XML/ZIP files.
3.  **Refinement:**
    - Polish mobile view for tables.

## 6. Constraints & Rules

- **Windows Compatibility:** Do NOT use Emoji flags (🇺🇸). Use `flagcdn.com`.
- **JSON Serialization:** Use `json.dumps()` in views.
- **HTMX:** Always ensure `hx-headers` include the CSRF token.
- **Environment:** Keep secrets in `.env`; do not hardcode.
