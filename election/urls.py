from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CSRFTokenView, LoginView, LogoutView, CurrentUserView,
    LocalGovernmentAreaViewSet, WardViewSet,
    PollingUnitViewSet, PoliticalPartyViewSet,
    ElectionResultViewSet
)

router = DefaultRouter()
router.register(r'lgas', LocalGovernmentAreaViewSet, basename='lga')
router.register(r'wards', WardViewSet, basename='ward')
router.register(r'polling-units', PollingUnitViewSet, basename='polling-unit')
router.register(r'parties', PoliticalPartyViewSet, basename='party')
router.register(r'results', ElectionResultViewSet, basename='result')

urlpatterns = [
    path('auth/csrf/', CSRFTokenView.as_view(), name='csrf-token'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),
    path('', include(router.urls)),
]

