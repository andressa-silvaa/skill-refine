"""
Tests for version history: list, get, restore, and version creation on save.
"""
from __future__ import annotations

from django.test import TestCase

from apps.accounts.infrastructure.models import User
from apps.resumes.infrastructure.models import (
    Resume,
    ResumeContact,
    ResumeStatus,
    ResumeVersion,
)
from apps.resumes.interfaces.api.services import create_resume_draft, update_resume_draft
from apps.resumes.interfaces.api.version_services import (
    get_version_by_id,
    list_versions,
    maybe_create_version_after_save,
    restore_version,
)


class VersionCreationTest(TestCase):
    """Version is created on first save and on update when content changes."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="version-create@test.local",
            defaults={"full_name": "Version User", "status": "active"},
        )

    def test_first_save_creates_version(self):
        data = {
            "name": "My Resume",
            "targetPosition": "Dev",
            "contact": {"fullName": "A", "email": "a@test.local"},
        }
        resume = create_resume_draft(str(self.user.id), data)
        maybe_create_version_after_save(str(self.user.id), str(resume.id))
        versions = list(ResumeVersion.objects.filter(resume_id=resume.id).order_by("version_number"))
        self.assertEqual(len(versions), 1)
        self.assertTrue(versions[0].is_current)
        self.assertEqual(versions[0].version_number, 1)
        self.assertIn("Versão inicial", versions[0].change_summary_json)

    def test_update_with_changes_creates_new_version(self):
        data = {
            "name": "V1",
            "targetPosition": "Dev",
            "contact": {"fullName": "A", "email": "a@test.local"},
        }
        resume = create_resume_draft(str(self.user.id), data)
        maybe_create_version_after_save(str(self.user.id), str(resume.id))
        update_resume_draft(str(self.user.id), str(resume.id), {"targetPosition": "Senior Dev"})
        maybe_create_version_after_save(str(self.user.id), str(resume.id))
        versions = list(ResumeVersion.objects.filter(resume_id=resume.id).order_by("version_number"))
        self.assertEqual(len(versions), 2)
        self.assertFalse(versions[0].is_current)
        self.assertTrue(versions[1].is_current)
        self.assertEqual(versions[1].version_number, 2)


class VersionListTest(TestCase):
    """List versions for user, optionally filtered by resume."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="version-list@test.local",
            defaults={"full_name": "List User", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user.id,
            name="R1",
            status=ResumeStatus.DRAFT,
            target_position="Dev",
        )
        ResumeVersion.objects.create(
            resume=self.resume,
            user_id=self.user.id,
            version_number=1,
            is_current=True,
            snapshot_json={"targetPosition": "Dev"},
            change_summary_json=["Initial"],
        )

    def test_list_all_versions_for_user(self):
        qs = list_versions(str(self.user.id))
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().resume_id, self.resume.id)

    def test_list_filtered_by_resume(self):
        qs = list_versions(str(self.user.id), resume_id=str(self.resume.id))
        self.assertEqual(qs.count(), 1)
        qs_other = list_versions(str(self.user.id), resume_id="00000000-0000-0000-0000-000000000000")
        self.assertEqual(qs_other.count(), 0)


class VersionRestoreTest(TestCase):
    """Restore applies snapshot and creates new version."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="version-restore@test.local",
            defaults={"full_name": "Restore User", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user.id,
            name="R1",
            status=ResumeStatus.DRAFT,
            target_position="Current",
            summary="Now",
        )
        ResumeContact.objects.update_or_create(
            resume=self.resume,
            defaults={"full_name": "Current", "email": "c@test.local"},
        )
        self.version = ResumeVersion.objects.create(
            resume=self.resume,
            user_id=self.user.id,
            version_number=1,
            is_current=True,
            snapshot_json={
                "targetPosition": "Old",
                "summary": "Old summary",
                "themeId": "classic-one-column",
                "contact": {"fullName": "Old", "email": "old@test.local"},
                "experiences": [],
                "educations": [],
                "skills": [],
                "languages": [],
            },
            change_summary_json=["Initial"],
        )

    def test_restore_updates_resume_and_creates_version(self):
        result = restore_version(str(self.user.id), str(self.resume.id), str(self.version.id))
        self.assertIsNotNone(result)
        self.resume.refresh_from_db()
        self.assertEqual(self.resume.target_position, "Old")
        self.assertEqual(self.resume.summary, "Old summary")
        contact = ResumeContact.objects.get(resume_id=self.resume.id)
        self.assertEqual(contact.full_name, "Old")
        versions = list(ResumeVersion.objects.filter(resume_id=self.resume.id).order_by("-version_number"))
        self.assertEqual(versions[0].version_number, 2)
        self.assertTrue(versions[0].is_current)
        self.assertIn("Versão restaurada", versions[0].change_summary_json)

    def test_restore_wrong_user_returns_none(self):
        other_user, _ = User.objects.get_or_create(
            email="other-restore@test.local",
            defaults={"full_name": "Other", "status": "active"},
        )
        result = restore_version(str(other_user.id), str(self.resume.id), str(self.version.id))
        self.assertIsNone(result)


class VersionGetTest(TestCase):
    """Get single version by id; ownership enforced."""

    def setUp(self):
        self.user, _ = User.objects.get_or_create(
            email="version-get@test.local",
            defaults={"full_name": "Get User", "status": "active"},
        )
        self.resume = Resume.objects.create(
            user_id=self.user.id, name="R1", status=ResumeStatus.DRAFT
        )
        self.version = ResumeVersion.objects.create(
            resume=self.resume,
            user_id=self.user.id,
            version_number=1,
            is_current=True,
            snapshot_json={},
            change_summary_json=[],
        )

    def test_get_version_returns_when_owned(self):
        v = get_version_by_id(str(self.user.id), str(self.resume.id), str(self.version.id))
        self.assertIsNotNone(v)
        self.assertEqual(v.id, self.version.id)

    def test_get_version_returns_none_for_wrong_resume(self):
        v = get_version_by_id(
            str(self.user.id),
            "00000000-0000-0000-0000-000000000000",
            str(self.version.id),
        )
        self.assertIsNone(v)
