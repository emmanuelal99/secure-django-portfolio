"""Custom template tags and filters for the projects app."""

from django import template
from django.utils.html import format_html_join

register = template.Library()


@register.filter
def tech_badges(technologies):
    """Render a queryset of Technology objects as styled badge spans.

    format_html_join escapes each technology name, so a name containing
    HTML or JavaScript is shown as text instead of being executed.
    """
    return format_html_join(
        " ",
        '<span class="tech-badge">{}</span>',
        ((tech.name,) for tech in technologies.all()),
    )


@register.simple_tag
def query_string(request, **kwargs):
    """
    Build a query string preserving existing params but overriding
    the ones provided as keyword arguments.

    Usage: {% query_string request page=3 %}
    """
    params = request.GET.copy()
    for key, value in kwargs.items():
        params[key] = value
    return f"?{params.urlencode()}"