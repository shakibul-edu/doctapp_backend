import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.doctors.models import DoctorAssistant, DoctorProfile
from apps.hospitals.models import Chamber, Hospital
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


@pytest.mark.django_db
class TestPatientProfiles:
    def test_patient_can_update_only_own_profile(self):
        owner = create_user("patient@example.com", User.Role.PATIENT)
        other = create_user("other@example.com", User.Role.PATIENT)
        owner_profile = PatientProfile.objects.create(user=owner)
        other_profile = PatientProfile.objects.create(user=other)
        client = APIClient()
        client.force_authenticate(owner)

        response = client.patch(
            "/api/v1/patients/me/",
            {"address": "Dhaka", "emergency_contact_phone": "+8801700000000"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["address"] == "Dhaka"

        response = client.get(f"/api/v1/patients/{other_profile.id}/")
        assert response.status_code == 403
        assert PatientProfile.objects.get(id=owner_profile.id).address == "Dhaka"


@pytest.mark.django_db
class TestDoctorProfiles:
    def test_pending_doctor_is_not_public_but_owner_can_access_me(self):
        doctor = create_user("doctor@example.com", User.Role.DOCTOR)
        profile = DoctorProfile.objects.create(
            user=doctor,
            professional_name="Dr Test",
            specialty="Cardiology",
            medical_registration_number="REG-1",
            verification_status=DoctorProfile.VerificationStatus.PENDING,
        )
        client = APIClient()
        client.force_authenticate(doctor)

        assert client.get("/api/v1/doctors/").status_code == 200
        assert client.get("/api/v1/doctors/").data["count"] == 0
        assert client.get(f"/api/v1/doctors/{profile.id}/").status_code == 404
        me = client.get("/api/v1/doctors/me/")
        assert me.status_code == 200

    def test_only_approved_doctors_appear_in_public_listing(self):
        approved = create_user("approved@example.com", User.Role.DOCTOR)
        rejected = create_user("rejected@example.com", User.Role.DOCTOR)
        approved_profile = DoctorProfile.objects.create(
            user=approved,
            professional_name="Approved Doctor",
            specialty="Dermatology",
            medical_registration_number="REG-APP",
            verification_status=DoctorProfile.VerificationStatus.APPROVED,
        )
        DoctorProfile.objects.create(
            user=rejected,
            professional_name="Rejected Doctor",
            specialty="Dermatology",
            medical_registration_number="REG-REJ",
            verification_status=DoctorProfile.VerificationStatus.REJECTED,
        )

        client = APIClient()
        listing = client.get("/api/v1/doctors/")
        ids = [item["id"] for item in listing.data["results"]]
        assert str(approved_profile.id) in ids


@pytest.mark.django_db
class TestAssistantRelationships:
    def test_assistant_authorization_and_revocation(self):
        doctor = create_user("owner@example.com", User.Role.DOCTOR)
        assistant = create_user("assistant@example.com", User.Role.ASSISTANT)
        profile = DoctorProfile.objects.create(
            user=doctor,
            professional_name="Owner Doctor",
            specialty="General",
            medical_registration_number="REG-OWNER",
            verification_status=DoctorProfile.VerificationStatus.APPROVED,
        )
        doctor_client = APIClient()
        doctor_client.force_authenticate(doctor)

        created = doctor_client.post(
            "/api/v1/doctors/me/assistants/",
            {
                "assistant_id": str(assistant.id),
                "active": True,
                "can_manage_chambers": True,
            },
            format="json",
        )
        assert created.status_code == 201
        relationship_id = created.data["id"]

        assistant_client = APIClient()
        assistant_client.force_authenticate(assistant)
        associated = assistant_client.get("/api/v1/assistants/me/doctors/")
        assert associated.status_code == 200
        assert str(profile.id) in [item["id"] for item in associated.data["results"]]

        deleted = doctor_client.delete(
            f"/api/v1/doctors/me/assistants/{relationship_id}/"
        )
        assert deleted.status_code == 204
        assert DoctorAssistant.objects.filter(id=relationship_id).count() == 0
        associated = assistant_client.get("/api/v1/assistants/me/doctors/")
        assert associated.data["count"] == 0


@pytest.mark.django_db
class TestHospitalAndChamberRelationships:
    def test_doctor_cannot_create_chamber_for_another_doctor(self):
        owner = create_user("hospital-owner@example.com", User.Role.DOCTOR)
        other = create_user("other-doctor@example.com", User.Role.DOCTOR)
        owner_profile = DoctorProfile.objects.create(
            user=owner,
            professional_name="Owner",
            specialty="Surgery",
            medical_registration_number="REG-H-1",
        )
        other_profile = DoctorProfile.objects.create(
            user=other,
            professional_name="Other",
            specialty="Surgery",
            medical_registration_number="REG-H-2",
        )
        hospital = Hospital.objects.create(name="Test Hospital", address="Dhaka")

        client = APIClient()
        client.force_authenticate(owner)
        response = client.post(
            "/api/v1/chambers/",
            {
                "doctor_id": str(other_profile.id),
                "hospital": str(hospital.id),
                "chamber_name": "Cross-account chamber",
                "address": "Dhaka",
            },
            format="json",
        )
        assert response.status_code in (400, 403)
        assert Chamber.objects.filter(doctor=owner_profile).count() == 0
