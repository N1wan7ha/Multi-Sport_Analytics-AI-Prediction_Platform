"""JWT serializers for accounts app."""
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Attach role metadata used by frontend route guards."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['user_id'] = user.id
        token['email'] = user.email
        return token
