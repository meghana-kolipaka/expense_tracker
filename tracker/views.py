from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    filterset_fields = {
        "type": ["exact"],
        "category": ["exact"],
        "date": ["gte", "lte"],
    }

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SummaryView(APIView):
    """Totals, spending per category and totals per month for the logged-in user."""

    def get(self, request):
        qs = Transaction.objects.filter(user=request.user)

        totals = {
            row["type"]: row["total"]
            for row in qs.values("type").annotate(total=Sum("amount"))
        }
        income = totals.get("income") or 0
        expense = totals.get("expense") or 0

        by_category = (
            qs.filter(type="expense")
            .values("category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        by_month = (
            qs.annotate(month=TruncMonth("date"))
            .values("month", "type")
            .annotate(total=Sum("amount"))
            .order_by("month", "type")
        )

        return Response(
            {
                "total_income": income,
                "total_expense": expense,
                "balance": income - expense,
                "by_category": [
                    {"category": r["category__name"] or "Uncategorized", "total": r["total"]}
                    for r in by_category
                ],
                "by_month": [
                    {"month": r["month"].strftime("%Y-%m"), "type": r["type"], "total": r["total"]}
                    for r in by_month
                ],
            }
        )