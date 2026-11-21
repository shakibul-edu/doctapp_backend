from django.urls import path

from .views import (
    AppointmentCancelView,
    AppointmentCompleteView,
    AppointmentConfirmView,
    AppointmentDetailView,
    AppointmentListCreateView,
    AppointmentMeView,
    DoctorAvailabilityView,
)

app_name = "appointments"

urlpatterns = [
    path("", AppointmentListCreateView.as_view(), name="appointment-list-create"),
    path("me/", AppointmentMeView.as_view(), name="appointment-me"),
    path("<uuid:id>/", AppointmentDetailView.as_view(), name="appointment-detail"),
    path("<uuid:id>/cancel/", AppointmentCancelView.as_view(), name="appointment-cancel"),
    path("<uuid:id>/confirm/", AppointmentConfirmView.as_view(), name="appointment-confirm"),
    path("<uuid:id>/complete/", AppointmentCompleteView.as_view(), name="appointment-complete"),
]
