from django.urls import path

from .views import (
    AssistantDoctorsView,
    DoctorAssistantDeleteView,
    DoctorAssistantListCreateView,
    DoctorDetailView,
    DoctorListView,
    DoctorMeView,
)

app_name = "doctors"

urlpatterns = [
    path("", DoctorListView.as_view(), name="doctor-list"),
    path("me/", DoctorMeView.as_view(), name="doctor-me"),
    path("me/assistants/", DoctorAssistantListCreateView.as_view(), name="doctor-assistants"),
    path(
        "me/assistants/<uuid:id>/",
        DoctorAssistantDeleteView.as_view(),
        name="doctor-assistant-detail",
    ),
    path("<uuid:id>/", DoctorDetailView.as_view(), name="doctor-detail"),
]
