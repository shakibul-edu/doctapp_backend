from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions

from apps.accounts.permissions import IsAccountActive
from apps.doctors.models import DoctorAssistant
from .models import Chamber, Hospital
from .serializers import ChamberSerializer, HospitalSerializer


def _get_authorized_doctor(request):
    if request.user.role == "DOCTOR":
        return getattr(request.user, "doctor_profile", None)
    doctor_id = request.data.get("doctor_id") or request.query_params.get("doctor")
    if not doctor_id:
        return None
    relationship = DoctorAssistant.objects.filter(
        assistant=request.user,
        active=True,
        can_manage_chambers=True,
        doctor_id=doctor_id,
    ).select_related("doctor").first()
    return relationship.doctor if relationship else None


class IsActiveAuthorizedChamberAssistant(IsAccountActive):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.user.role == "DOCTOR":
            profile = getattr(request.user, "doctor_profile", None)
            if profile is None:
                return False
            submitted_doctor_id = request.data.get("doctor_id")
            return not submitted_doctor_id or str(submitted_doctor_id) == str(profile.id)
        chamber_id = getattr(view, "kwargs", {}).get("id")
        if chamber_id:
            return DoctorAssistant.objects.filter(
                assistant=request.user,
                active=True,
                can_manage_chambers=True,
                doctor__chambers__id=chamber_id,
            ).exists()
        doctor_id = request.data.get("doctor_id") or request.query_params.get("doctor")
        if not doctor_id:
            return False
        return DoctorAssistant.objects.filter(
            assistant=request.user,
            active=True,
            can_manage_chambers=True,
            doctor_id=doctor_id,
        ).exists()


class HospitalListView(generics.ListCreateAPIView):
    queryset = Hospital.objects.filter(active=True)
    serializer_class = HospitalSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("name", "description", "address")
    ordering_fields = ("name", "created_at")
    filterset_fields = ("active",)

    def get_permissions(self):
        if self.request.method == "POST":
            return (permissions.IsAdminUser(),)
        return (permissions.AllowAny(),)


class HospitalDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    lookup_field = "id"

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return (permissions.AllowAny(),)
        return (permissions.IsAdminUser(),)


class ChamberListCreateView(generics.ListCreateAPIView):
    queryset = Chamber.objects.filter(active=True).select_related("doctor", "hospital")
    serializer_class = ChamberSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("chamber_name", "address", "doctor__professional_name")
    ordering_fields = ("chamber_name", "consultation_fee_override", "created_at")
    filterset_fields = ("doctor", "hospital", "active")

    def get_permissions(self):
        if self.request.method == "POST":
            return (IsActiveAuthorizedChamberAssistant(),)
        return (permissions.AllowAny(),)

    def perform_create(self, serializer):
        doctor = _get_authorized_doctor(self.request)
        serializer.save(doctor=doctor)


class ChamberDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Chamber.objects.select_related("doctor", "hospital")
    serializer_class = ChamberSerializer
    lookup_field = "id"

    def get_permissions(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return (permissions.AllowAny(),)
        return (IsActiveAuthorizedChamberAssistant(),)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.method in ("PATCH", "PUT", "DELETE"):
            if self.request.user.role == "DOCTOR":
                doctor = getattr(self.request.user, "doctor_profile", None)
                return qs.filter(doctor=doctor) if doctor else qs.none()
            doctor_ids = DoctorAssistant.objects.filter(
                assistant=self.request.user,
                active=True,
                can_manage_chambers=True,
            ).values("doctor_id")
            return qs.filter(doctor_id__in=doctor_ids)
        return qs
