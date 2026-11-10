from rest_framework import serializers

from .models import Category, Transaction


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]

    def validate_name(self, value):
        user = self.context["request"].user
        if Category.objects.filter(user=user, name__iexact=value).exists():
            raise serializers.ValidationError("You already have this category.")
        return value


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "category", "type", "amount", "date", "note", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate_category(self, value):
        if value and value.user != self.context["request"].user:
            raise serializers.ValidationError("Invalid category.")
        return value