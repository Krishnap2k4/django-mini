from apps.notifications.models import Notification


def dashboard_context(request):
    """Inject unread notification count and recent items for the topbar bell."""
    if request.user.is_authenticated and hasattr(request.user, 'is_superadmin') and request.user.is_superadmin:
        unread_qs = Notification.objects.filter(is_read=False).order_by('-created_at')
        return {
            'unread_notifications': unread_qs.count(),
            'recent_notifications': unread_qs[:5],
        }
    return {}
