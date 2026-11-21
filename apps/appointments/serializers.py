from datetime import timezone as datetime_timezone
from decimal import Decimal

from django.db import transaction
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.doctors.models import DoctorProfile
from apps.hospitals.models import Chamber

from .models import Appointment, AvailabilitySchedule, ScheduleException
from .services import generate_available_slots


class AvailabilityScheduleSerializer(serializers.ModelSerializer):
    doctor = serializers.UUIDField(source="doctor.id", read_only=True)
    chamber = serializers.UUIDField()

    class Meta:
        model = AvailabilitySchedule
        fields = (
            "id",
            "doctor",
            "chamber",
            "weekday",
            "start_time",
            "end_time",
            "appointment_duration_minutes",
            "break_start",
            "break_end",
            "active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "doctor", "created_at", "updated_at")

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        break_start = attrs.get("break_start")
        break_end = attrs.get("break_end")
        if (break_start is None) != (break_end is None):
            raise serializers.ValidationError("Break start and end must be provided together.")
        if break_start is not None and not (attrs["start_time"] < break_start < break_end < attrs["end_time"]):
            raise serializers.ValidationError("Break must be inside the schedule and end after it starts.")
        chamber_id = attrs.get("chamber")
        request = self.context["request"]
        doctor = getattr(request.user, "doctor_profile", None)
        if doctor is None:
            raise serializers.ValidationError("Create your doctor profile first.")
        try:
            chamber = Chamber.objects.get(id=chamber_id, doctor=doctor)
        except Chamber.DoesNotExist:
            raise serializers.ValidationError({"chamber": "This is not an active chamber belonging to you."})
        attrs["chamber"] = chamber
        attrs["doctor"] = doctor
        return attrs


class ScheduleExceptionSerializer(serializers.ModelSerializer):
    chamber = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = ScheduleException
        fields = (
            "id",
            "chamber",
            "exception_type",
            "date",
            "start_datetime",
            "end_datetime",
            "start_time",
            "end_time",
            "break_start",
            "break_end",
            "active",
            "reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        exception_type = attrs.get("exception_type", getattr(self.instance, "exception_type", None))
        if exception_type in (
            ScheduleException.ExceptionType.MODIFIED_HOURS,
            ScheduleException.ExceptionType.ONE_TIME,
        ):
            if attrs.get("start_time") is None or attrs.get("end_time") is None:
                if getattr(self.instance, "start_time", None) is None or getattr(self.instance, "end_time", None) is None:
                    raise serializers.ValidationError("Modified hours require start_time and end_time.")
            start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
            end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
            if start_time is not None and end_time is not None and end_time <= start_time:
                raise serializers.ValidationError({"end_time": "End time must be after start time."})

        chamber_id = attrs.get("chamber")
        request = self.context["request"]
        doctor = getattr(request.user, "doctor_profile", None)
        if doctor is None:
            raise serializers.ValidationError("Create your doctor profile first.")
        if chamber_id:
            try:
                attrs["chamber"] = Chamber.objects.get(id=chamber_id, doctor=doctor)
            except Chamber.DoesNotExist:
                raise serializers.ValidationError({"chamber": "This chamber does not belong to you."})
        else:
            attrs["chamber"] = None
        attrs["doctor"] = doctor
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            "id",
            "patient",
            "doctor",
            "chamber",
            "start_at",
            "end_at",
            "consultation_fee_snapshot",
            "status",
            "patient_notes",
            "cancellation_reason",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "patient",
            "doctor",
            "chamber",
            "end_at",
            "consultation_fee_snapshot",
            "status",
            "cancellation_reason",
            "created_at",
            "updated_at",
        )


class AppointmentCreateSerializer(serializers.Serializer):
    doctor = serializers.UUIDField()
    chamber = serializers.UUIDField()
    start_at = serializers.DateTimeField()
    patient_notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        request = self.context["request"]
        if request.user.role != User.Role.PATIENT:
            raise serializers.ValidationError("Only patients can book appointments.")
        try:
            patient_profile = request.user.patient_profile
        except Exception:
            patient_profile = None
        if patient_profile is None:
            raise serializers.ValidationError("Create your patient profile before booking.")

        try:
            doctor = DoctorProfile.objects.get(
                id=attrs["doctor"],
                verification_status=DoctorProfile.VerificationStatus.APPROVED,
            )
        except DoctorProfile.DoesNotExist:
            raise serializers.ValidationError({"doctor": "Doctor is not approved or does not exist."})

        try:
            chamber = Chamber.objects.get(
                id=attrs["chamber"],
                doctor=doctor,
                active=True,
            )
        except Chamber.DoesNotExist:
            raise serializers.ValidationError({"chamber": "This chamber is not active or belongs to another doctor."})

        start_at = attrs["start_at"]
        if timezone.is_naive(start_at):
            raise serializers.ValidationError({"start_at": "A timezone-aware datetime is required."})
        start_utc = start_at.astimezone(datetime_timezone.utc)
        if start_utc <= timezone.now():
            raise serializers.ValidationError({"start_at": "Past appointments cannot be booked."})

        local_start = timezone.localtime(start_utc)
        slots = generate_available_slots(
            doctor,
            chamber=chamber,
            start_date=local_start.date(),
            end_date=local_start.date(),
        )
        matched = next(
            (
                slot
                for slot in slots
                if slot["start_at"] == start_utc
                and str(slot["chamber"]) == str(chamber.id)
            ),
            None,
        )
        if matched is None:
            raise serializers.ValidationError({"start_at": "This start time is not available."})

        attrs["doctor"] = doctor
        attrs["chamber"] = chamber
        attrs["start_at"] = matched["start_at"]
        attrs["end_at"] = matched["end_at"]
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        doctor = validated_data["doctor"]
        chamber = validated_data["chamber"]
        fee = (
            chamber.consultation_fee_override
            if chamber.consultation_fee_override is not None
            else doctor.consultation_fee
        )

        try:
            with transaction.atomic():
                # Serialize all bookings for one doctor. The row lock also protects
                # against schedules changing between validation and insertion.
                DoctorProfile.objects.select_for_update().get(pk=doctor.pk)

                conflict = Appointment.objects.filter(
                    doctor=doctor,
                    status__in=(Appointment.Status.PENDING, Appointment.Status.CONFIRMED),
                    start_at__lt=validated_data["end_at"],
                    end_at__gt=validated_data["start_at"],
                ).exists()
                if conflict:
                    raise serializers.ValidationError(
                        {"start_at": "This slot is no longer available."}
                    )

                return Appointment.objects.create(
                    patient=request.user,
                    doctor=doctor,
                    chamber=chamber,
                    start_at=validated_data["start_at"],
                    end_at=validated_data["end_at"],
                    consultation_fee_snapshot=Decimal(fee),
                    patient_notes=validated_data.get("patient_notes", ""),
                )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"start_at": "This slot was just booked by another patient."}
            ) from exc
