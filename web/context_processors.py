def portal(request):
    user = getattr(request, 'user', None)
    context = {'is_admin': bool(user and user.is_authenticated and getattr(user, 'is_admin', False))}
    election = getattr(request, 'election', None)
    if election is not None:
        # The switch between elections: same page, same filters, other election.
        from election.models import Election
        links = []
        for e in Election.objects.all():
            query = request.GET.copy()
            query['election'] = e.slug
            query.pop('page', None)
            links.append({'slug': e.slug, 'name': e.name, 'active': e.pk == election.pk,
                          'url': f'{request.path}?{query.urlencode()}'})
        context.update(election=election, elections=links)
    return context
