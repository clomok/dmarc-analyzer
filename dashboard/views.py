from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Q, Count, Max
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.core.management import call_command
from django.http import HttpResponse
from django.core.paginator import Paginator #
import io
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
    
    # Threat Calculation
    threat_ips = reports.filter(
        spf_aligned=False, 
        dkim_aligned=False,
        is_acknowledged=False
    ).values('source_ip').distinct().count()

    total_volume = global_stats['total_volume'] or 0
    dmarc_pass = global_stats['dmarc_pass_count'] or 0
    pass_percentage = round((dmarc_pass / total_volume) * 100, 1) if total_volume > 0 else 0

    # 4. Domain Table Stats (Updated with Last Seen & Threat Count)
    domain_stats = reports.values(
        'domain_entity__id',
        'domain_entity__domain_name'
    ).annotate(
        total=Sum('count'),
        dmarc_pass_count=Sum('count', filter=Q(spf_aligned=True) | Q(dkim_aligned=True)),
        spf_pass_count=Sum('count', filter=Q(spf_aligned=True)),
        dkim_pass_count=Sum('count', filter=Q(dkim_aligned=True)),
        # NEW: Count specific threat rows for this domain
        active_threat_count=Count('id', filter=Q(spf_aligned=False, dkim_aligned=False, is_acknowledged=False)),
        # NEW: Last Seen based on record date
        last_seen=Max('date_begin')
    ).order_by('-total')

    # 5. Chart Logic (Multi-Line by Domain)
    trunc_func = TruncDay
    if granularity == 'week':
        trunc_func = TruncWeek
    elif granularity == 'month':
        trunc_func = TruncMonth

    # A. Get Top 10 Domains
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
    unique_dates = sorted(list(set(item['date_group'].strftime('%Y-%m-%d') for item in chart_data_qs)))
    
    series_data = []
    for domain in top_domains:
        domain_volumes = []
        for date in unique_dates:
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
        'threat_ips': threat_ips, 
        'pass_percentage': pass_percentage,
        'domain_stats': domain_stats,
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

# --- NEW VIEW FOR ALL REPORTS ---
def report_list(request):
    """
    Shows a paginated list of all reports, ordered by date (newest first).
    """
    report_list = DmarcReport.objects.select_related('domain_entity').all().order_by('-date_begin')
    
    paginator = Paginator(report_list, 50) # Show 50 reports per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj
    }
    return render(request, 'dashboard/report_list.html', context)

def active_threats(request):
    """
    Shows a consolidated list of ALL unacknowledged threats across ALL domains.
    """
    period = request.GET.get('period', '30d')
    days_map = {'7d': 7, '30d': 30, '90d': 90}
    days = days_map.get(period, 30)
    
    date_end = timezone.now()
    date_begin = date_end - timedelta(days=days)

    threats = DmarcReport.objects.filter(
        date_begin__gte=date_begin,
        date_begin__lte=date_end,
        spf_aligned=False,
        dkim_aligned=False,
        is_acknowledged=False
    ).select_related('domain_entity').order_by('-date_begin')

    context = {
        'reports': threats,
        'period': period,
        'total_threats': threats.count()
    }
    return render(request, 'dashboard/active_threats.html', context)

def trigger_ingest(request):
    if request.method == "POST":
        out = io.StringIO()
        try:
            call_command('ingest_dmarc', limit=10, stdout=out)
            output_text = out.getvalue()
            return HttpResponse(f"""
                <div class="text-sm text-green-600 bg-green-50 p-2 rounded flex items-center">
                    <span class="mr-2">✔</span> Sync Complete: {output_text.splitlines()[-1] if output_text else 'Done'}
                </div>
            """)
        except Exception as e:
            return HttpResponse(f"""
                <div class="text-sm text-red-600 bg-red-50 p-2 rounded">
                    Error: {str(e)}
                </div>
            """)
    return HttpResponse(status=400)

def acknowledge_report(request, report_id):
    if request.method == "POST":
        report = get_object_or_404(DmarcReport, id=report_id)
        report.is_acknowledged = not report.is_acknowledged
        report.save()
        
        checked_attr = "checked" if report.is_acknowledged else ""
        label_text = "Reviewed" if report.is_acknowledged else "Mark as Reviewed"
        text_color = "text-green-600 font-bold" if report.is_acknowledged else "text-gray-500"
        
        return HttpResponse(f"""
            <label class="inline-flex items-center cursor-pointer select-none">
                <input type="checkbox" 
                       {checked_attr}
                       hx-post="/report/{report.id}/ack/" 
                       hx-swap="innerHTML" 
                       hx-target="#ack-btn-{report.id}"
                       class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50">
                <span class="ml-2 text-xs {text_color}">{label_text}</span>
            </label>
        """)
    return HttpResponse(status=400)