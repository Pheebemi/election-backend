def portal(request):
    user = getattr(request, 'user', None)
    return {'is_admin': bool(user and user.is_authenticated and getattr(user, 'is_admin', False))}
