from django import template

register = template.Library()


@register.filter
def split(value, separator=","):
    """Split a string in templates while ignoring empty items."""
    if value is None:
        return []
    return [item.strip() for item in str(value).split(separator) if item.strip()]
