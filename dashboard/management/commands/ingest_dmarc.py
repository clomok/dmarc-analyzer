import parsedmarc
from django.core.management.base import BaseCommand
from django.conf import settings
from dashboard.models import DomainEntity, DmarcReport, Organization
from django.utils.timezone import make_aware
from django.utils.dateparse import parse_datetime
from datetime import datetime, timezone
import logging

# Import the connection class and the high-level processor
from parsedmarc.mail import IMAPConnection
from parsedmarc import get_dmarc_reports_from_mailbox

logger = logging.getLogger(__name__)

def parse_date(value):
    """
    Robustly parses a date value which might be a float timestamp, 
    a string timestamp, a string datetime, or a datetime object.
    """
    if value is None:
        return None
    
    # 1. If it's already a datetime object
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return make_aware(value)
        return value
    
    # 2. Try parsing as a timestamp (float/int/string)
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (ValueError, TypeError):
        pass

    # 3. Try parsing as a standard datetime string (ISO or SQL-like)
    if isinstance(value, str):
        # Django's helper handles 'YYYY-MM-DD HH:MM:SS' and ISO formats
        dt = parse_datetime(value)
        if dt is not None:
            if dt.tzinfo is None:
                return make_aware(dt)
            return dt
            
    return None

class Command(BaseCommand):
    help = 'Fetches DMARC reports from IMAP and saves to DB'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10, help='Number of emails to process')

    def handle(self, *args, **options):
        limit = options['limit']
        self.stdout.write(f"Connecting to IMAP (Batch Size: {limit})...")
        
        try:
            # 1. Initialize the Connection
            connection = IMAPConnection(
                host=settings.EMAIL_HOST_IMAP,
                user=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD
            )
            
            # 2. Fetch & Parse Reports
            self.stdout.write("Fetching and parsing reports...")
            
            results = get_dmarc_reports_from_mailbox(
                connection=connection,
                reports_folder="INBOX",
                archive_folder="Archive",
                delete=False,
                batch_size=limit,
                test=False
            )
            
            aggregate_reports = results.get("aggregate_reports", [])
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ingest Error: {e}"))
            return

        self.stdout.write(f"Successfully parsed {len(aggregate_reports)} reports.")

        # 3. Process Aggregate (RUA) Reports into Database
        count_created = 0
        count_skipped = 0
        
        for report in aggregate_reports:
            # Extract header info
            metadata = report["report_metadata"]
            policy_pub = report["policy_published"]
            domain_name = policy_pub["domain"]
            
            # --- DEDUPLICATION CHECK ---
            report_id = metadata.get("report_id")
            if report_id and DmarcReport.objects.filter(report_id=report_id).exists():
                self.stdout.write(f"Skipping duplicate report: {report_id}")
                count_skipped += 1
                continue

            # Find or Create the Domain Entity
            default_org, _ = Organization.objects.get_or_create(
                name="Unassigned", 
                defaults={"slug": "unassigned"}
            )
            
            entity, created = DomainEntity.objects.get_or_create(
                domain_name=domain_name,
                defaults={"organization": default_org}
            )

            # Process every record (row) in the XML
            for record in report["records"]:
                source = record.get("source", {})
                alignment = record.get("alignment", {})
                auth_results = record.get("auth_results", {})
                identifiers = record.get("identifiers", {})
                
                # Handle flat vs nested structure
                if "row" in record and isinstance(record["row"], dict):
                    count = int(record["row"].get("count", 0))
                    policy_eval = record["row"].get("policy_evaluated", {})
                else:
                    count = int(record.get("count", 0))
                    policy_eval = record.get("policy_evaluated", {})

                # --- UPDATED DATE HANDLING ---
                # Attempt to find dates in priority order
                date_begin = None
                date_end = None
                
                # 1. Try standard 'date_range' (Most common)
                if "date_range" in metadata:
                    date_begin = parse_date(metadata["date_range"].get("begin"))
                    date_end = parse_date(metadata["date_range"].get("end"))
                
                # 2. Try 'begin_date' / 'end_date' keys
                if not date_begin and "begin_date" in metadata:
                    date_begin = parse_date(metadata.get("begin_date"))
                if not date_end and "end_date" in metadata:
                    date_end = parse_date(metadata.get("end_date"))

                # 3. Try flat 'begin' / 'end' keys
                if not date_begin:
                    date_begin = parse_date(metadata.get("begin"))
                if not date_end:
                    date_end = parse_date(metadata.get("end"))

                # 4. Fallback: If all parsing failed, use Now
                if not date_begin:
                    self.stdout.write(self.style.WARNING(f"Could not parse date for report {report_id}. Using NOW."))
                    date_begin = datetime.now(timezone.utc)
                if not date_end:
                    date_end = datetime.now(timezone.utc)
                # -----------------------------

                # Extract DKIM domains
                dkim_domains = [
                    d["domain"] for d in auth_results.get("dkim", []) if "domain" in d
                ]

                # Create the Report Entry
                DmarcReport.objects.create(
                    domain_entity=entity,
                    report_id=report_id,
                    date_begin=date_begin,
                    date_end=date_end,
                    source_ip=source.get("ip_address", "0.0.0.0"),
                    source_hostname=source.get("reverse_dns"),
                    source_base_domain=source.get("base_domain"),
                    country_code=source.get("country"),
                    count=count,
                    disposition=policy_eval.get("disposition", "none"),
                    dkim_aligned=alignment.get("dkim", False),
                    spf_aligned=alignment.get("spf", False),
                    header_from=policy_pub.get("domain", ""),
                    envelope_from=identifiers.get("envelope_from"),
                    dkim_domains=dkim_domains,
                    auth_results=auth_results 
                )
                count_created += 1
        
        self.stdout.write(self.style.SUCCESS(f"Done! Created {count_created} rows. Skipped {count_skipped} duplicate reports."))