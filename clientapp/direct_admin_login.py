from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["GET", "POST"])
def direct_admin_login(request):
    if request.method == "GET":
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Direct Admin Login</title>
            <style>
                body { font-family: Arial; max-width: 400px; margin: 100px auto; padding: 20px; }
                input { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #417690; color: white; border: none; cursor: pointer; }
                button:hover { background: #305a6e; }
                .error { color: red; margin: 10px 0; }
            </style>
        </head>
        <body>
            <h2>Direct Admin Login</h2>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        """
        return HttpResponse(html)
    
    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "").strip()
    
    # Debug database location
    from django.conf import settings
    db_path = settings.DATABASES['default'].get('NAME', 'unknown')
    print(f"Database location: {db_path}")
    
    # Debug logging
    print(f"Login attempt - Username: '{username}' (len={len(username)}), Password: '{password}' (len={len(password)})")
    
    # Try to get user directly
    from django.contrib.auth.models import User
    all_users = User.objects.all()
    print(f"Total users in database: {all_users.count()}")
    for u in all_users[:5]:
        print(f"  - {u.username} (staff={u.is_staff}, active={u.is_active})")
    
    try:
        db_user = User.objects.get(username=username)
        print(f"User found in DB: {db_user.username}, is_active={db_user.is_active}")
        print(f"Password check: {db_user.check_password(password)}")
    except User.DoesNotExist:
        print(f"User '{username}' NOT FOUND in database")
    
    # Don't pass request to authenticate - it can interfere
    user = authenticate(username=username, password=password)
    
    print(f"Authentication result: {user}")
    if user:
        print(f"User details - is_staff: {user.is_staff}, is_active: {user.is_active}, is_superuser: {user.is_superuser}")
    
    if user is not None and user.is_active and user.is_staff:
        login(request, user)
        print(f"Login successful for {username}")
        return HttpResponseRedirect("/admin/")
    else:
        error_msg = "Invalid credentials or not a staff account"
        if user and not user.is_staff:
            error_msg = "User exists but is not a staff member"
        elif user and not user.is_active:
            error_msg = "User account is inactive"
        elif not user:
            error_msg = "Invalid username or password"
        
        print(f"Login failed: {error_msg}")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Direct Admin Login</title>
            <style>
                body {{ font-family: Arial; max-width: 400px; margin: 100px auto; padding: 20px; }}
                input {{ width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }}
                button {{ width: 100%; padding: 12px; background: #417690; color: white; border: none; cursor: pointer; }}
                button:hover {{ background: #305a6e; }}
                .error {{ color: red; margin: 10px 0; padding: 10px; background: #fee; }}
            </style>
        </head>
        <body>
            <h2>Direct Admin Login</h2>
            <div class="error">❌ {error_msg}</div>
            <form method="POST">
                <input type="text" name="username" placeholder="Username" value="{username or ''}" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </body>
        </html>
        """
        return HttpResponse(html)
