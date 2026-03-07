"""
URL configuration for client project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static

from clientapp.api_views import RegisterView, ChangePasswordView
from clientapp.admin_login_bypass import AdminLoginBypassView
from clientapp.direct_admin_login import direct_admin_login
from clientapp import session_auth
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})
from clientapp.storefront_views import (
    StorefrontHomeView,
    StorefrontProductsPageView,
    StorefrontLoginPageView,
    StorefrontRegisterPageView,
    StorefrontQuoteBuilderPageView,
    StorefrontContactPageView,
    StorefrontDashboardPageView,
)


schema_view = get_schema_view(
    openapi.Info(
        title="PrintDuka API",
        default_version="v1",
        description="Headless API for PrintDuka",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('api/health/', health_check, name='health_check'),
    path('direct-login/', direct_admin_login, name='direct_login'),
    path('admin/', admin.site.urls),
    path('admin-bypass-login/', AdminLoginBypassView.as_view(), name='admin_bypass'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='admin/login.html'), name='login'),

    # API + Auth (JWT)
    path('api/v1/', include('clientapp.api_urls')),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/register/', RegisterView.as_view(), name='api_register'),
    path('api/auth/change-password/', ChangePasswordView.as_view(), name='api_change_password'),

    # Session-based Auth (for web app with httpOnly cookies)
    path('api/auth/session/login/', session_auth.session_login, name='session_login'),
    path('api/auth/session/logout/', session_auth.session_logout, name='session_logout'),
    path('api/auth/session/check/', session_auth.check_session, name='check_session'),
    path('api/auth/csrf/', session_auth.get_csrf_token, name='get_csrf_token'),

    # API Docs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # ========================================================================
    # STOREFRONT FRONTEND PAGES (HTML Template Views)
    # ========================================================================
    path('storefront/', StorefrontHomeView.as_view(), name='storefront-home'),
    path('storefront/products/', StorefrontProductsPageView.as_view(), name='storefront-products'),
    path('storefront/login/', StorefrontLoginPageView.as_view(), name='storefront-login'),
    path('storefront/register/', StorefrontRegisterPageView.as_view(), name='storefront-register'),
    path('storefront/quote-builder/', StorefrontQuoteBuilderPageView.as_view(), name='storefront-quote-builder'),
    path('storefront/contact/', StorefrontContactPageView.as_view(), name='storefront-contact'),
    path('storefront/dashboard/', StorefrontDashboardPageView.as_view(), name='storefront-dashboard'),

    path('', include('clientapp.urls')),
    path('quickbooks/', include('quickbooks_integration.urls')),

]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

