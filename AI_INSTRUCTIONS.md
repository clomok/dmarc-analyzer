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
- **Authentication:** Postponed (Will rely on external Authentik proxy eventually).

## 2. Current Status

- **Infrastructure:**
  - `docker-compose.yaml` handles `web` and `db`.
  - **Security Fix:** CSRF tokens are now injected into `base.html` (`hx-headers`) to allow HTMX POST requests.
- **Database:**
  - `DmarcReport`: TimescaleDB Hypertable.
  - **Fields:** Added `report_id` (deduplication) and `is_acknowledged` (boolean for manual workflow).
  - **Logic:** `DmarcReport` model includes an `inspection_data` property that generates "Layman Summaries" and standardized "Threat Levels" (Red/Yellow/Green) on the fly.
- **Ingress:**
  - Deduplication logic active (checks `report_id`).
  - **Manual Trigger:** "Check for Updates" button on Dashboard triggers `ingest_dmarc` via HTMX.
- **Frontend (Dashboard):**
  - **Stats Cards:** Added "Active Threats" card (Counts unacknowledged IPs failing SPF & DKIM).
  - **Charts:** Multi-series line chart for domain volume.
- **Frontend (Domain Detail):**
  - **Visuals:** Rows failing both SPF & DKIM are highlighted Red.
  - **Interaction:** **Accordion Style** expansion for rows.
  - **Drill Down:** Clicking a row reveals:
    - **Analysis:** Human-readable summary of _why_ it failed.
    - **Tags:** Technical breakdown of SPF/DKIM results.
    - **Raw Data:** Hidden JSON fields (`auth_results`, `envelope_from`) for debugging.
  - **Workflow:** "Mark as Reviewed" checkbox (HTMX) allows users to dismiss threats from the main dashboard counter.

## 3. Operational Commands (PowerShell)

- **Start Dev Server:** `.\manage.ps1 dev`
- **Run Ingest (Manual):** `.\manage.ps1 ingest` (Or use the GUI button)
- **Reset DB:** `.\manage.ps1 reset`
- **Migrations:**
  ```powershell
  docker-compose exec web python manage.py makemigrations
  docker-compose exec web python manage.py migrate
  ```

## 4\. Development Philosophy (CRITICAL)

1.  **Simplicity First:** Always prioritize the simplest, most durable solution (e.g., standard Checkbox vs. dynamic state-swapping buttons).
2.  **Consent for Complexity:** If a feature requires complex logic (e.g., websockets, celery tasks, heavy JS), **explain WHY** it is needed and get approval before generating code.
3.  **Visual Clarity:** UI should cleanly separate "Technical Details" (for debugging) from "Layman Summaries" (for quick decision making).

## 5\. Next Steps / Roadmap

1.  **Refinement:**
    - Add "Last Seen" dates to the main Domain list.
    - Polish mobile view for tables.
2.  **Authentication:**
    - _Status: Low Priority / On Hold._ (Will likely use basic Django LoginView later).
3.  **Automations (Future):**
    - Filters to auto-ignore known safe IPs.

## 6\. Constraints & Rules

- **JSON Serialization:** Use `json.dumps()` in views and `{{ variable|safe }}` in templates for ECharts.
- **HTMX:** Always ensure `hx-headers` include the CSRF token for POST requests.
- **TimescaleDB:** Migrations must respect the Hypertable structure (composite primary keys).
- **Environment:** Keep secrets in `.env`; do not hardcode in `docker-compose.yaml`.
