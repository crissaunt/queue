from functools import wraps
from django.shortcuts import redirect

def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("user_id"):  # check if user is logged in
            return redirect("auth_login")      # redirect to login page
        return view_func(request, *args, **kwargs)
    return wrapper
