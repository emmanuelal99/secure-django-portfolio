"""
Forms for the dashboard CRUD interface.

Uses ModelForm for Project creation/editing with a clean widget set.
"""

from django import forms

from .models import Project, Technology


class ProjectForm(forms.ModelForm):
    """Form for creating and editing projects via the dashboard."""

    # Allow creating new technologies inline via comma-separated input
    technologies_input = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. Python, Django, Docker",
                "class": "form-input",
            }
        ),
        help_text="Comma-separated list of technologies. New ones are created automatically.",
    )

    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "github_link",
            "live_demo",
            "image",
            "is_featured",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "Project Title"}),
            "description": forms.Textarea(
                attrs={
                    "class": "form-input form-textarea",
                    "rows": 8,
                    "placeholder": "Describe your project…",
                }
            ),
            "github_link": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://github.com/..."}
            ),
            "live_demo": forms.URLInput(
                attrs={"class": "form-input", "placeholder": "https://example.com"}
            ),
            "image": forms.ClearableFileInput(attrs={"class": "form-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill technology input if editing an existing project
        if self.instance and self.instance.pk:
            self.fields["technologies_input"].initial = ", ".join(
                self.instance.technologies.values_list("name", flat=True)
            )

    def save(self, commit=True):
        project = super().save(commit=commit)
        if commit:
            self._save_technologies(project)
        return project

    def _save_technologies(self, project):
        """Parse comma-separated tech input and link to the project."""
        raw = self.cleaned_data.get("technologies_input", "")
        tech_names = [t.strip() for t in raw.split(",") if t.strip()]
        techs = []
        for name in tech_names:
            tech, _ = Technology.objects.get_or_create(
                name__iexact=name,
                defaults={"name": name},
            )
            techs.append(tech)
        project.technologies.set(techs)
