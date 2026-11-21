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
from apps.appointments.views import (
    DoctorAvailabilityView,
    DoctorScheduleDetailView,
    DoctorScheduleExceptionDetailView,
    DoctorScheduleExceptionListCreateView,
    DoctorScheduleListCreateView,
)

app_name = "doctors"

urlpatterns = [
    path("", DoctorListView.as_view(), name="doctor-list"),
    path("filter-options/", DoctorFilterOptionsView.as_view(), name="doctor-filter-options"),
    path("specializations/", DoctorSpecializationListView.as_view(), name="doctor-specializations"),
    path("me/", DoctorMeView.as_view(), name="doctor-me"),
    path("me/schedules/", DoctorScheduleListCreateView.as_view(), name="doctor-schedules"),
    path("me/schedules/<uuid:id>/", DoctorScheduleDetailView.as_view(), name="doctor-schedule-detail"),
    path("me/exceptions/", DoctorScheduleExceptionListCreateView.as_view(), name="doctor-schedule-exceptions"),
    path(
        "me/exceptions/<uuid:id>/",
        DoctorScheduleExceptionDetailView.as_view(),
        name="doctor-schedule-exception-detail",
    ),
    path("me/assistants/", DoctorAssistantListCreateView.as_view(), name="doctor-assistants"),
    path(
        "me/assistants/<uuid:id>/",
        DoctorAssistantDeleteView.as_view(),
        name="doctor-assistant-detail",
    ),
    path("<uuid:id>/availability/", DoctorAvailabilityView.as_view(), name="doctor-availability"),
    path("<uuid:id>/", DoctorDetailView.as_view(), name="doctor-detail"),
]
