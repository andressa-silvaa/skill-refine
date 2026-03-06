"""
Tests for shared.api.responses (error contract).
Ensures payload shape and status codes remain identical after centralization.
"""
from __future__ import annotations

from django.test import TestCase
from rest_framework import status

from shared.api.responses import (
    canonical_error_code,
    error_response,
    extract_error_message,
    field_error_response,
    serializer_field_errors,
)


class TestCanonicalErrorCode(TestCase):
    def test_normalization_cases(self):
        cases = [
            ("  invalid_credentials  ", "INVALID_CREDENTIALS"),
            ("not_found", "NOT_FOUND"),
            ("", ""),
            (None, ""),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                assert canonical_error_code(raw) == expected


class TestErrorResponse(TestCase):
    def test_payload_shape_and_status(self):
        resp = error_response("not_found", "Currículo não encontrado.", status.HTTP_404_NOT_FOUND)
        assert resp.status_code == 404
        data = resp.data
        assert "error" in data
        assert data["error"]["code"] == "not_found"
        assert data["error"]["error_code"] == "NOT_FOUND"
        assert data["error"]["message"] == "Currículo não encontrado."
        assert data["error_code"] == "NOT_FOUND"
        assert data["message"] == "Currículo não encontrado."

    def test_no_extra_keys(self):
        resp = error_response("unauthorized", "Não autenticado.", status.HTTP_401_UNAUTHORIZED)
        assert set(resp.data.keys()) == {"error", "error_code", "message"}


class TestFieldErrorResponse(TestCase):
    def test_payload_shape_and_status(self):
        resp = field_error_response(
            "validation_error",
            "Dados inválidos.",
            {"targetPosition": "Informe o cargo alvo."},
            status.HTTP_400_BAD_REQUEST,
        )
        assert resp.status_code == 400
        data = resp.data
        assert data["error"]["code"] == "validation_error"
        assert data["error"]["error_code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Dados inválidos."
        assert data["error_code"] == "VALIDATION_ERROR"
        assert data["message"] == "Dados inválidos."
        assert data["fields"] == {"targetPosition": "Informe o cargo alvo."}

    def test_fields_key_present(self):
        resp = field_error_response(
            "validation_error", "Dados inválidos.", {}, status.HTTP_400_BAD_REQUEST
        )
        assert "fields" in resp.data
        assert resp.data["fields"] == {}


class TestExtractErrorMessage(TestCase):
    def test_extraction_cases(self):
        cases = [
            (None, "Valor inválido."),
            ([], "Valor inválido."),
            (["Campo obrigatório."], "Campo obrigatório."),
            ({"email": ["E-mail inválido."]}, "E-mail inválido."),
            ("Erro direto", "Erro direto"),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                assert extract_error_message(raw) == expected


class TestSerializerFieldErrors(TestCase):
    def test_converts_serializer_errors_to_field_dict(self):
        class FakeSerializer:
            errors = {"targetPosition": ["Informe o cargo alvo."], "contact": {"fullName": ["Nome é obrigatório."]}}

        fields = serializer_field_errors(FakeSerializer())
        assert fields["targetPosition"] == "Informe o cargo alvo."
        assert fields["contact"] == "Nome é obrigatório."

    def test_skips_empty_key(self):
        class FakeSerializer:
            errors = {"": ["ignored"], "email": ["E-mail inválido."]}

        fields = serializer_field_errors(FakeSerializer())
        assert "" not in fields
        assert fields["email"] == "E-mail inválido."
