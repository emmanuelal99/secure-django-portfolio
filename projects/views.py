"""
Views for the portfolio projects app.

Public views:
    ProjectListView   – paginated grid of all projects
    ProjectDetailView – single project detail page

Dashboard views (login required):
    DashboardListView     – manage projects
    DashboardCreateView   – add new project
    DashboardUpdateView   – edit existing project
    DashboardDeleteView   – delete project
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import ProjectForm
from .models import Project, Technology


# ──────────────────────────────────────────────
# Public views
# ──────────────────────────────────────────────


class ProjectListView(ListView):
    """Public portfolio page showing all projects in a grid."""

    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 9

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("technologies")

        # Search by title or description
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query))

        # Filter by technology slug
        tech_slug = self.request.GET.get("tech", "").strip()
        if tech_slug:
            qs = qs.filter(technologies__slug=tech_slug)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["technologies"] = Technology.objects.all()
        context["current_tech"] = self.request.GET.get("tech", "")
        context["search_query"] = self.request.GET.get("q", "")
        return context


class ProjectDetailView(DetailView):
    """Full detail page for a single project."""

    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("technologies")


# ──────────────────────────────────────────────
# Dashboard views (authentication required)
# ──────────────────────────────────────────────


class DashboardListView(LoginRequiredMixin, ListView):
    """Dashboard listing all projects for management."""

    model = Project
    template_name = "projects/dashboard/project_list.html"
    context_object_name = "projects"
    paginate_by = 12


class DashboardCreateView(LoginRequiredMixin, CreateView):
    """Create a new project via the dashboard."""

    model = Project
    form_class = ProjectForm
    template_name = "projects/dashboard/project_form.html"
    success_url = reverse_lazy("dashboard_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add New Project"
        context["submit_label"] = "Create Project"
        return context


class DashboardUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing project via the dashboard."""

    model = Project
    form_class = ProjectForm
    template_name = "projects/dashboard/project_form.html"
    success_url = reverse_lazy("dashboard_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit: {self.object.title}"
        context["submit_label"] = "Save Changes"
        return context


class DashboardDeleteView(LoginRequiredMixin, DeleteView):
    """Confirm and delete a project."""

    model = Project
    template_name = "projects/dashboard/project_confirm_delete.html"
    context_object_name = "project"
    success_url = reverse_lazy("dashboard_list")
