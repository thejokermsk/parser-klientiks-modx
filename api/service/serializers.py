from django.db import models
from django.db.models import fields
from rest_framework.serializers import (ModelSerializer, )

from .models import (UpdatedService, ServiceList, )


class UpdatedServiceSerializer(ModelSerializer):
    class Meta:
        model = UpdatedService
        fields = '__all__'


class ServiceListSerializer(ModelSerializer):
    class Meta:
        model = ServiceList
        fields = '__all__'
