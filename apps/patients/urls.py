from django.urls import path

from .views import PatientDetailView, PatientMeView

app_name = "patients"

urlpatterns = [
    path("me/", PatientMeView.as_view(), name="patient-me"),
    path("<uuid:id>/", PatientDetailView.as_view(), name="patient-detail"),
]
