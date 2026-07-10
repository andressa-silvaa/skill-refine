"""Integration tests for the rehash-on-login upgrade when Argon2id params change."""
from __future__ import annotations

from datetime import UTC, datetime

from argon2 import PasswordHasher as _Argon2PasswordHasher
from django.test import TestCase

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
from shared.utils.normalization import normalize_password

PASSWORD = "MyStrong!Pass123"


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


class LoginRehashTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create(
            email="rehash@test.local",
            full_name="Rehash User",
            status="active",
            email_verified_at=datetime.now(UTC),
        )
        weak = _Argon2PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
        outdated_hash = weak.hash(normalize_password(PASSWORD))
        UserPassword.objects.create(
            user=self.user,
            password_hash=outdated_hash,
            password_updated_at=datetime.now(UTC),
        )
        self.outdated_hash = outdated_hash

    def _login(self, password: str):
        return login_with_password(
            cfg=_build_cfg(),
            users=OrmUserRepository(),
            passwords=OrmPasswordRepository(),
            identities=OrmAuthIdentityRepository(),
            sessions=OrmSessionRepository(),
            password_hasher=Argon2PasswordHasher(),
            audit=OrmAuditLogger(),
            email=self.user.email,
            password=password,
            ip="127.0.0.1",
            user_agent="test",
        )

    def test_outdated_hash_login_succeeds_and_rehashes(self) -> None:
        result, refresh_cookie = self._login(PASSWORD)

        self.assertTrue(result.access_token)
        self.assertIn(".", refresh_cookie)

        updated = UserPassword.objects.get(user=self.user).password_hash
        self.assertNotEqual(updated, self.outdated_hash)
        self.assertFalse(Argon2PasswordHasher().needs_rehash(updated))
        self.assertTrue(
            Argon2PasswordHasher().verify(updated, normalize_password(PASSWORD))
        )

    def test_wrong_password_does_not_rehash(self) -> None:
        from apps.accounts.domain.errors import InvalidCredentials

        with self.assertRaises(InvalidCredentials):
            self._login(PASSWORD + "x")

        stored = UserPassword.objects.get(user=self.user).password_hash
        self.assertEqual(stored, self.outdated_hash)

    def test_second_login_does_not_rehash_again(self) -> None:
        self._login(PASSWORD)
        hash_after_first = UserPassword.objects.get(user=self.user).password_hash

        self._login(PASSWORD)
        hash_after_second = UserPassword.objects.get(user=self.user).password_hash

        self.assertEqual(hash_after_first, hash_after_second)
