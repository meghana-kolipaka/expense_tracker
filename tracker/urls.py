from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, SummaryView, TransactionViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("summary/", SummaryView.as_view()),
] + router.urls