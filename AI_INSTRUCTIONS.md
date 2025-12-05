# AI_INSTRUCTIONS.md

# Project: Self-Hosted DMARC Analyzer

## 1\. Context & Architecture

Goal: A personal, self-hosted tool to receive, parse, store, and visualize DMARC reports from multiple domains.

Deployment: Single-user (Admin), Multi-tenant data structure (Grouped by Domain/Organization).

Infrastructure: Docker Compose (Local Homelab).

### The Stack

- **Backend:** Django 5.x (Python 3.11)
- **Database:** PostgreSQL 14 + **TimescaleDB** (for time-series report data)
- **Ingress:** Custom Django Management Command using `parsedmarc` library (IMAP fetch).
- **Frontend:** Django Templates + **HTMX** + **Tailwind CSS** (CDN) + **Apache ECharts**.
- **Authentication:** `django-allauth` (Installed but not yet fully configured for UI).

## 2\. Current Status (As of Last Session)

- **Infrastructure:**
  - Docker Compose handles `web` and `db` services.
  - Environment variables moved to `.env` file (gitignored).
  - `docker-compose.yaml` uses `DATABASE_URL` injection.
  - `settings.py` uses `dj-database-url` to parse db connections.
- **Database:**
  - `DmarcReport` table is a **TimescaleDB Hypertable**.
  - **Schema Update:** Added `report_id` field to `DmarcReport` model to support deduplication.
- **Ingress (**`ingest_dmarc.py`**):**
  - Connects to IMAP via `parsedmarc`.
  - **Deduplication:** Now checks `report_id` against the DB before inserting to prevent duplicate rows.
  - Successfully parses XML, handles nested/flat structures, and robust date parsing.
- **Frontend (Implemented):**
  - **Base Template:** Includes Tailwind (Dark Mode default), HTMX, and ECharts.
  - **Dashboard View:**
    - Aggregate Stats Cards (Total, Compliance %, SPF/DKIM Alignment).
    - **Multi-Series Line Chart:** Visualizes volume per domain over time.
    - **Granularity Toggle:** Switch chart between Day/Week/Month.
    - **Domain Table:** Lists domains with summary stats.
  - **Domain Detail View:**
    - Lists individual report rows for a specific domain.
    - Shows Source IP, Country, Count, Disposition, and Alignment status.

## 3\. Operational Commands (PowerShell)

- **Start Dev Server:** `.\manage.ps1 dev`
- **Run Ingest (Fetch Emails):** `.\manage.ps1 ingest`
- **Reset DB (Nuclear):** `.\manage.ps1 reset`
- **Manual Migrations (if models change):**
  ```
  docker-compose exec web python manage.py makemigrations
  docker-compose exec web python manage.py migrate
  ```

## 4\. Database Schema Reference

- **Organization:** Grouping entity.
- **DomainEntity:** Represents a domain (e.g., `google.com`).
- **DmarcReport:**
  - **Type:** Hypertable (partitioned by `date_begin`).
  - **Deduplication Key:** `report_id`.
  - **Key Data:** `source_ip`, `count`, `disposition`, `dkim_aligned`, `spf_aligned`.
  - **JSONB Fields:** `auth_results`, `dkim_domains`.

## 5\. Next Session Goals

1.  **Row Expansion (Drill Down):**
    - In the `Domain Detail` view, make table rows clickable.
    - Reveal hidden JSON data: `auth_results` (why it failed), `envelope_from`, and `dkim_domains`.
2.  **Authentication UI:**
    - Create Login/Logout templates.
    - Protect views with `@login_required`.
3.  **Refinement:**
    - Add "Last Seen" dates to the Domain list.
    - specific highlighting for "Threats" (IPs that fail both SPF and DKIM).

## 6\. Critical Constraints & Rules

- **JSON Serialization:** When passing data to ECharts in templates, ALWAYS use `json.dumps()` in the view and `{{ variable|safe }}` in the template to prevent JavaScript syntax errors.
- **TimescaleDB:** Always ensure migrations respect the Hypertable structure (composite primary keys involving time).
- **Environment:** maintain `.env` file usage for secrets; do not hardcode credentials in `docker-compose.yaml`.
