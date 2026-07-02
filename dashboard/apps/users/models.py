"""
apps.users — Custom User Model
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class EkafyUser(AbstractUser):
    """
    Extended user model with EKAFY-specific fields.
    Roles: admin > operator > viewer
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        OPERATOR = "operator", "Operator"
        VIEWER = "viewer", "Viewer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
        db_index=True,
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    last_active = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    invited_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invitees",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "EKAFY User"
        verbose_name_plural = "EKAFY Users"
        ordering = ["username"]

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.role})"

    @property
    def is_admin(self) -> bool:
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_operator(self) -> bool:
        return self.is_admin or self.role == self.Role.OPERATOR

    @property
    def is_viewer(self) -> bool:
        return self.is_authenticated

    @property
    def display_name(self) -> str:
        return self.get_full_name() or self.username

    @property
    def initials(self) -> str:
        name = self.get_full_name()
        if name:
            parts = name.split()
            return "".join(p[0].upper() for p in parts[:2])
        return self.username[:2].upper()
