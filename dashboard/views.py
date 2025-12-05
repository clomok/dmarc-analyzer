from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Q, Count
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
import json

from .models import DmarcReport, DomainEntity

def dashboard(request):
    # 1. Date Filter Logic
    period = request.GET.get('period', '30d')
    granularity = request.GET.get('granularity', 'day')
    
    days_map = {'7d': 7, '30d': 30, '90d': 90}
    days = days_map.get(period, 30)
    
    date_end = timezone.now()
    date_begin = date_end - timedelta(days=days)

    # 2. Base Query
    reports = DmarcReport.objects.filter(date_begin__gte=date_begin, date_begin__lte=date_end)

    # 3. High Level Stats (Cards)
    global_stats = reports.aggregate(
        total_volume=Sum('count'),
        dkim_aligned_count=Sum('count', filter=Q(dkim_aligned=True)),
        spf_aligned_count=Sum('count', filter=Q(spf_aligned=True)),
        dmarc_pass_count=Sum('count', filter=Q(spf_aligned=True) | Q(dkim_aligned=True))
    )
    
    # --- New Threat Calculation ---
    # Count distinct Source IPs that failed BOTH SPF and DKIM
    threat_ips = reports.filter(
        spf_aligned=False, 
        dkim_aligned=False
    ).values('source_ip').distinct().count()

    total_volume = global_stats['total_volume'] or 0
    dmarc_pass = global_stats['dmarc_pass_count'] or 0
    pass_percentage = round((dmarc_pass / total_volume) * 100, 1) if total_volume > 0 else 0

    # 4. Domain Table Stats
    domain_stats = reports.values(
        'domain_entity__id',
        'domain_entity__domain_name'
    ).annotate(
        total=Sum('count'),
        dmarc_pass_count=Sum('count', filter=Q(spf_aligned=True) | Q(dkim_aligned=True)),
        spf_pass_count=Sum('count', filter=Q(spf_aligned=True)),
        dkim_pass_count=Sum('count', filter=Q(dkim_aligned=True))
    ).order_by('-total')

    # --- 5. Chart Logic (Multi-Line by Domain) ---
    
    # Determine Trunc function
    trunc_func = TruncDay
    if granularity == 'week':
        trunc_func = TruncWeek
    elif granularity == 'month':
        trunc_func = TruncMonth

    # A. Get Top 10 Domains (to avoid overcrowding the chart)
    top_domains = list(domain_stats[:10].values_list('domain_entity__domain_name', flat=True))

    # B. Aggregate data
    chart_data_qs = reports.filter(
        domain_entity__domain_name__in=top_domains
    ).annotate(
        date_group=trunc_func('date_begin')
    ).values(
        'date_group', 'domain_entity__domain_name'
    ).annotate(
        volume=Sum('count')
    ).order_by('date_group')

    # C. Pivot Data
    # Convert dates to string immediately
    unique_dates = sorted(list(set(item['date_group'].strftime('%Y-%m-%d') for item in chart_data_qs)))
    
    series_data = []
    for domain in top_domains:
        domain_volumes = []
        for date in unique_dates:
            # Find matching record
            record = next(
                (x for x in chart_data_qs if x['date_group'].strftime('%Y-%m-%d') == date and x['domain_entity__domain_name'] == domain), 
                None
            )
            vol = int(record['volume']) if record else 0
            domain_volumes.append(vol)
            
        series_data.append({
            'name': domain,
            'type': 'line',
            'smooth': True,
            'data': domain_volumes
        })

    context = {
        'period': period,
        'granularity': granularity,
        'global_stats': global_stats,
        'threat_ips': threat_ips, # <--- Added to context
        'pass_percentage': pass_percentage,
        'domain_stats': domain_stats,
        # JSON Dumps ensures correct JS syntax
        'chart_dates': json.dumps(unique_dates),
        'chart_series': json.dumps(series_data),
    }

    return render(request, 'dashboard/dashboard.html', context)

def domain_detail(request, domain_id):
    domain = get_object_or_404(DomainEntity, pk=domain_id)
    
    period = request.GET.get('period', '30d')
    days_map = {'7d': 7, '30d': 30, '90d': 90}
    days = days_map.get(period, 30)
    
    date_end = timezone.now()
    date_begin = date_end - timedelta(days=days)
    
    reports = DmarcReport.objects.filter(
        domain_entity=domain,
        date_begin__gte=date_begin, 
        date_begin__lte=date_end
    ).order_by('-date_begin')
    
    context = {
        'domain': domain,
        'reports': reports,
        'period': period
    }
    return render(request, 'dashboard/domain_detail.html', context)