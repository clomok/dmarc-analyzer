# Project: Self-Hosted DMARC Analyzer

## 1\. Context & Architecture

**Goal:** A personal, self-hosted tool to receive, parse, store, and visualize DMARC reports from multiple domains. **Deployment:** Single-user (Admin), Multi-tenant data structure (Grouped by Domain/Organization). **Infrastructure:** Docker Compose (Local Homelab).

### The Stack

- **Backend:** Django 5.x (Python 3.11)
- **Database:** PostgreSQL 14 + **TimescaleDB** (for time-series report data)
- **Ingress:** Custom Django Management Command using `parsedmarc` library (IMAP fetch).
- **Frontend (Decision Made):** Django Templates + **HTMX** + **Tailwind CSS** (via CDN). _No React/Node build pipeline._
- **Authentication:** `django-allauth` (Local DB auth for now, OIDC/Authentik planned for later).

## 2\. Current Status (As of Last Session)

- **Infrastructure:** Docker containers (`web` and `db`) are healthy. `manage.ps1` script created for orchestration.
- **Database:** \* Schema applied.
  - `DmarcReport` table converted to a **TimescaleDB Hypertable**.
  - Composite Primary Key `(id, date_begin)` applied to satisfy Timescale constraints.
- **Ingress:** \* `ingest_dmarc.py` script is **COMPLETE and TESTED**.
  - Successfully ingested 13 test records from the live mailbox.
  - Logic handles `parsedmarc` v9.x API changes (using `IMAPConnection` class directly).
  - Logic handles flat vs. nested XML structures for `count` and `policy_evaluated`.
- **Frontend:** Not started. Currently standard Django 404 page.

## 3\. Operational Commands (PowerShell)

- **Start Dev Server:** `.\manage.ps1 dev`
- **Run Ingest (Fetch Emails):** `.\manage.ps1 ingest`
- **Reset DB (Nuclear):** `.\manage.ps1 reset`

## 4\. Database Schema Reference

- **Organization:** Grouping entity for domains.
- **DomainEntity:** Represents a domain (e.g., `google.com`). Settings for notification thresholds.
- **DmarcReport:** The heavy lifter.
  - **Type:** Hypertable (partitioned by `date_begin`).
  - **Key Data:** `source_ip`, `count`, `disposition`, `dkim_aligned`, `spf_aligned`.
  - **JSONB Fields:** `auth_results`, `dkim_domains` (stores complex auth details).

## 5\. Next Session Goals (Immediate Actions)

We are moving from **Backend** to **Display**.

1.  **Base Template:** Create `base.html` with:
    - Tailwind CSS (CDN).
    - HTMX (CDN).
    - Dark Mode styles by default.
2.  **Dashboard View (**`views.py`**):**
    - Query `DmarcReport` to get aggregate stats (Pass vs. Fail counts).
    - Group data by `DomainEntity`.
3.  **Visualizations:**
    - Integrate a lightweight charting library (e.g., Apache ECharts or ApexCharts) via `<script>` tag.
    - Visualize the "Alignment" (SPF vs DKIM vs From Header).
4.  **Drill Down:** Create a detail view for inspecting individual report rows.

## 6\. Critical Constraints & Rules

- **DO NOT** suggest converting to React/Next.js. We are committed to the Django/HTMX path.
- **DO NOT** use `parsedmarc.get_dmarc_reports_from_inbox` (it is deprecated/removed). Use the `ingest_dmarc.py` pattern we established.
- **Always** check for Windows Line Ending (CRLF) issues when generating shell scripts or requirements files.
