from datetime import datetime, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.appointments.models import (
    Appointment,
    AvailabilitySchedule,
    ScheduleException,
)
from apps.appointments.services import generate_available_slots
from apps.doctors.models import DoctorAssistant, DoctorProfile
from apps.hospitals.models import Chamber
from apps.patients.models import PatientProfile


def create_user(email, role):
    return User.objects.create_user(
        email=email,
        password="SecurePass123!",
        first_name=email.split("@")[0],
        last_name="User",
        role=role,
        account_status=User.AccountStatus.ACTIVE,
    )


@pytest.fixture
def appointment_setup(db):
    doctor_user = create_user("schedule-doctor@example.com", User.Role.DOCTOR)
    patient_user = create_user("schedule-patient@example.com", User.Role.PATIENT)
    PatientProfile.objects.create(user=patient_user)
    doctor = DoctorProfile.objects.create(
        user=doctor_user,
        professional_name="Dr Schedule",
        specialty="General",
        medical_registration_number="REG-SCHEDULE",
        consultation_fee="600.00",
        verification_status=DoctorProfile.VerificationStatus.APPROVED,
    )
    chamber = Chamber.objects.create(
        doctor=doctor,
        chamber_name="Main",
        consultation_fee_override="750.00",
        active=True,
    )
    day = timezone.localtime(timezone.now() + timedelta(days=2)).date()
    AvailabilitySchedule.objects.create(
        doctor=doctor,
        chamber=chamber,
        weekday=day.weekday(),
        start_time="09:00",
        end_time="11:00",
        appointment_duration_minutes=30,
        break_start="10:00",
        break_end="10:30",
        active=True,
    )
    return doctor_user, patient_user, doctor, chamber, day


@pytest.mark.django_db
class TestAppointmentScheduling:
    def test_slots_exclude_break_and_are_future(self, appointment_setup):
        _, _, doctor, chamber, day = appointment_setup
        slots = generate_available_slots(
            doctor,
            chamber=chamber,
            start_date=day,
            end_date=day,
        )
        assert slots
        assert all(slot["start_at"] > timezone.now() for slot in slots)
        for slot in slots:
            local_time = timezone.localtime(slot["start_at"]).time()
            assert not (
                datetime.strptime("10:00", "%H:%M").time()
                <= local_time
                < datetime.strptime("10:30", "%H:%M").time()
            )

    def test_holiday_exception_returns_no_slots(self, appointment_setup):
        _, _, doctor, chamber, day = appointment_setup
        ScheduleException.objects.create(
            doctor=doctor,
            chamber=chamber,
            exception_type=ScheduleException.ExceptionType.HOLIDAY,
            date=day,
        )
        assert generate_available_slots(
            doctor,
            chamber=chamber,
            start_date=day,
            end_date=day,
        ) == []

    def test_patient_can_book_and_cannot_double_book(self, appointment_setup):
        _, patient, doctor, chamber, day = appointment_setup
        slots = generate_available_slots(
            doctor,
            chamber=chamber,
            start_date=day,
            end_date=day,
        )
        client = APIClient()
        client.force_authenticate(patient)
        payload = {
            "doctor": str(doctor.id),
            "chamber": str(chamber.id),
            "start_at": slots[0]["start_at"].isoformat(),
        }
        first = client.post("/api/v1/appointments/", payload, format="json")
        assert first.status_code == 201
        assert str(first.data["consultation_fee_snapshot"]) == "750.00"

        second = client.post("/api/v1/appointments/", payload, format="json")
        assert second.status_code == 400

        me = client.get("/api/v1/appointments/me/")
        assert me.status_code == 200
        assert me.data["count"] == 1

    def test_cancellation_requires_owner_and_reason(self, appointment_setup):
        _, patient, doctor, chamber, _ = appointment_setup
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            chamber=chamber,
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=3, minutes=30),
            consultation_fee_snapshot="750.00",
        )
        client = APIClient()
        client.force_authenticate(patient)
        cancelled = client.post(
            f"/api/v1/appointments/{appointment.id}/cancel/",
            {"reason": "Schedule conflict"},
            format="json",
        )
        assert cancelled.status_code == 200
        assert cancelled.data["status"] == "CANCELLED"

        other = create_user("other-patient@example.com", User.Role.PATIENT)
        PatientProfile.objects.create(user=other)
        client.force_authenticate(other)
        denied = client.post(
            f"/api/v1/appointments/{appointment.id}/cancel/",
            {"reason": "Unauthorized"},
            format="json",
        )
        assert denied.status_code == 403

    def test_assistant_can_confirm_associated_appointment(self, appointment_setup):
        _, patient, doctor, chamber, _ = appointment_setup
        assistant = create_user("schedule-assistant@example.com", User.Role.ASSISTANT)
        DoctorAssistant.objects.create(
            doctor=doctor,
            assistant=assistant,
            active=True,
        )
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            chamber=chamber,
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=3, minutes=30),
            consultation_fee_snapshot="750.00",
        )
        client = APIClient()
        client.force_authenticate(assistant)
        confirmed = client.post(
            f"/api/v1/appointments/{appointment.id}/confirm/",
            {},
            format="json",
        )
        assert confirmed.status_code == 200
        assert confirmed.data["status"] == "CONFIRMED"
