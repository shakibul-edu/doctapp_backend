from django.urls import path

from .views import ChamberDetailView, ChamberListCreateView

urlpatterns = [
    path("", ChamberListCreateView.as_view(), name="chamber-list"),
    path("<uuid:id>/", ChamberDetailView.as_view(), name="chamber-detail"),
]
