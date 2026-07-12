from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User, Role

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'role', 'department')

    def validate_role(self, value):
        # Superadmin cannot be created via public registration
        if value == Role.SUPERADMIN:
            raise serializers.ValidationError("Cannot register as superadmin.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user