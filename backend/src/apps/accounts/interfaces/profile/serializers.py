from __future__ import annotations

from rest_framework import serializers


ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2MB


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField()

    def validate_avatar(self, f):
        size = int(getattr(f, "size", 0) or 0)
        if size <= 0:
            raise serializers.ValidationError("Arquivo inválido.")
        if size > MAX_AVATAR_BYTES:
            raise serializers.ValidationError("Arquivo muito grande. Tamanho máximo: 2MB.")

        content_type = (getattr(f, "content_type", "") or "").strip().lower()
        if content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
            raise serializers.ValidationError("Formato inválido. Envie JPG, PNG ou WEBP.")
        return f


class ProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(min_length=2, max_length=255, required=False)


class PreferencesSerializer(serializers.Serializer):
    email_notifications_enabled = serializers.BooleanField(required=False)
    language = serializers.ChoiceField(choices=["pt-BR", "en-US", "es-ES"], required=False)
    theme = serializers.ChoiceField(choices=["light", "dark"], required=False)
    accent_color = serializers.ChoiceField(choices=["pink", "purple", "blue", "green", "orange"], required=False)