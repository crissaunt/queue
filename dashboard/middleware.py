# dashboard/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect

class DashboardAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only protect paths that start with /my/admin/
        dashboard_paths = [
            '/h/',
        ]
        
        # Check if this is a dashboard path
        is_dashboard_path = any(request.path.startswith(path) for path in dashboard_paths)
        
        # Within dashboard paths, these are allowed without authentication
        allowed_dashboard_paths = [
            '/h/login/',
            '/h/register/',
        ]
        
        is_allowed_dashboard_path = any(request.path.startswith(path) for path in allowed_dashboard_paths)
        
        # Update session for authenticated users
        if request.user.is_authenticated:
            request.session.set_expiry(86400)  # 24 hours
            request.session.modified = True
        
        # Only redirect if:
        # - It's a dashboard path
        # - User is not authenticated  
        # - It's not an allowed path (login/register)
        if (is_dashboard_path and 
            not request.user.is_authenticated and 
            not is_allowed_dashboard_path):
            redirect_url = f"/h/login/?next={request.path}"
            return HttpResponseRedirect(redirect_url)

        # For all other paths, proceed normally
        response = self.get_response(request)
        return response