import uuid

from django.db import transaction
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.accounts.permissions import IsAssistant, IsDoctor
from .models import DoctorAssistant, DoctorProfile
from .serializers import (
    DoctorAssistantCreateSerializer,
    DoctorAssistantSerializer,
    DoctorPublicSerializer,
    DoctorWriteSerializer,
)


class DoctorListView(generics.ListAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DoctorPublicSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "professional_name",
        "specialty",
        "qualifications",
        "languages",
        "chambers__chamber_name",
        "chambers__address",
        "chambers__hospital__name",
    )
    ordering_fields = (
        "professional_name", "experience_years", "consultation_fee", "created_at",
    )
    filterset_fields = ("experience_years", "consultation_fee")

    def get_queryset(self):
        qs = DoctorProfile.objects.filter(
            verification_status=DoctorProfile.VerificationStatus.APPROVED
        ).prefetch_related("chambers")
        specialization_values = self._get_query_values(("specialization", "specialty"))
        if specialization_values:
            specialization_query = Q()
            for value in specialization_values:
                specialization_query |= Q(specialty__iexact=value)
            qs = qs.filter(specialization_query)

        hospital_values = self._get_query_values(("hospital",))
        if hospital_values:
            valid_hospital_ids = []
            for hospital_value in hospital_values:
                try:
                    valid_hospital_ids.append(uuid.UUID(hospital_value))
                except (ValueError, AttributeError):
                    continue
            if valid_hospital_ids:
                qs = qs.filter(
                    chambers__hospital_id__in=valid_hospital_ids,
                    chambers__active=True,
                ).distinct()
            else:
                qs = qs.none()
        location = self.request.query_params.get("location")
        if location:
            qs = qs.filter(chambers__address__icontains=location, chambers__active=True).distinct()
        return qs

    def _get_query_values(self, names):
        values = []
        for name in names:
            for raw_value in self.request.query_params.getlist(name):
                values.extend(
                    value.strip()
                    for value in raw_value.split(",")
                    if value.strip()
                )
        return list(dict.fromkeys(values))


class DoctorSpecializationListView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        specialties = (
            DoctorProfile.objects.filter(
                verification_status=DoctorProfile.VerificationStatus.APPROVED,
            )
            .exclude(specialty="")
            .values_list("specialty", flat=True)
            .distinct()
            .order_by("specialty")
        )

        normalized = {}
        for specialty in specialties:
            key = specialty.strip().casefold()
            if key:
                normalized.setdefault(key, specialty.strip())

        specializations = [
            {"id": specialty, "name": specialty}
            for specialty in normalized.values()
        ]
        return Response(specializations)


class DoctorFilterOptionsView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        specialization_view = DoctorSpecializationListView()
        specialization_response = specialization_view.get(request)

        from apps.hospitals.models import Hospital

        hospitals = Hospital.objects.filter(active=True).order_by("name").values("id", "name")
        hospital_options = [
            {"id": str(hospital["id"]), "name": hospital["name"]}
            for hospital in hospitals
        ]

        return Response(
            {
                "specializations": specialization_response.data,
                "hospitals": hospital_options,
            }
        )


class DoctorDetailView(generics.RetrieveAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DoctorPublicSerializer
    lookup_field = "id"

    def get_queryset(self):
        return DoctorProfile.objects.filter(
            verification_status=DoctorProfile.VerificationStatus.APPROVED
        ).prefetch_related("chambers")


class DoctorMeView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsDoctor,)

    def get_object(self):
        profile, _ = DoctorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                "professional_name": self.request.user.full_name,
                "specialty": "",
                "medical_registration_number": f"PENDING-{self.request.user.id}",
            },
        )
        return profile

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return DoctorWriteSerializer
        return DoctorPublicSerializer


class DoctorAssistantListCreateView(generics.ListCreateAPIView):
    permission_classes = (IsDoctor,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return DoctorAssistantCreateSerializer
        return DoctorAssistantSerializer

    def get_queryset(self):
        profile = getattr(self.request.user, "doctor_profile", None)
        if profile is None:
            return DoctorAssistant.objects.none()
        return DoctorAssistant.objects.filter(doctor=profile).select_related("assistant")

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        profile = getattr(request.user, "doctor_profile", None)
        if profile is None:
            return Response(
                {"detail": "Create your doctor profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assistant = serializer.validated_data["assistant_id"]
        relationship, created = DoctorAssistant.objects.update_or_create(
            doctor=profile,
            assistant=assistant,
            defaults={
                "active": serializer.validated_data["active"],
                "can_view_patient_profiles": serializer.validated_data["can_view_patient_profiles"],
                "can_manage_chambers": serializer.validated_data["can_manage_chambers"],
            },
        )
        output = DoctorAssistantSerializer(relationship, context={"request": request})
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class DoctorAssistantDeleteView(generics.DestroyAPIView):
    permission_classes = (IsDoctor,)
    serializer_class = DoctorAssistantSerializer
    lookup_field = "id"

    def get_queryset(self):
        profile = getattr(self.request.user, "doctor_profile", None)
        if profile is None:
            return DoctorAssistant.objects.none()
        return DoctorAssistant.objects.filter(doctor=profile)


class AssistantDoctorsView(generics.ListAPIView):
    permission_classes = (IsAssistant,)
    serializer_class = DoctorPublicSerializer

    def get_queryset(self):
        doctor_ids = DoctorAssistant.objects.filter(
            assistant=self.request.user,
            active=True,
        ).values("doctor_id")
        return DoctorProfile.objects.filter(id__in=doctor_ids).prefetch_related("chambers")
