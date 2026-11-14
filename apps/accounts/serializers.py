"""Serializers for authentication, profiles, and password recovery."""
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    """Public representation of the authenticated user's profile."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "account_status",
            "profile_image",
            "created_at",
        )
        read_only_fields = ("id", "email", "role", "account_status", "created_at")


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "first_name", "last_name", "phone_number")

    def validate_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            **validated_data,
            role=User.Role.PATIENT,
            account_status=User.AccountStatus.ACTIVE,
        )


class LoginSerializer(TokenObtainPairSerializer):
    """Issue JWTs only to active, approved accounts."""

    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        email = attrs.get(self.username_field)
        password = attrs.get("password")
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active or user.account_status != User.AccountStatus.ACTIVE:
            raise serializers.ValidationError("This account cannot access the API.")
        attrs[self.username_field] = user.email
        return super().validate(attrs)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(
                value, self.context["request"].user
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        form = PasswordResetForm(data=self.validated_data)
        if form.is_valid():
            form.save(
                use_https=self.context["request"].is_secure(),
                request=self.context["request"],
                email_template_name="registration/password_reset_email.html",
            )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value

    def save(self):
        form = SetPasswordForm(
            user=self.context["user"],
            data={
                "new_password1": self.validated_data["new_password"],
                "new_password2": self.validated_data["new_password"],
            },
        )
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)
        form.save()
