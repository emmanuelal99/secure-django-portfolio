"""URL routing for the projects app.

Public routes exist in every container. Dashboard and auth routes are only
added when ENABLE_ADMIN is True, which is the admin container reached through
the SSM tunnel (and your laptop when DEBUG=True).
"""

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # ── Public ──────────────────────────────────
    path("", views.ProjectListView.as_view(), name="project_list"),
    path("project/<slug:slug>/", views.ProjectDetailView.as_view(), name="project_detail"),
]

if settings.ENABLE_ADMIN:
    urlpatterns += [
        # ── Dashboard ───────────────────────────────
        path("dashboard/", views.DashboardListView.as_view(), name="dashboard_list"),
        path("dashboard/add/", views.DashboardCreateView.as_view(), name="dashboard_create"),
        path(
            "dashboard/<slug:slug>/edit/",
            views.DashboardUpdateView.as_view(),
            name="dashboard_update",
        ),
        path(
            "dashboard/<slug:slug>/delete/",
            views.DashboardDeleteView.as_view(),
            name="dashboard_delete",
        ),
        # ── Auth ────────────────────────────────────
        path(
            "dashboard/login/",
            auth_views.LoginView.as_view(template_name="registration/login.html"),
            name="dashboard_login",
        ),
        path(
            "dashboard/logout/",
            auth_views.LogoutView.as_view(),
            name="dashboard_logout",
        ),
    ]