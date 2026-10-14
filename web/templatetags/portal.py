from django import template

register = template.Library()


@register.filter
def num(value):
    """1234567 -> '1,234,567'."""
    try:
        return f'{int(value):,}'
    except (TypeError, ValueError):
        return value


@register.filter
def get(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.filter
def plural(count, word):
    return word if count == 1 else f'{word}s'


@register.filter
def ago(value):
    """'just now', '5 min ago', '2 hr ago', '3 d ago' - like the old frontend."""
    if not value:
        return '—'
    from django.utils import timezone
    secs = max(0, int((timezone.now() - value).total_seconds()))
    if secs < 60:
        return 'just now'
    if secs < 3600:
        return f'{secs // 60} min ago'
    if secs < 86400:
        return f'{secs // 3600} hr ago'
    return f'{secs // 86400} d ago'
