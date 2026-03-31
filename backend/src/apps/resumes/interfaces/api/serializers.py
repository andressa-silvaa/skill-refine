from __future__ import annotations

from rest_framework import serializers


class ResumeContactSerializer(serializers.Serializer):
    fullName = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=160)
    email = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=254)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=32)
    city = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=120)
    country = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=120)
    linkedin = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    portfolio = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    github = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    website = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)


class ResumeExperienceSerializer(serializers.Serializer):
    company = serializers.CharField(required=False, allow_blank=True, max_length=180)
    position = serializers.CharField(required=False, allow_blank=True, max_length=160)
    startDate = serializers.CharField(required=False, allow_blank=True, max_length=10)
    endDate = serializers.CharField(required=False, allow_blank=True, max_length=10)
    isCurrent = serializers.BooleanField(required=False)
    description = serializers.ListField(child=serializers.CharField(allow_blank=True), required=False)


class ResumeEducationSerializer(serializers.Serializer):
    institution = serializers.CharField(required=False, allow_blank=True, max_length=180)
    course = serializers.CharField(required=False, allow_blank=True, max_length=180)
    degree = serializers.CharField(required=False, allow_blank=True, max_length=120)
    startDate = serializers.CharField(required=False, allow_blank=True, max_length=10)
    endDate = serializers.CharField(required=False, allow_blank=True, max_length=10)
    status = serializers.ChoiceField(required=False, choices=["completed", "in_progress"])


class ResumeSkillSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    level = serializers.ChoiceField(required=False, allow_null=True, choices=["beginner", "intermediate", "advanced", "expert"])


class ResumeLanguageSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=80)
    level = serializers.ChoiceField(required=False, choices=["basic", "intermediate", "advanced", "fluent", "native"])


class ResumeDraftSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=160)
    status = serializers.ChoiceField(required=False, choices=["draft", "complete", "analyzing"])
    lastStep = serializers.CharField(required=False, allow_blank=True, max_length=32)
    score = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=100)
    themeId = serializers.CharField(required=False, allow_blank=True, max_length=64)
    themePaletteId = serializers.CharField(required=False, allow_blank=True, max_length=64)
    themeAccentOverride = serializers.CharField(required=False, allow_blank=True, max_length=16)
    themeSecondaryOverride = serializers.CharField(required=False, allow_blank=True, max_length=16)
    targetPosition = serializers.CharField(required=False, allow_blank=True, max_length=160)
    summary = serializers.CharField(required=False, allow_blank=True)
    contact = ResumeContactSerializer(required=False, allow_null=True)
    experiences = ResumeExperienceSerializer(many=True, required=False)
    educations = ResumeEducationSerializer(many=True, required=False)
    skills = ResumeSkillSerializer(many=True, required=False)
    languages = ResumeLanguageSerializer(many=True, required=False)

