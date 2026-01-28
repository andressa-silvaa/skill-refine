from __future__ import annotations

from rest_framework import serializers


class RewriteOptionsSerializer(serializers.Serializer):
    language = serializers.CharField(required=False, allow_blank=True)
    tone = serializers.CharField(required=False, allow_blank=True)
    maxLength = serializers.IntegerField(required=False, min_value=1, max_value=2000)


class RewriteRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000)
    context = serializers.CharField(max_length=128)
    options = RewriteOptionsSerializer(required=False)

