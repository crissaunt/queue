from django.shortcuts import redirect
from django.urls import reverse

class PersonelAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Exclude login/register routes
        allowed_paths = [reverse("auth_login"), reverse("auth_register")]
        
        if not request.session.get("user_id") and request.path not in allowed_paths:
            return redirect("auth_login")

        return self.get_response(request)
