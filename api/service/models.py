from django.db import models

# Create your models here.


class UpdatedService(models.Model):
    added = models.IntegerField(null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="wait")

class ServiceList(models.Model):
    tmplvarid = models.IntegerField()
    contentid = models.IntegerField()
    value = models.TextField()

    class Meta:
        managed = False
        db_table = 'modx_site_tmplvar_contentvalues'


class ModxSystemSettings(models.Model):
    key = models.CharField(max_length=50, primary_key=True)
    value = models.TextField()
    xtype = models.CharField(max_length=75)
    namespace = models.CharField(max_length=40)
    area = models.CharField(max_length=191)
    editedon = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'modx_system_settings'
