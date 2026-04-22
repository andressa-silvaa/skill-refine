"""Unit tests for the server-side peppered Argon2id password hasher."""
from __future__ import annotations

import warnings

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from apps.accounts.infrastructure.password_hasher import Argon2PasswordHasher
from shared.auth.pepper_password_hasher import (
    PEPPER_PREFIX,
    PepperedArgon2PasswordHasher,
    resolve_pepper_or_raise,
)


PASSWORD = "S3cur3-Pass!"


class PepperedHasherEncodeTests(SimpleTestCase):
    def test_hash_is_tagged_with_prefix(self) -> None:
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        encoded = hasher.hash(PASSWORD)
        self.assertTrue(encoded.startswith(PEPPER_PREFIX))
        self.assertIn("$argon2", encoded)

    def test_pepper_influences_output_for_same_password(self) -> None:
        peppered = PepperedArgon2PasswordHasher(pepper="pepper-a").hash(PASSWORD)
        unpeppered = Argon2PasswordHasher().hash(PASSWORD)
        self.assertNotEqual(peppered, unpeppered)
        self.assertFalse(unpeppered.startswith(PEPPER_PREFIX))

    def test_two_calls_produce_different_hashes_due_to_salt(self) -> None:
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        self.assertNotEqual(hasher.hash(PASSWORD), hasher.hash(PASSWORD))


class PepperedHasherVerifyTests(SimpleTestCase):
    def test_verify_with_correct_pepper_and_password(self) -> None:
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        encoded = hasher.hash(PASSWORD)
        self.assertTrue(hasher.verify(encoded, PASSWORD))

    def test_verify_with_wrong_password_returns_false(self) -> None:
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        encoded = hasher.hash(PASSWORD)
        self.assertFalse(hasher.verify(encoded, PASSWORD + "x"))

    def test_verify_with_wrong_pepper_returns_false(self) -> None:
        encoded = PepperedArgon2PasswordHasher(pepper="pepper-a").hash(PASSWORD)
        other = PepperedArgon2PasswordHasher(pepper="pepper-b")
        self.assertFalse(other.verify(encoded, PASSWORD))

    def test_verify_accepts_legacy_unpeppered_hash(self) -> None:
        legacy = Argon2PasswordHasher().hash(PASSWORD)
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        self.assertTrue(hasher.verify(legacy, PASSWORD))
        self.assertFalse(hasher.verify(legacy, PASSWORD + "x"))

    def test_verify_handles_empty_and_malformed_input(self) -> None:
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        self.assertFalse(hasher.verify("", PASSWORD))
        self.assertFalse(hasher.verify("peppered$v1$not-an-argon2-hash", PASSWORD))
        self.assertFalse(hasher.verify("not-an-argon2-hash-at-all", PASSWORD))


class PepperedHasherNeedsRehashTests(SimpleTestCase):
    def test_legacy_hash_needs_rehash(self) -> None:
        legacy = Argon2PasswordHasher().hash(PASSWORD)
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        self.assertTrue(hasher.needs_rehash(legacy))

    def test_fresh_peppered_hash_does_not_need_rehash(self) -> None:
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        self.assertFalse(hasher.needs_rehash(hasher.hash(PASSWORD)))

    def test_empty_input_does_not_request_rehash(self) -> None:
        hasher = PepperedArgon2PasswordHasher(pepper="pepper-a")
        self.assertFalse(hasher.needs_rehash(""))


class PepperedHasherConstructionTests(SimpleTestCase):
    def test_empty_pepper_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PepperedArgon2PasswordHasher(pepper="")


class ResolvePepperTests(SimpleTestCase):
    def test_production_missing_pepper_raises(self) -> None:
        with self.assertRaises(ImproperlyConfigured):
            resolve_pepper_or_raise(debug=False, raw="")
        with self.assertRaises(ImproperlyConfigured):
            resolve_pepper_or_raise(debug=False, raw=None)

    def test_production_with_pepper_returns_value(self) -> None:
        self.assertEqual(
            resolve_pepper_or_raise(debug=False, raw="prod-pepper"),
            "prod-pepper",
        )

    def test_dev_missing_pepper_falls_back_with_warning(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = resolve_pepper_or_raise(debug=True, raw="")
        self.assertTrue(value)
        self.assertTrue(any("PASSWORD_HASH_PEPPER" in str(w.message) for w in caught))
