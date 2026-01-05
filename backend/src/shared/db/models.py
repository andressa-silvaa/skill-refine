from __future__ import annotations

import uuid

from django.db import models


class UUIDPrimaryKeyModel(models.Model):
    """
    Base model with UUID primary key.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """
    created_at / updated_at with timezone-aware timestamps (timestamptz on Postgres).
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CreatedAtModel(models.Model):
    """
    Only created_at (timestamptz). Some tables are append-only and don't need updated_at.
    """

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Optional soft delete marker (timestamptz).
    """

    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


