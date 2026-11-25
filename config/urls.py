"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import JsonResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health', lambda r: JsonResponse({'status': 'ok'})),
    path('health/', lambda r: JsonResponse({'status': 'ok'})),
    path('', include('ailearn.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "سامانه مدیریت دبیرستان سخت‌کوشان"
admin.site.site_title = "مدیریت ai-learn"
admin.site.index_title = "پنل مدیریت دوره‌ها و ثبت‌نام‌ها"
