"""Integration tests for the rehash-on-login migration from legacy to peppered hashes."""
from __future__ import annotations

from datetime import UTC, datetime

from django.test import TestCase, override_settings

from apps.accounts.application.use_cases import (
    AccountsAuthConfig,
    login_with_password,
)
from apps.accounts.infrastructure.models import User, UserPassword
from apps.accounts.infrastructure.password_hasher import Argon2PasswordHasher
from apps.accounts.infrastructure.repositories import (
    OrmAuthIdentityRepository,
    OrmPasswordRepository,
    OrmSessionRepository,
    OrmUserRepository,
)
from apps.audit.infrastructure.logger import OrmAuditLogger
from shared.auth.pepper_password_hasher import (
    PEPPER_PREFIX,
    PepperedArgon2PasswordHasher,
)

PASSWORD = "MyStrong!Pass123"
PEPPER = "unit-test-pepper"


def _build_cfg() -> AccountsAuthConfig:
    return AccountsAuthConfig(
        jwt_secret="test-secret",
        jwt_issuer="skill-refine-test",
        jwt_access_ttl_minutes=15,
        refresh_token_pepper="refresh-pepper",
        refresh_ttl_days=30,
        password_reset_code_ttl_minutes=10,
        password_reset_grant_ttl_minutes=15,
        password_reset_code_pepper="reset-pepper",
        email_confirmation_token_ttl_hours=24,
        email_confirmation_token_pepper="confirm-pepper",
        frontend_url="http://localhost:3000",
        google_oauth_client_id="",
    )


@override_settings(PASSWORD_HASH_PEPPER=PEPPER)
class LoginRehashTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            email="rehash@test.local",
            full_name="Rehash User",
            status="active",
            email_verified_at=datetime.now(UTC),
        )
        legacy_hash = Argon2PasswordHasher().hash(PASSWORD)
        UserPassword.objects.create(
            user=self.user,
            password_hash=legacy_hash,
            password_updated_at=datetime.now(UTC),
        )
        self.legacy_hash = legacy_hash

    def _login(self, password: str):
        hasher = PepperedArgon2PasswordHasher(pepper=PEPPER)
        return login_with_password(
            cfg=_build_cfg(),
            users=OrmUserRepository(),
            passwords=OrmPasswordRepository(),
            identities=OrmAuthIdentityRepository(),
            sessions=OrmSessionRepository(),
            password_hasher=hasher,
            audit=OrmAuditLogger(),
            email=self.user.email,
            password=password,
            ip="127.0.0.1",
            user_agent="test",
        )

    def test_legacy_hash_login_succeeds_and_rehashes_to_peppered(self) -> None:
        result, refresh_cookie = self._login(PASSWORD)

        self.assertTrue(result.access_token)
        self.assertIn(".", refresh_cookie)

        updated = UserPassword.objects.get(user=self.user).password_hash
        self.assertNotEqual(updated, self.legacy_hash)
        self.assertTrue(updated.startswith(PEPPER_PREFIX))
        self.assertTrue(
            PepperedArgon2PasswordHasher(pepper=PEPPER).verify(updated, PASSWORD)
        )

    def test_wrong_password_does_not_rehash(self) -> None:
        from apps.accounts.domain.errors import InvalidCredentials

        with self.assertRaises(InvalidCredentials):
            self._login(PASSWORD + "x")

        stored = UserPassword.objects.get(user=self.user).password_hash
        self.assertEqual(stored, self.legacy_hash)

    def test_second_login_does_not_rehash_again(self) -> None:
        self._login(PASSWORD)
        hash_after_first = UserPassword.objects.get(user=self.user).password_hash

        self._login(PASSWORD)
        hash_after_second = UserPassword.objects.get(user=self.user).password_hash

        self.assertEqual(hash_after_first, hash_after_second)
