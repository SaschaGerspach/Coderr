from django.contrib.auth import get_user_model
from rest_framework import serializers
from ..models import Profile

User = get_user_model()

class ProfilePatchSerializer(serializers.ModelSerializer):
    # User-Felder patchbar
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(source="user.email", required=False, allow_blank=True, allow_null=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "user",          # id des Users (read-only)
            "username",      # aus User
            "first_name",    # aus User
            "last_name",     # aus User
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "type",
            "email",         # aus User
            "created_at",
        ]
        read_only_fields = ["user", "username", "created_at"]

        extra_kwargs = {
            "file":          {"required": False, "allow_blank": True, "allow_null": True},
            "location":      {"required": False, "allow_blank": True, "allow_null": True},
            "tel":           {"required": False, "allow_blank": True, "allow_null": True},
            "description":   {"required": False, "allow_blank": True, "allow_null": True},
            "working_hours": {"required": False, "allow_blank": True, "allow_null": True},
            "type":          {"required": False, "allow_blank": True, "allow_null": True},
        }

    def update(self, instance: Profile, validated_data):
        # User-Felder separat aktualisieren
        user_data = validated_data.pop("user", {})
        for attr, val in user_data.items():
            setattr(instance.user, attr, val if val is not None else "")
        if user_data:
            instance.user.save(update_fields=["first_name", "last_name", "email"])

        # Profil-Felder aktualisieren (None -> "")
        for attr, val in validated_data.items():
            setattr(instance, attr, val if val is not None else "")
        instance.save()
        return instance

    # Spez: diese Felder dürfen in der Response nicht null sein -> "" wenn None/leer
    _no_null = {"first_name", "last_name", "location", "tel", "description", "working_hours"}

    def to_representation(self, instance: Profile):
        data = super().to_representation(instance)
        for key in self._no_null:
            if data.get(key) is None:
                data[key] = ""
        return data
    
class ProfileDetailSerializer(serializers.ModelSerializer):
    # User-Felder als Read-Only
    username   = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True, allow_blank=True)
    last_name  = serializers.CharField(source="user.last_name", read_only=True, allow_blank=True)
    email      = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "user",
            "username",
            "first_name",
            "last_name",
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "type",
            "email",
            "created_at",
        ]
        read_only_fields = fields  # rein lesend

    # Spez: bestimmte Felder dürfen nicht null sein → "" statt None
    _no_null = {"first_name", "last_name", "location", "tel", "description", "working_hours"}

    def to_representation(self, instance: Profile):
        data = super().to_representation(instance)
        for key in self._no_null:
            if data.get(key) is None:
                data[key] = ""
        return data

from rest_framework import serializers
from ..models import Profile

class BusinessProfileListSerializer(serializers.ModelSerializer):
    username   = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True, allow_blank=True)
    last_name  = serializers.CharField(source="user.last_name", read_only=True, allow_blank=True)

    class Meta:
        model = Profile
        fields = [
            "user",
            "username",
            "first_name",
            "last_name",
            "file",
            "location",
            "tel",
            "description",
            "working_hours",
            "type",
        ]

    # nie null -> leere Strings
    _no_null = {"first_name", "last_name", "location", "tel", "description", "working_hours"}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for k in self._no_null:
            if data.get(k) is None:
                data[k] = ""
        return data


class CustomerProfileListSerializer(serializers.ModelSerializer):
    username    = serializers.CharField(source="user.username", read_only=True)
    first_name  = serializers.CharField(source="user.first_name", read_only=True, allow_blank=True)
    last_name   = serializers.CharField(source="user.last_name", read_only=True, allow_blank=True)
    uploaded_at = serializers.DateTimeField(
        source="created_at",
        read_only=True,
        format="%Y-%m-%dT%H:%M:%S",
    )# Spec: uploaded_at

    class Meta:
        model = Profile
        fields = [
            "user",
            "username",
            "first_name",
            "last_name",
            "file",
            "uploaded_at",
            "type",
        ]

    # Felder dürfen nie null sein → leere Strings statt None
    _no_null = {"first_name", "last_name", "type"}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for k in self._no_null:
            if data.get(k) is None:
                data[k] = ""
        return data