from __future__ import annotations

from rest_framework import serializers

from apps.resumes.infrastructure.models import ResumeStatus

LIST_SORT_ALLOWED = ("recent", "oldest", "score", "name")


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


class ResumeListFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        choices=[value for value, _ in ResumeStatus.choices],
        error_messages={"invalid_choice": "Parâmetro status inválido."},
    )
    search = serializers.CharField(required=False, allow_blank=True)
    score_min = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
        error_messages={
            "invalid": "Parâmetro score_min inválido.",
            "min_value": "Parâmetro score_min deve ser entre 0 e 100.",
            "max_value": "Parâmetro score_min deve ser entre 0 e 100.",
        },
    )
    score_max = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        max_value=100,
        error_messages={
            "invalid": "Parâmetro score_max inválido.",
            "min_value": "Parâmetro score_max deve ser entre 0 e 100.",
            "max_value": "Parâmetro score_max deve ser entre 0 e 100.",
        },
    )
    include_no_score = serializers.BooleanField(required=False, default=False)
    updated_from = serializers.DateField(
        required=False,
        allow_null=True,
        error_messages={"invalid": "Parâmetro updated_from inválido (use YYYY-MM-DD)."},
    )
    updated_to = serializers.DateField(
        required=False,
        allow_null=True,
        error_messages={"invalid": "Parâmetro updated_to inválido (use YYYY-MM-DD)."},
    )
    sort = serializers.ChoiceField(
        required=False,
        default="recent",
        choices=list(LIST_SORT_ALLOWED),
        error_messages={
            "invalid_choice": f"Parâmetro sort inválido. Valores permitidos: {', '.join(sorted(LIST_SORT_ALLOWED))}."
        },
    )

    # Query params arrive as strings; an empty one means "not provided", same as the
    # request.query_params.get(...) or "" pattern this replaces — not an invalid value.
    _BLANK_MEANS_ABSENT = ("score_min", "score_max", "include_no_score", "updated_from", "updated_to", "sort")

    def to_internal_value(self, data):
        data = data.copy()
        for field in self._BLANK_MEANS_ABSENT:
            if data.get(field) == "":
                del data[field]
        return super().to_internal_value(data)

    def validate(self, attrs):
        score_min = attrs.get("score_min")
        score_max = attrs.get("score_max")
        if score_min is not None and score_max is not None and score_min > score_max:
            raise serializers.ValidationError("Parâmetro score_min não pode ser maior que score_max.")

        updated_from = attrs.get("updated_from")
        updated_to = attrs.get("updated_to")
        if updated_from and updated_to and updated_from > updated_to:
            raise serializers.ValidationError("Parâmetro updated_from não pode ser maior que updated_to.")

        return attrs

