import pytest

from apps.accounts.models import User
from apps.doctors.models import DoctorProfile
from apps.hospitals.models import Chamber, Hospital


def create_approved_doctor(email, specialty="Cardiology"):
    user = User.objects.create_user(
        email=email,
        password="SecurePass123!",
        first_name="Test",
        last_name="Doctor",
        role=User.Role.DOCTOR,
        account_status=User.AccountStatus.ACTIVE,
    )
    return DoctorProfile.objects.create(
        user=user,
        professional_name=f"Dr. {email}",
        specialty=        specialty,
        qualifications="MD",
        experience_years=8,
        consultation_fee="50.00",
        medical_registration_number=f"REG-{email}",
        verification_status=DoctorProfile.VerificationStatus.APPROVED,
    )


@pytest.mark.django_db
class TestDoctorFilters:
    def test_filter_options_return_specializations_and_hospitals(self, client):
        doctor = create_approved_doctor("cardio@example.com")
        hospital = Hospital.objects.create(
            name="Example Hospital",
            address="Main Street",
            active=True,
        )
        Chamber.objects.create(
            doctor=doctor,
            hospital=hospital,
            chamber_name="Main Chamber",
            active=True,
        )

        response = client.get("/api/v1/doctors/filter-options/")

        assert response.status_code == 200
        assert response.json()["specializations"] == [
            {"id": "Cardiology", "name": "Cardiology"}
        ]
        assert response.json()["hospitals"] == [
            {"id": str(hospital.id), "name": "Example Hospital"}
        ]

    def test_specialization_alias_filter_is_case_insensitive(self, client):
        doctor = create_approved_doctor("cardio@example.com")
        create_approved_doctor("neuro@example.com", "Neurology")

        response = client.get(
            "/api/v1/doctors/",
            {"specialization": "cardiology"},
        )

        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["results"][0]["id"] == str(doctor.id)

    def test_hospital_filter_accepts_uuid_and_returns_hospital_details(self, client):
        doctor = create_approved_doctor("cardio@example.com")
        hospital = Hospital.objects.create(
            name="Example Hospital",
            address="Main Street",
            active=True,
        )
        Chamber.objects.create(
            doctor=doctor,
            hospital=hospital,
            chamber_name="Main Chamber",
            address="Main Street",
            active=True,
        )

        response = client.get(
            "/api/v1/doctors/",
            {"hospital": str(hospital.id), "page_size": 10},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        doctor_data = payload["results"][0]
        assert doctor_data["specialization"] == {
            "id": "Cardiology",
            "name": "Cardiology",
        }
        assert doctor_data["hospitals"] == [
            {"id": str(hospital.id), "name": "Example Hospital"}
        ]
        assert doctor_data["verification_status"] == "APPROVED"

    def test_search_matches_hospital_name(self, client):
        doctor = create_approved_doctor("cardio@example.com")
        hospital = Hospital.objects.create(
            name="City Medical Centre",
            address="Main Street",
            active=True,
        )
        Chamber.objects.create(
            doctor=doctor,
            hospital=hospital,
            chamber_name="Main Chamber",
            active=True,
        )

        response = client.get("/api/v1/doctors/", {"search": "city medical"})

        assert response.status_code == 200
        assert response.json()["count"] == 1
