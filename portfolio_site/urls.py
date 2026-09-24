"""
Root URL configuration for portfolio_site.

Routes:
    /           → public project listing
    /project/   → project detail pages
    /dashboard/ → authenticated CRUD dashboard (admin container only)
    /admin/     → Django admin (admin container only)

ENABLE_ADMIN is False in the public container, so /admin/ and /dashboard/
do not exist there at all. It is True only in the admin container, which is
reachable solely through an SSM port-forwarding session.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("projects.urls")),
]

if settings.ENABLE_ADMIN:
    urlpatterns += [
        path("admin/", admin.site.urls),
    ]

# Serve media files in development (production media is served from S3 via CloudFront)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)