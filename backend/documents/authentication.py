"""Authentication helpers for JWT and local MVP demo mode."""
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication


class DemoOrJWTAuthentication(JWTAuthentication):
    """Accept Simple JWT tokens and the frontend demo token used by the MVP login screen."""

    demo_access_token = "demo-access-token"

    def authenticate(self, request):
        header = self.get_header(request)
        if header is None:
            return None

        raw_token = self.get_raw_token(header)
        if raw_token is None:
            return None

        if raw_token.decode("utf-8") == self.demo_access_token:
            user, _created = get_user_model().objects.get_or_create(
                username="demo",
                defaults={"email": "demo@example.com", "is_active": True},
            )
            return user, raw_token

        return super().authenticate(request)
