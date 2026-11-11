from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


@never_cache
@require_safe
def health(request):
    """Process liveness only; no billable image reads or database wakeups."""
    return JsonResponse({'status': 'ok'})
