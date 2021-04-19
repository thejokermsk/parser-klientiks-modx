from django.urls import path
from .views import (UpdateServiceListAPIView, )

urlpatterns = [
    path('list/update', UpdateServiceListAPIView.as_view()),
]
