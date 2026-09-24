"""
Data models for the portfolio projects app.

Provides Project and Technology models with a many-to-many relationship.
"""

from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Technology(models.Model):
    """A technology / skill tag (e.g. Python, React, Docker)."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "technologies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Project(models.Model):
    """A portfolio project with metadata, images, and links."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(
        help_text="Full project description. Supports plain text or Markdown."
    )
    github_link = models.URLField(
        max_length=500,
        help_text="Link to the GitHub repository.",
    )
    live_demo = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="Optional link to a live demo.",
    )
    image = models.ImageField(
        upload_to="projects/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "gif", "webp", "svg"]
            )
        ],
        help_text="Project cover image (JPG, PNG, GIF, WebP, or SVG).",
    )
    technologies = models.ManyToManyField(
        Technology,
        blank=True,
        related_name="projects",
        help_text="Technologies used in this project.",
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Feature this project at the top of the listing.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Project.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("project_detail", kwargs={"slug": self.slug})

    @property
    def short_description(self):
        """Return the first 160 characters of the description."""
        if len(self.description) <= 160:
            return self.description
        return self.description[:157] + "…"
