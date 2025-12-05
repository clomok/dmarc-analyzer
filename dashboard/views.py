from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncDay
from .models import DmarcReport, DomainEntity

def dashboard(request):
    # ... (Keep your existing dashboard code exactly as it is) ...
    # 1. Date Filter Logic
    period = request.GET.get('period', '30d')
    days_map = {
        '7d': 7,
        '30d': 30,
        '90d': 90,
        'all': 365 * 10
    }
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
    
    # Handle None if DB is empty
    total_volume = global_stats['total_volume'] or 0
    dmarc_pass = global_stats['dmarc_pass_count'] or 0
    
    pass_percentage = 0
    if total_volume > 0:
        pass_percentage = round((dmarc_pass / total_volume) * 100, 1)

    # 4. Domain Level Details (Table)
    # NOTE: We need the ID now to build the link
    domain_stats = reports.values(
        'domain_entity__id',  # Added ID here
        'domain_entity__domain_name'
    ).annotate(
        total=Sum('count'),
        dmarc_pass_count=Sum('count', filter=Q(spf_aligned=True) | Q(dkim_aligned=True)),
        spf_pass_count=Sum('count', filter=Q(spf_aligned=True)),
        dkim_pass_count=Sum('count', filter=Q(dkim_aligned=True))
    ).order_by('-total')

    # 5. Prepare Chart Data (Time Series)
    timeline_qs = reports.annotate(
        day=TruncDay('date_begin')
    ).values('day').annotate(
        total=Sum('count'),
        passed=Sum('count', filter=Q(spf_aligned=True) | Q(dkim_aligned=True)),
        failed=Sum('count', filter=Q(spf_aligned=False) & Q(dkim_aligned=False))
    ).order_by('day')

    chart_dates = [x['day'].strftime('%Y-%m-%d') for x in timeline_qs]
    chart_pass = [x['passed'] for x in timeline_qs]
    chart_fail = [x['failed'] for x in timeline_qs]

    context = {
        'period': period,
        'global_stats': global_stats,
        'pass_percentage': pass_percentage,
        'domain_stats': domain_stats,
        'chart_dates': chart_dates,
        'chart_pass': chart_pass,
        'chart_fail': chart_fail,
    }

    return render(request, 'dashboard/dashboard.html', context)

# --- NEW FUNCTION ---
def domain_detail(request, domain_id):
    domain = get_object_or_404(DomainEntity, pk=domain_id)
    
    # Reuse Date Filter Logic
    period = request.GET.get('period', '30d')
    days_map = {'7d': 7, '30d': 30, '90d': 90}
    days = days_map.get(period, 30)
    
    date_end = timezone.now()
    date_begin = date_end - timedelta(days=days)
    
    # Fetch Reports for this domain only
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