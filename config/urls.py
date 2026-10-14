"""URL configuration.

/            the election portal (web app: results, projector, dashboard)
/api/        the REST API (still used by the apc portal)
/admin/      Django admin
/media/      party logos
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('election.urls')),
    # Party logos ship with the code (media/party_logos), so serve them in
    # production too - there is no separate file server on Vercel.
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    path('', include('web.urls')),
]
