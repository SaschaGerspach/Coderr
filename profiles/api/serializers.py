"""Profiles API serializers.

Contains serializers for:
- reading a profile,
- partially updating a profile (owner-only),
- listing business profiles,
- listing customer profiles (with `uploaded_at` alias).

Serializers ensure certain string fields never return `null` in responses, but
empty strings instead, matching the project specification.
"""

import os
import uuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from rest_framework import serializers
from ..models import Profile

User = get_user_model()


# ------------------------------ helpers ------------------------------

def _avatar_upload_path(user_id: int, filename: str) -> str:
    base, ext = os.path.splitext(filename or "")
    ext = (ext or ".jpg").lower()
    return f"avatars/{user_id}/{uuid.uuid4().hex}{ext}"


def _is_uploaded_file(obj) -> bool:
    return hasattr(obj, "read")


def _abs_url(request, relative_url: str) -> str:
    if not relative_url:
        return ""
    return request.build_absolute_uri(relative_url) if request else relative_url


def _save_avatar_and_get_url(request, file_obj) -> str:
    """Store uploaded image and return absolute URL (JPEG/PNG, ≤5MB)."""
    ctype = (getattr(file_obj, "content_type", "") or "").lower()
    if ctype not in {"image/jpeg", "image/png"}:
        raise serializers.ValidationError(
            {"file": "Unsupported file type. Allowed: JPEG, PNG"}
        )
    if getattr(file_obj, "size", 0) > 5 * 1024 * 1024:
        raise serializers.ValidationError({"file": "File too large (>5MB)."})

    path = _avatar_upload_path(request.user.id, getattr(file_obj, "name", "avatar"))
    saved_path = default_storage.save(path, file_obj)
    rel = f"{settings.MEDIA_URL}{saved_path}".replace("//", "/")
    return _abs_url(request, rel)


def _apply_user_updates(user, data: dict):
    for attr, val in data.items():
        setattr(user, attr, val if val is not None else "")
    if data:
        user.save(update_fields=["first_name", "last_name", "email"])


def _coalesce_fields(data: dict, keys: set):
    for k in keys:
        if data.get(k) is None:
            data[k] = ""


# ------------------------------ custom field ------------------------------

class FileOrURLField(serializers.Field):
    """
    Accepts EITHER an UploadedFile (multipart) OR a string URL (JSON).
    Representation is always a (possibly empty) string.
    """

    def to_internal_value(self, data):
        if _is_uploaded_file(data):                # upload
            return data
        if data in (None, ""):                     # empty/None -> empty string
            return ""
        if isinstance(data, str):                  # URL string
            return data
        raise serializers.ValidationError(
            "file must be an uploaded image or a string URL."
        )

    def to_representation(self, value):
        return value or ""


# ------------------------------ serializers ------------------------------

class ProfilePatchSerializer(serializers.ModelSerializer):
    """
    Partial update of the caller's own profile.
    `file` remains the single API key for avatar URL OR multipart upload.
    """

    file = FileOrURLField(required=False)
    first_name = serializers.CharField(
        source="user.first_name", required=False, allow_blank=True, allow_null=True
    )
    last_name = serializers.CharField(
        source="user.last_name", required=False, allow_blank=True, allow_null=True
    )
    email = serializers.EmailField(
        source="user.email", required=False, allow_blank=True, allow_null=True
    )
    username = serializers.CharField(source="user.username", read_only=True)

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
        read_only_fields = ["user", "username", "created_at"]
        extra_kwargs = {
            "file": {"required": False, "allow_blank": True, "allow_null": True},
            "location": {"required": False, "allow_blank": True, "allow_null": True},
            "tel": {"required": False, "allow_blank": True, "allow_null": True},
            "description": {"required": False, "allow_blank": True, "allow_null": True},
            "working_hours": {"required": False, "allow_blank": True, "allow_null": True},
            "type": {"required": False, "allow_blank": True, "allow_null": True},
        }

    def update(self, instance: Profile, validated_data):
        """Handle nested user fields, avatar upload/string, and normalize None -> ''."""
        request = self.context.get("request")
        _apply_user_updates(instance.user, validated_data.pop("user", {}))

        if "file" in validated_data:
            incoming = validated_data.pop("file")
            instance.file = (
                _save_avatar_and_get_url(request, incoming)
                if _is_uploaded_file(incoming)
                else (incoming or "")
            )

        for attr, val in validated_data.items():
            setattr(instance, attr, val if val is not None else "")
        instance.save()
        return instance

    _no_null = {
        "first_name",
        "last_name",
        "location",
        "tel",
        "description",
        "working_hours",
        "file",
    }

    def to_representation(self, instance: Profile):
        data = super().to_representation(instance)
        _coalesce_fields(data, self._no_null)
        return data


class ProfileDetailSerializer(serializers.ModelSerializer):
    """Read-only detail serializer (coalesces selected string fields to '')."""

    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(
        source="user.first_name", read_only=True, allow_blank=True
    )
    last_name = serializers.CharField(
        source="user.last_name", read_only=True, allow_blank=True
    )
    email = serializers.EmailField(source="user.email", read_only=True)

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
        read_only_fields = fields

    _no_null = {
        "first_name",
        "last_name",
        "location",
        "tel",
        "description",
        "working_hours",
    }

    def to_representation(self, instance: Profile):
        data = super().to_representation(instance)
        _coalesce_fields(data, self._no_null)
        return data


class BusinessProfileListSerializer(serializers.ModelSerializer):
    """List serializer for business profiles (no nulls for selected fields)."""

    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(
        source="user.first_name", read_only=True, allow_blank=True
    )
    last_name = serializers.CharField(
        source="user.last_name", read_only=True, allow_blank=True
    )

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

    _no_null = {
        "first_name",
        "last_name",
        "location",
        "tel",
        "description",
        "working_hours",
    }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        _coalesce_fields(data, self._no_null)
        return data


class CustomerProfileListSerializer(serializers.ModelSerializer):
    """List serializer for customer profiles with `uploaded_at` alias."""

    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(
        source="user.first_name", read_only=True, allow_blank=True
    )
    last_name = serializers.CharField(
        source="user.last_name", read_only=True, allow_blank=True
    )
    uploaded_at = serializers.DateTimeField(
        source="created_at", read_only=True, format="%Y-%m-%dT%H:%M:%S"
    )

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

    _no_null = {"first_name", "last_name", "type"}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        _coalesce_fields(data, self._no_null)
        return data
