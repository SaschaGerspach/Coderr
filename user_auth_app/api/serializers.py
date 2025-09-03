from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

User = get_user_model()


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    repeated_password = serializers.CharField(write_only=True, min_length=6)
    type = serializers.ChoiceField(choices=("customer", "business"))

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(_("Username already taken."))
        return value

    def validate_email(self, value):
        validate_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("Email already in use."))
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["repeated_password"]:
            raise serializers.ValidationError(
                {"repeated_password": _("Passwords do not match.")})
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        validated_data.pop("repeated_password", None)
        validated_data.pop("type", None)  # nur validieren, nicht speichern
        raw_password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(raw_password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs.get("username"),
                            password=attrs.get("password"))
        if not user:
            raise serializers.ValidationError(
                {"detail": "Invalid Credentials"})
        attrs["user"] = user

        return attrs
