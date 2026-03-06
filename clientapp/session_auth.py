from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.middleware.csrf import get_token
import json


def _resolve_portal_role(user, groups):
    if user.is_superuser or 'Admin' in groups:
        return 'admin'
    if 'Account Manager' in groups:
        return 'account_manager'
    if 'Production Team' in groups:
        return 'production_team'
    try:
        from .models import ClientPortalUser
        if ClientPortalUser.objects.filter(user=user, is_active=True).exists():
            return 'client'
    except Exception:
        pass
    try:
        from .models import Vendor
        if Vendor.objects.filter(user=user, active=True).exists():
            return 'vendor'
    except Exception:
        pass
    return None


@require_http_methods(["POST"])
def session_login(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return JsonResponse({
                'error': 'Username and password are required'
            }, status=400)
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_active:
            login(request, user)
            groups = list(user.groups.values_list('name', flat=True))
            portal_role = _resolve_portal_role(user, groups)
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'is_active': user.is_active,
                    'groups': groups,
                    'portal_role': portal_role,
                }
            })
        else:
            return JsonResponse({
                'error': 'Invalid credentials'
            }, status=401)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON'
        }, status=400)
    except Exception:
        return JsonResponse({
            'error': 'Unable to process request. Please try again.'
        }, status=500)


@require_http_methods(["POST"])
def session_logout(request):
    logout(request)
    return JsonResponse({'success': True})


@ensure_csrf_cookie
@require_http_methods(["GET"])
def get_csrf_token(request):
    return JsonResponse({
        'csrfToken': get_token(request)
    })


@require_http_methods(["GET"])
def check_session(request):
    if request.user.is_authenticated:
        user = request.user
        groups = list(user.groups.values_list('name', flat=True))
        portal_role = _resolve_portal_role(user, groups)
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'is_active': user.is_active,
                'groups': groups,
                'portal_role': portal_role,
            }
        })
    else:
        return JsonResponse({
            'authenticated': False
        }, status=401)
