from __future__ import annotations

from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(min_length=1, max_length=255)
    birth_date = serializers.DateField(required=False, allow_null=True)
    password = serializers.CharField(min_length=8, write_only=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=1, write_only=True)


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField(min_length=1, write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.RegexField(regex=r"^\d{5}$")


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reset_token = serializers.CharField(min_length=10, write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class EmailConfirmationRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailConfirmationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(min_length=10, write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(min_length=1, write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_new_password = serializers.CharField(min_length=1, write_only=True)


class AuthUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    email_verified = serializers.BooleanField()


class AuthResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    user = AuthUserSerializer()


class RefreshResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()


