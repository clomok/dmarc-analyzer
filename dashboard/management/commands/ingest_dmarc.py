import parsedmarc
from django.core.management.base import BaseCommand
from django.conf import settings
from dashboard.models import DomainEntity, DmarcReport, Organization
from django.utils.timezone import make_aware
from datetime import datetime
import logging

# Import the connection class and the high-level processor
from parsedmarc.mail import IMAPConnection
from parsedmarc import get_dmarc_reports_from_mailbox

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches DMARC reports from IMAP and saves to DB'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=10, help='Number of emails to process')

    def handle(self, *args, **options):
        limit = options['limit']
        self.stdout.write(f"Connecting to IMAP (Batch Size: {limit})...")
        
        try:
            # 1. Initialize the Connection
            # We establish the link to the server first
            connection = IMAPConnection(
                host=settings.EMAIL_HOST_IMAP,
                user=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD
            )
            
            # 2. Fetch & Parse Reports
            # We pass the connection object, NOT the credentials, to this function.
            # This function handles downloading, unzip, XML parsing, and batching.
            self.stdout.write("Fetching and parsing reports...")
            
            results = get_dmarc_reports_from_mailbox(
                connection=connection,
                reports_folder="INBOX",
                archive_folder="Archive",
                delete=False,
                batch_size=limit,
                test=False
            )
            
            # The results object contains keys for 'aggregate_reports' and 'forensic_reports'
            aggregate_reports = results.get("aggregate_reports", [])
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ingest Error: {e}"))
            return

        self.stdout.write(f"Successfully parsed {len(aggregate_reports)} reports.")

        # 3. Process Aggregate (RUA) Reports into Database
        count_created = 0
        
        for report in aggregate_reports:
            # Extract header info
            metadata = report["report_metadata"]
            policy_pub = report["policy_published"]
            domain_name = policy_pub["domain"]
            
            # Find or Create the Domain Entity
            # We assign it to a default Organization if it's new
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
                # Use .get() safely for top-level keys to prevent KeyErrors
                source = record.get("source", {})
                alignment = record.get("alignment", {})
                auth_results = record.get("auth_results", {})
                identifiers = record.get("identifiers", {})
                
                # Fix 1: Handle flat vs nested structure for count/policy
                if "row" in record and isinstance(record["row"], dict):
                    # Some parsers nest these deeply
                    count = int(record["row"].get("count", 0))
                    policy_eval = record["row"].get("policy_evaluated", {})
                else:
                    # Others flatten them
                    count = int(record.get("count", 0))
                    policy_eval = record.get("policy_evaluated", {})

                # Fix 2: Robust Date Handling
                try:
                    # Check for nested date_range dictionary
                    if "date_range" in metadata:
                        begin_ts = float(metadata["date_range"]["begin"])
                        end_ts = float(metadata["date_range"]["end"])
                    # Fallback to flat keys if present
                    elif "begin_date" in metadata and "end_date" in metadata:
                         begin_raw = metadata["begin_date"]
                         end_raw = metadata["end_date"]
                         
                         # If it's already a datetime object (some parsers do this)
                         if isinstance(begin_raw, datetime):
                             date_begin = make_aware(begin_raw)
                             date_end = make_aware(end_raw)
                             # Skip the timestamp conversion logic
                             raise StopIteration 

                         begin_ts = float(begin_raw)
                         end_ts = float(end_raw)
                    else:
                        # Last ditch effort: look for 'begin' key in metadata
                        begin_ts = float(metadata.get("begin", 0))
                        end_ts = float(metadata.get("end", 0))

                    date_begin = make_aware(datetime.fromtimestamp(begin_ts))
                    date_end = make_aware(datetime.fromtimestamp(end_ts))
                
                except StopIteration:
                    pass # Dates were already handled
                except (ValueError, TypeError):
                    # Fallback for malformed dates
                    date_begin = make_aware(datetime.now())
                    date_end = make_aware(datetime.now())

                # Extract DKIM domains safely
                dkim_domains = [
                    d["domain"] for d in auth_results.get("dkim", []) if "domain" in d
                ]

                # Create the Report Entry
                DmarcReport.objects.create(
                    domain_entity=entity,
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
        
        self.stdout.write(self.style.SUCCESS(f"Done! Created {count_created} report rows."))