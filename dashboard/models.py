from django.db import models
import json

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

    @property
    def inspection_data(self):
        """
        Parses auth_results to provide UI-ready technical and layman explanations.
        """
        data = {
            "threat": False,
            "threat_color": "gray",
            "spf_tag": {"label": "SPF", "status": "Unknown", "color": "gray", "detail": ""},
            "dkim_tag": {"label": "DKIM", "status": "Unknown", "color": "gray", "detail": ""},
            "layman_summary": ""
        }

        # 1. Determine Threat Level
        if not self.spf_aligned and not self.dkim_aligned:
            data["threat"] = True
            data["threat_color"] = "red"
        elif not self.spf_aligned or not self.dkim_aligned:
            data["threat_color"] = "yellow"
        else:
            data["threat_color"] = "green"

        # 2. Extract SPF Details
        # auth_results structure often: {'spf': [{'domain': '...', 'result': 'pass', ...}]}
        spf_info = self.auth_results.get('spf', [])
        if spf_info and isinstance(spf_info, list) and len(spf_info) > 0:
            res = spf_info[0].get('result', 'unknown')
            domain = spf_info[0].get('domain', 'unknown')
            data["spf_tag"]["status"] = res.upper()
            data["spf_tag"]["detail"] = f"Domain: {domain}"
            
            if res == 'pass':
                data["spf_tag"]["color"] = "green"
            elif res in ['softfail', 'neutral']:
                data["spf_tag"]["color"] = "yellow"
            else:
                data["spf_tag"]["color"] = "red"
        else:
            data["spf_tag"]["status"] = "MISSING"
            data["spf_tag"]["color"] = "red"

        # 3. Extract DKIM Details
        dkim_info = self.auth_results.get('dkim', [])
        if dkim_info and isinstance(dkim_info, list) and len(dkim_info) > 0:
            # Often multiple signatures, grab the first or relevant one
            res = dkim_info[0].get('result', 'unknown')
            selector = dkim_info[0].get('selector', '-')
            data["dkim_tag"]["status"] = res.upper()
            data["dkim_tag"]["detail"] = f"Selector: {selector}"
            
            if res == 'pass':
                data["dkim_tag"]["color"] = "green"
            else:
                data["dkim_tag"]["color"] = "red"
        else:
            data["dkim_tag"]["status"] = "MISSING"
            data["dkim_tag"]["color"] = "gray"

        # 4. Generate Layman Summary
        if data["threat"]:
            data["layman_summary"] = (
                "🚨 **High Risk:** This email failed both sender checks (SPF) and digital signature checks (DKIM). "
                "The server sending this email is NOT authorized by your domain, and the email content may have been tampered with. "
                "This is a strong indicator of spoofing."
            )
        elif not self.spf_aligned:
            data["layman_summary"] = (
                "⚠️ **SPF Misalignment:** The email was sent from an IP address that is not listed in your domain's SPF record. "
                "However, it had a valid digital signature (DKIM), so it might be a legitimate forwarding service or a third-party tool you use."
            )
        elif not self.dkim_aligned:
            data["layman_summary"] = (
                "⚠️ **DKIM Failure:** The email did not have a valid digital signature for your domain. "
                "However, it came from an authorized IP address (SPF Pass), so it is likely a configuration error on your mail server."
            )
        else:
            data["layman_summary"] = (
                "✅ **Legitimate:** This email passed all checks. It came from an authorized IP and had a valid digital signature."
            )

        return data

class ForensicSample(models.Model):
    domain_entity = models.ForeignKey(DomainEntity, on_delete=models.CASCADE)
    arrival_date = models.DateTimeField()
    subject = models.TextField(null=True)
    source_ip = models.GenericIPAddressField(null=True)
    feedback_report = models.JSONField()