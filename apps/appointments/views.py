from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsAssistant, IsDoctor, IsPatient
from apps.doctors.models import DoctorAssistant, DoctorProfile
from apps.hospitals.models import Chamber

from .models import Appointment, AvailabilitySchedule, ScheduleException
from .serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    AvailabilityScheduleSerializer,
    ScheduleExceptionSerializer,
)
from .services import generate_available_slots


def _assistant_doctor_ids(user):
    return DoctorAssistant.objects.filter(
        assistant=user,
        active=True,
    ).values("doctor_id")


def _can_manage_appointment(user, appointment):
    if user.role == User.Role.DOCTOR:
        doctor = getattr(user, "doctor_profile", None)
        return doctor is not None and appointment.doctor_id == doctor.id
    if user.role == User.Role.ASSISTANT:
        return DoctorAssistant.objects.filter(
            doctor_id=appointment.doctor_id,
            assistant=user,
            active=True,
        ).exists()
    return False


class DoctorAvailabilityView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, id):
        doctor = DoctorProfile.objects.filter(
            id=id,
            verification_status=DoctorProfile.VerificationStatus.APPROVED,
        ).first()
        if doctor is None:
            return Response({"detail": "Approved doctor not found."}, status=404)

        chamber = None
        chamber_id = request.query_params.get("chamber")
        if chamber_id:
            chamber = Chamber.objects.filter(
                id=chamber_id,
                doctor=doctor,
                active=True,
            ).first()
            if chamber is None:
                return Response(
                    {"detail": "Valid active chamber not found for this doctor."},
                    status=400,
                )

        date_value = request.query_params.get("date")
        from_value = request.query_params.get("from")
        to_value = request.query_params.get("to")
        raw_start = date_value or from_value
        try:
            start_date = (
                datetime.strptime(raw_start, "%Y-%m-%d").date()
                if raw_start
                else timezone.localtime().date()
            )
            end_date = (
                datetime.strptime(to_value, "%Y-%m-%d").date()
                if to_value
                else (start_date if date_value or from_value else start_date)
            )
        except ValueError:
            return Response(
                {"detail": "Dates must use YYYY-MM-DD format."},
                status=400,
            )
        if end_date < start_date:
            return Response({"detail": "End date must not be before start date."}, status=400)
        if (end_date - start_date).days > 31:
            return Response({"detail": "Availability range cannot exceed 31 days."}, status=400)

        slots = generate_available_slots(
            doctor,
            chamber=chamber,
            start_date=start_date,
            end_date=end_date,
        )
        return Response(
            {
                "doctor": str(doctor.id),
                "chamber": str(chamber.id) if chamber else None,
                "slots": [
                    {
                        "chamber": slot["chamber"],
                        "start_at": slot["start_at"],
                        "end_at": slot["end_at"],
                        "duration_minutes": slot["duration_minutes"],
                    }
                    for slot in slots
                ],
            }
        )


class DoctorScheduleListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsDoctor,)
    serializer_class = AvailabilityScheduleSerializer

    def get_queryset(self):
        doctor = getattr(self.request.user, "doctor_profile", None)
        if doctor is None:
            return AvailabilitySchedule.objects.none()
        return AvailabilitySchedule.objects.filter(doctor=doctor).select_related("chamber")


class DoctorScheduleDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsDoctor,)
    serializer_class = AvailabilityScheduleSerializer
    lookup_field = "id"

    def get_queryset(self):
        doctor = getattr(self.request.user, "doctor_profile", None)
        if doctor is None:
            return AvailabilitySchedule.objects.none()
        return AvailabilitySchedule.objects.filter(doctor=doctor)


class DoctorScheduleExceptionListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsDoctor,)
    serializer_class = ScheduleExceptionSerializer

    def get_queryset(self):
        doctor = getattr(self.request.user, "doctor_profile", None)
        if doctor is None:
            return ScheduleException.objects.none()
        return ScheduleException.objects.filter(doctor=doctor).select_related("chamber")


class DoctorScheduleExceptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (IsDoctor,)
    serializer_class = ScheduleExceptionSerializer
    lookup_field = "id"

    def get_queryset(self):
        doctor = getattr(self.request.user, "doctor_profile", None)
        if doctor is None:
            return ScheduleException.objects.none()
        return ScheduleException.objects.filter(doctor=doctor)


class AppointmentListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return (IsPatient(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.PATIENT:
            return Appointment.objects.filter(patient=user).select_related(
                "doctor", "chamber", "patient"
            )
        if user.role == User.Role.DOCTOR:
            doctor = getattr(user, "doctor_profile", None)
            return (
                Appointment.objects.filter(doctor=doctor).select_related("doctor", "chamber", "patient")
                if doctor
                else Appointment.objects.none()
            )
        if user.role == User.Role.ASSISTANT:
            return Appointment.objects.filter(
                doctor_id__in=_assistant_doctor_ids(user)
            ).select_related("doctor", "chamber", "patient")
        return Appointment.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = AppointmentCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        appointment = serializer.save()
        output = AppointmentSerializer(
            appointment,
            context={"request": request},
        )
        return Response(output.data, status=status.HTTP_201_CREATED)


class AppointmentMeView(generics.ListAPIView):
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.PATIENT:
            return Appointment.objects.filter(patient=user)
        if user.role == User.Role.DOCTOR:
            doctor = getattr(user, "doctor_profile", None)
            return Appointment.objects.filter(doctor=doctor) if doctor else Appointment.objects.none()
        if user.role == User.Role.ASSISTANT:
            return Appointment.objects.filter(doctor_id__in=_assistant_doctor_ids(user))
        return Appointment.objects.none()


class AppointmentDetailView(generics.RetrieveAPIView):
    serializer_class = AppointmentSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.role == User.Role.PATIENT:
            qs = Appointment.objects.filter(patient=user)
        elif user.role == User.Role.DOCTOR:
            doctor = getattr(user, "doctor_profile", None)
            qs = Appointment.objects.filter(doctor=doctor) if doctor else Appointment.objects.none()
        elif user.role == User.Role.ASSISTANT:
            qs = Appointment.objects.filter(doctor_id__in=_assistant_doctor_ids(user))
        else:
            qs = Appointment.objects.none()
        return qs.select_related("doctor", "chamber", "patient")


class AppointmentCancelView(APIView):
    def post(self, request, id):
        appointment = (
            Appointment.objects.select_related("doctor", "chamber")
            .filter(id=id)
            .first()
        )
        if appointment is None:
            return Response({"detail": "Appointment not found."}, status=404)
        if request.user.role == User.Role.PATIENT:
            if appointment.patient_id != request.user.id:
                return Response({"detail": "You cannot cancel another patient's appointment."}, status=403)
        elif not _can_manage_appointment(request.user, appointment):
            return Response({"detail": "You cannot manage this appointment."}, status=403)

        if appointment.status not in (
            Appointment.Status.PENDING,
            Appointment.Status.CONFIRMED,
        ):
            return Response(
                {"detail": "Only pending or confirmed appointments can be cancelled."},
                status=400,
            )
        if appointment.start_at <= timezone.now() + timedelta(hours=2):
            return Response(
                {"detail": "Appointments can only be cancelled more than 2 hours before the start time."},
                status=400,
            )

        reason = request.data.get("reason", "")
        if not str(reason).strip():
            return Response({"detail": "Cancellation reason is required."}, status=400)
        appointment.status = Appointment.Status.CANCELLED
        appointment.cancellation_reason = str(reason).strip()
        appointment.save(update_fields=("status", "cancellation_reason", "updated_at"))
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)


class AppointmentStatusView(APIView):
    target_status = None

    def post(self, request, id):
        appointment = (
            Appointment.objects.select_related("doctor", "chamber")
            .filter(id=id)
            .first()
        )
        if appointment is None:
            return Response({"detail": "Appointment not found."}, status=404)
        if not _can_manage_appointment(request.user, appointment):
            return Response(
                {"detail": "Only the doctor or an authorized assistant can change this status."},
                status=403,
            )

        if self.target_status == Appointment.Status.CONFIRMED:
            if appointment.status != Appointment.Status.PENDING:
                return Response({"detail": "Only pending appointments can be confirmed."}, status=400)
        if self.target_status == Appointment.Status.COMPLETED:
            if appointment.status != Appointment.Status.CONFIRMED:
                return Response({"detail": "Only confirmed appointments can be completed."}, status=400)

        appointment.status = self.target_status
        appointment.save(update_fields=("status", "updated_at"))
        return Response(AppointmentSerializer(appointment, context={"request": request}).data)


class AppointmentConfirmView(AppointmentStatusView):
    target_status = Appointment.Status.CONFIRMED


class AppointmentCompleteView(AppointmentStatusView):
    target_status = Appointment.Status.COMPLETED
