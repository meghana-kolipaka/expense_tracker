from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Category, Transaction

User = get_user_model()


class BaseTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.other = User.objects.create_user("bob", password="pass12345")
        self.client.force_authenticate(self.user)
        self.food = Category.objects.create(user=self.user, name="Food")
        self.rent = Category.objects.create(user=self.user, name="Rent")
        self.bob_category = Category.objects.create(user=self.other, name="Travel")

    def make(self, user=None, **kwargs):
        data = {
            "user": user or self.user,
            "type": "expense",
            "amount": "100.00",
            "date": date(2026, 11, 1),
        }
        data.update(kwargs)
        return Transaction.objects.create(**data)


class AuthTests(BaseTestCase):
    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/transactions/")
        self.assertEqual(response.status_code, 401)

    def test_token_login_and_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/token/", {"username": "alice", "password": "pass12345"}
        )
        self.assertEqual(response.status_code, 200)
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)
        self.assertEqual(self.client.get("/api/transactions/").status_code, 200)


class TransactionTests(BaseTestCase):
    def test_create_transaction_sets_owner(self):
        response = self.client.post(
            "/api/transactions/",
            {"category": self.food.id, "type": "expense", "amount": "250.00", "date": "2026-11-10"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Transaction.objects.get(id=response.data["id"]).user, self.user)

    def test_rejects_zero_amount(self):
        response = self.client.post(
            "/api/transactions/", {"type": "expense", "amount": "0", "date": "2026-11-10"}
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_negative_amount(self):
        response = self.client.post(
            "/api/transactions/", {"type": "expense", "amount": "-5", "date": "2026-11-10"}
        )
        self.assertEqual(response.status_code, 400)

    def test_user_sees_only_own_transactions(self):
        self.make()
        self.make(user=self.other, amount="999.00")
        response = self.client.get("/api/transactions/")
        self.assertEqual(response.data["count"], 1)

    def test_cannot_open_other_users_transaction(self):
        theirs = self.make(user=self.other)
        response = self.client.get(f"/api/transactions/{theirs.id}/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_use_other_users_category(self):
        response = self.client.post(
            "/api/transactions/",
            {"category": self.bob_category.id, "type": "expense", "amount": "10", "date": "2026-11-10"},
        )
        self.assertEqual(response.status_code, 400)

    def test_update_transaction(self):
        tx = self.make()
        response = self.client.patch(f"/api/transactions/{tx.id}/", {"amount": "175.50"})
        self.assertEqual(response.status_code, 200)
        tx.refresh_from_db()
        self.assertEqual(tx.amount, Decimal("175.50"))

    def test_delete_transaction(self):
        tx = self.make()
        response = self.client.delete(f"/api/transactions/{tx.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_filter_by_type(self):
        self.make(type="income", amount="1000.00")
        self.make(type="expense")
        response = self.client.get("/api/transactions/?type=income")
        self.assertEqual(response.data["count"], 1)

    def test_filter_by_date_range(self):
        self.make(date=date(2026, 10, 1))
        self.make(date=date(2026, 11, 10))
        response = self.client.get("/api/transactions/?date__gte=2026-11-01&date__lte=2026-11-30")
        self.assertEqual(response.data["count"], 1)


class CategoryTests(BaseTestCase):
    def test_duplicate_category_rejected(self):
        response = self.client.post("/api/categories/", {"name": "food"})
        self.assertEqual(response.status_code, 400)


class SummaryTests(BaseTestCase):
    def test_summary_totals(self):
        self.make(type="income", amount="1000.00")
        self.make(category=self.food, amount="100.00")
        self.make(category=self.rent, amount="300.00")
        data = self.client.get("/api/summary/").data
        self.assertEqual(data["total_income"], Decimal("1000.00"))
        self.assertEqual(data["total_expense"], Decimal("400.00"))
        self.assertEqual(data["balance"], Decimal("600.00"))

    def test_summary_only_counts_own_data(self):
        self.make(amount="100.00")
        self.make(user=self.other, amount="5000.00")
        data = self.client.get("/api/summary/").data
        self.assertEqual(data["total_expense"], Decimal("100.00"))

    def test_summary_by_category(self):
        self.make(category=self.food, amount="100.00")
        self.make(category=self.rent, amount="300.00")
        data = self.client.get("/api/summary/").data
        self.assertEqual(data["by_category"][0]["category"], "Rent")
        self.assertEqual(data["by_category"][0]["total"], Decimal("300.00"))

    def test_summary_by_month(self):
        self.make(date=date(2026, 10, 15))
        self.make(date=date(2026, 11, 1))
        data = self.client.get("/api/summary/").data
        months = [row["month"] for row in data["by_month"]]
        self.assertEqual(months, ["2026-10", "2026-11"])