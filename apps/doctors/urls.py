from django.urls import path

from .views import (
    AssistantDoctorsView,
    DoctorAssistantDeleteView,
    DoctorAssistantListCreateView,
    DoctorDetailView,
    DoctorFilterOptionsView,
    DoctorListView,
    DoctorMeView,
    DoctorSpecializationListView,
)

app_name = "doctors"

urlpatterns = [
    path("", DoctorListView.as_view(), name="doctor-list"),
    path("filter-options/", DoctorFilterOptionsView.as_view(), name="doctor-filter-options"),
    path("specializations/", DoctorSpecializationListView.as_view(), name="doctor-specializations"),
    path("me/", DoctorMeView.as_view(), name="doctor-me"),
    path("me/assistants/", DoctorAssistantListCreateView.as_view(), name="doctor-assistants"),
    path(
        "me/assistants/<uuid:id>/",
        DoctorAssistantDeleteView.as_view(),
        name="doctor-assistant-detail",
    ),
    path("<uuid:id>/", DoctorDetailView.as_view(), name="doctor-detail"),
]
