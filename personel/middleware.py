# middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect

class PersonelAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only protect paths that start with /personel/
        personel_paths = [
            '/personel/',
        ]
        
        # Check if this is a personel path
        is_personel_path = any(request.path.startswith(path) for path in personel_paths)
        
        # Within personel paths, these are allowed without authentication
        allowed_personel_paths = [
            '/personel/auth/login/',
            '/personel/auth/register/',
        ]
        
        is_allowed_personel_path = any(request.path.startswith(path) for path in allowed_personel_paths)
        
        # Update session for authenticated users
        if request.user.is_authenticated:
            request.session.set_expiry(0)  # expire when browser closes

        
        # Only redirect if:
        # - It's a personel path
        # - User is not authenticated  
        # - It's not an allowed path (login/register)
        if (is_personel_path and 
            not request.user.is_authenticated and 
            not is_allowed_personel_path):
            redirect_url = f"{reverse('auth_login')}?next={request.path}"
            return HttpResponseRedirect(redirect_url)

        # For all other paths (admin, students, display, survey, etc.), proceed normally
        response = self.get_response(request)
        return response