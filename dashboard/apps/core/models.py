"""
apps.core — Base Models
Provides abstract base classes used across all domain apps.
"""
import uuid
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    """Abstract model with UUID primary key."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """Abstract model with created_at / updated_at timestamps."""

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class BaseModel(UUIDModel, TimestampedModel):
    """
    Primary base model combining UUID PK + timestamps.
    All EKAFY domain models inherit from this.
    """

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} pk={self.pk}>"
