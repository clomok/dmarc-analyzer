from django.db import models

class Organization(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name

class DomainEntity(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    domain_name = models.CharField(max_length=255, unique=True, help_text="The domain being reported on (e.g. google.com)")
    
    # Config
    is_active = models.BooleanField(default=True)
    notify_email = models.EmailField(null=True, blank=True)
    
    def __str__(self):
        return self.domain_name

class DmarcReport(models.Model):
    """
    TimescaleDB Hypertable.
    We use a standard Django ID, but we will alter the Primary Key 
    in the migration to be composite (id + date_begin) to satisfy TimescaleDB.
    """
    domain_entity = models.ForeignKey(DomainEntity, on_delete=models.CASCADE)
    
    # --- NEW FIELD FOR DEDUPLICATION ---
    report_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    # The Partitioning Column
    date_begin = models.DateTimeField()
    date_end = models.DateTimeField()
    
    # Source Info
    source_ip = models.GenericIPAddressField()
    source_hostname = models.TextField(null=True, blank=True)
    source_base_domain = models.TextField(null=True, blank=True)
    country_code = models.TextField(null=True, blank=True)
    
    # Metrics
    count = models.IntegerField()
    
    # Policy & Alignment
    disposition = models.TextField() # none, quarantine, reject
    dkim_aligned = models.BooleanField()
    spf_aligned = models.BooleanField()
    
    # Details
    header_from = models.TextField()
    envelope_from = models.TextField(null=True)
    dkim_domains = models.JSONField(default=list) 
    auth_results = models.JSONField() 

    class Meta:
        indexes = [
            models.Index(fields=['date_begin', 'domain_entity']),
        ]

class ForensicSample(models.Model):
    domain_entity = models.ForeignKey(DomainEntity, on_delete=models.CASCADE)
    arrival_date = models.DateTimeField()
    subject = models.TextField(null=True)
    source_ip = models.GenericIPAddressField(null=True)
    feedback_report = models.JSONField()