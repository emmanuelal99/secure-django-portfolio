"""
Django admin configuration for the projects app.

Provides a rich admin interface with image previews, inline technology
management, and search/filter capabilities.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Project, Technology


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "project_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="# Projects")
    def project_count(self, obj):
        return obj.projects.count()


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "image_preview_small",
        "is_featured",
        "tech_list",
        "created_at",
    )
    list_filter = ("is_featured", "technologies", "created_at")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("technologies",)
    readonly_fields = ("image_preview_large", "created_at", "updated_at")
    list_editable = ("is_featured",)
    date_hierarchy = "created_at"

    fieldsets = (
        (
            None,
            {
                "fields": ("title", "slug", "description"),
            },
        ),
        (
            "Media",
            {
                "fields": ("image", "image_preview_large"),
            },
        ),
        (
            "Links",
            {
                "fields": ("github_link", "live_demo"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("technologies", "is_featured", "created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description="Preview")
    def image_preview_small(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;width:40px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return "—"

    @admin.display(description="Image Preview")
    def image_preview_large(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:300px;max-width:100%;border-radius:8px;" />',
                obj.image.url,
            )
        return "No image uploaded yet."

    @admin.display(description="Technologies")
    def tech_list(self, obj):
        return ", ".join(t.name for t in obj.technologies.all())
