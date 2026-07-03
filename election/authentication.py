from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class OptionalTokenAuthentication(TokenAuthentication):
    """Token auth that does NOT hard-fail on a bad/expired token.

    Django REST Framework's default TokenAuthentication raises 401 as soon as an
    Authorization header carries an invalid token — even for AllowAny (public)
    endpoints like the landing-page charts. Since the frontend attaches whatever
    token sits in localStorage to every request, a single stale token would break
    all the public pages.

    Here an invalid token is simply ignored (the request continues as an
    anonymous user), so:
      * public endpoints keep working, and
      * protected endpoints still return 401 via IsAuthenticated, because the
        user ends up unauthenticated.
    """

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None
