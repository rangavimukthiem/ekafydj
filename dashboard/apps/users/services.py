"""
apps.users — Service Layer
Business logic for user management, invitations, and role changes.
"""
import logging
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.audit.services import AuditService

logger = logging.getLogger(__name__)
User = get_user_model()


class UserService:
    """Handles user lifecycle: creation, invitation, role updates."""

    def __init__(self, acting_user=None):
        self.acting_user = acting_user
        self.audit = AuditService()

    def create_user(
        self,
        *,
        username: str,
        email: str,
        role: str,
        first_name: str = "",
        last_name: str = "",
        password: str | None = None,
    ) -> User:
        """Create a new EKAFY user and send a welcome email."""
        if User.objects.filter(username=username).exists():
            raise ValueError(f"Username '{username}' is already taken.")

        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            invited_by=self.acting_user,
            is_active=True,
        )

        if password:
            user.set_password(password)
        else:
            # Force password reset on first login
            user.set_unusable_password()

        user.save()
        logger.info("Created user %s (role=%s) by %s", username, role, self.acting_user)

        self.audit.log(
            user=self.acting_user,
            action="user.created",
            resource_type="user",
            resource_id=str(user.pk),
            meta={"username": username, "role": role, "email": email},
        )

        self._send_invitation_email(user)
        return user

    def change_role(self, user: User, new_role: str) -> User:
        """Change a user's role."""
        old_role = user.role
        user.role = new_role
        user.save(update_fields=["role", "updated_at"])

        self.audit.log(
            user=self.acting_user,
            action="user.role_changed",
            resource_type="user",
            resource_id=str(user.pk),
            meta={"old_role": old_role, "new_role": new_role},
        )

        logger.info("Role changed: %s → %s for user %s", old_role, new_role, user.username)
        return user

    def deactivate_user(self, user: User) -> User:
        """Deactivate a user account."""
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])

        self.audit.log(
            user=self.acting_user,
            action="user.deactivated",
            resource_type="user",
            resource_id=str(user.pk),
            meta={"username": user.username},
        )
        return user

    def activate_user(self, user: User) -> User:
        """Re-activate a user account."""
        user.is_active = True
        user.save(update_fields=["is_active", "updated_at"])

        self.audit.log(
            user=self.acting_user,
            action="user.activated",
            resource_type="user",
            resource_id=str(user.pk),
            meta={"username": user.username},
        )
        return user

    def _send_invitation_email(self, user: User) -> None:
        """Send a welcome/invitation email with a password reset link."""
        try:
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"{settings.CSRF_TRUSTED_ORIGINS[0] if hasattr(settings, 'CSRF_TRUSTED_ORIGINS') and settings.CSRF_TRUSTED_ORIGINS else 'http://localhost:8000'}/account/password/reset/{uid}/{token}/"

            send_mail(
                subject="Welcome to EKAFY — Set Your Password",
                message=(
                    f"Hi {user.display_name},\n\n"
                    f"You've been invited to EKAFY as {user.get_role_display()}.\n\n"
                    f"Set your password here: {reset_link}\n\n"
                    "The EKAFY Team"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send invitation email to %s: %s", user.email, exc)
