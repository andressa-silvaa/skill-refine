"""
Minimal tests for resume payload builders (contract preservation after extraction).
Ensures resume_payload and resume_detail_payload produce the same keys/shape as before refactor.
"""
from __future__ import annotations

from django.test import TestCase

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeEducation,
    ResumeExperience,
    ResumeExperienceBullet,
    ResumeLanguage,
    ResumeSkill,
    ResumeStatus,
    ResumeTag,
)
from apps.resumes.interfaces.api.payloads import resume_detail_payload, resume_payload


class ResumePayloadKeysTest(TestCase):
    """Ensure list-item payload has expected keys (no regression after extraction)."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="payload-list@test.local",
            defaults={"full_name": "Payload User", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user.id,
            name="Test Resume",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        ResumeTag.objects.create(resume=self.resume, label="tag1", position_index=0)
        ResumeSkill.objects.create(resume=self.resume, name="Python", position_index=0)

    def test_resume_payload_has_expected_keys(self):
        payload = resume_payload(self.resume)
        expected = {"id", "name", "updatedAt", "status", "score", "tags", "skills"}
        assert set(payload.keys()) == expected, f"Got keys: {set(payload.keys())}"
        assert payload["name"] == "Test Resume"
        assert payload["status"] == ResumeStatus.DRAFT
        assert isinstance(payload["tags"], list)
        assert isinstance(payload["skills"], list)

    def test_resume_payload_fallback_name(self):
        self.resume.name = ""
        self.resume.target_position = "Backend"
        self.resume.save()
        payload = resume_payload(self.resume)
        assert payload["name"] == "Backend"

    def test_resume_payload_omits_junk_skill_and_tag_labels(self):
        ResumeSkill.objects.create(resume=self.resume, name="l,o/", position_index=1)
        ResumeTag.objects.create(resume=self.resume, label="x,/", position_index=1)
        payload = resume_payload(self.resume)
        assert "l,o/" not in payload["skills"]
        assert "x,/" not in payload["tags"]
        assert "Python" in payload["skills"]
        assert "tag1" in payload["tags"]


class ResumeDetailPayloadKeysTest(TestCase):
    """Ensure detail/draft payload has expected keys and data shape (no regression)."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="payload-detail@test.local",
            defaults={"full_name": "Payload Detail User", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user.id,
            name="Detail Resume",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
            theme_id="classic-one-column",
        )
        ResumeContact.objects.create(
            resume=self.resume,
            full_name="Jane",
            email="j@test.local",
        )
        exp = ResumeExperience.objects.create(
            resume=self.resume, company="C", position="P", position_index=0
        )
        ResumeExperienceBullet.objects.create(experience=exp, content="Did X", position_index=0)
        ResumeEducation.objects.create(
            resume=self.resume, institution="U", course="CS", position_index=0
        )
        ResumeSkill.objects.create(resume=self.resume, name="Python", position_index=0)
        ResumeLanguage.objects.create(
            resume=self.resume, name="EN", level="intermediate", position_index=0
        )

    def test_resume_detail_payload_has_expected_top_keys(self):
        payload = resume_detail_payload(self.resume)
        expected_top = {"id", "name", "status", "updatedAt", "lastStep", "data"}
        assert set(payload.keys()) == expected_top, f"Got keys: {set(payload.keys())}"

    def test_resume_detail_payload_data_shape(self):
        payload = resume_detail_payload(self.resume)
        data = payload["data"]
        expected_data_keys = {
            "themeId",
            "themePaletteId",
            "themeAccentOverride",
            "themeSecondaryOverride",
            "targetPosition",
            "summary",
            "contact",
            "experiences",
            "educations",
            "skills",
            "languages",
        }
        assert set(data.keys()) == expected_data_keys, f"data keys: {set(data.keys())}"
        contact = data["contact"]
        assert set(contact.keys()) == {
            "fullName",
            "email",
            "phone",
            "city",
            "country",
            "linkedin",
            "portfolio",
            "github",
            "website",
        }
        assert data["contact"]["fullName"] == "Jane"
        assert data["contact"]["email"] == "j@test.local"
        assert len(data["experiences"]) == 1
        assert data["experiences"][0]["description"] == ["Did X"]
