from django.urls import path

from .views import HospitalDetailView, HospitalListView

app_name = "hospitals"

urlpatterns = [
    path("", HospitalListView.as_view(), name="hospital-list"),
    path("<uuid:id>/", HospitalDetailView.as_view(), name="hospital-detail"),
]
