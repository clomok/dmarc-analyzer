# AI_INSTRUCTIONS.md

# Project: Self-Hosted DMARC Analyzer (MSP Platform)

## 1. Context & Architecture

**Goal:** A "White-Glove" Managed Service Platform (MSP) for an expert administrator to manage email security for multiple clients (100% managed service).

**Deployment:** Single Super-Admin (You), Multi-tenant data structure (Grouped by Organization -> Domain). Clients do NOT log in.

**Infrastructure:** Docker Compose (Local Homelab -> Prod Server).

### The Stack

- **Backend:** Django 5.x (Python 3.11)
- **Database:** PostgreSQL 14 + **TimescaleDB** (Hypertable for time-series data)
- **Ingress:** Custom Django Management Command using `parsedmarc`.
- **Frontend:** Django Templates + **HTMX** (Interactivity) + **Tailwind CSS**.
- **Reporting:** PDF/HTML generation for client billing justification.

## 2. Current Status

- **Infrastructure:**
  - `docker-compose.yaml` handles `web` and `db`.
  - **Security:** `CSRF_TRUSTED_ORIGINS` and `SECURE_PROXY_SSL_HEADER` configured for Reverse Proxy (SSL) support.
- **Database:**
  - `DmarcReport`: TimescaleDB Hypertable.
  - `DomainEntity`: Linked to `Organization`.
- **Ingress Logic:**
  - Robust date parsing and deduplication (`report_id`).
  - "Active Threats" view implemented.

## 3. Workflow & Operations

**Development Cycle:**

1.  **Develop:** Write code on Windows (Localhost) using `manage.ps1`.
2.  **Push:** Commit changes to GitHub.
3.  **Deploy:** Pull changes on server (`prod-dock1`) and restart container.

**Operational Commands:**

- **Start Dev Server:** `.\manage.ps1 dev`
- **Run Ingest (Manual):** `.\manage.ps1 ingest`
- **Reset DB:** `.\manage.ps1 reset`

## 4. Development Philosophy

1.  **Efficiency for the Expert:** Prioritize global dashboards and "at-a-glance" status over friendly wizards.
2.  **Value Demonstration:** Reporting features must clearly demonstrate "Work Done" (Threats blocked, volume processed) to justify the monthly service fee.
3.  **Simplicity First:** Avoid complex microservices; keep logic within Django/Postgres.

## 5. Roadmap

### Phase 1: MSP Core (The "Sanity" Features)

1.  **Source Classification:**
    - Create a lookup system to map `source_hostname` (e.g., `*google.com`) to Vendor Names ("Google Workspace").
    - Group reporting by Vendor instead of IP.
2.  **Global MSP Dashboard:**
    - A "Super-Admin" view listing ALL domains.
    - Columns: Domain | Policy | Compliance % | SPF Lookup Count | Active Threat Count.
    - Sorting: Worst performing domains first.

### Phase 2: The "Security Analyst" Engine (Intelligence Upgrade)

**Goal:** Automate the distinction between "Real Hackers" and "Friendly Fire" (Misconfigurations/Forwarders).

1.  **Infrastructure Enrichment:**
    - Add `geoip2` to requirements.
    - Download `GeoLite2-ASN.mmdb` to a local `/geoip/` folder.
2.  **Database Expansion:**
    - Update `DmarcReport` model with `source_asn` (int) and `source_org` (char) fields.
3.  **Ingestion Upgrade:**
    - Modify `ingest_dmarc` to resolve IP -> ASN/Org immediately upon creation.
4.  **"Friendly Fire" Logic (The Analyst Engine):**
    - Implement a `threat_analysis` property in the Model.
    - **Logic:**
      - **Green/Safe:** Known Good ASN (History of passing DMARC for this domain).
      - **Blue/Forwarder:** Header From != Envelope From AND Hostname contains "relay/fwd".
      - **Yellow/Unauthorized:** Valid Corporate ASN (Google/Microsoft) but failing SPF.
      - **Red/Threat:** Residential/Dynamic IP or Unknown ASN.
5.  **UI Implementation:**
    - **Badges:** Show Provider Name (e.g., "Google LLC", "Stackmail") next to IPs in reports.
    - **Active Threats Split:** Separate the view into "Urgent Security Threats" (Red) vs "Misconfigurations" (Yellow/Blue).

### Phase 3: Client Value (The "Product")

1.  **Executive Reporting:**
    - Generate a monthly PDF/HTML summary for specific Organizations.
    - Metrics: Total Volume, Auth Rate, Threats Prevented, Geographic Breakdown.
2.  **SPF Monitoring:**
    - **Automated:** Daily background check of all managed domains to count SPF lookups. Alert if >10.
    - **Sales Tool:** A manual input form to scan a prospect's domain and reveal their SPF lookup count.

### Phase 4: Deployment & Refinement

1.  **Historic Upload:** Manual upload of past XML/ZIP files via browser.
2.  **Mobile Polish:** Better table rendering on small screens.

## 6. Constraints & Rules

- **Windows Compatibility:** Do NOT use Emoji flags (🇺🇸). Use `flagcdn.com`.
- **Security:** Use Environment Variables for all secrets.
- **Performance:** Avoid external API calls during page loads; stick to local DB/MMDB lookups.
