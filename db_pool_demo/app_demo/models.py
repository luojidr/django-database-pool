from django.db import models


class PoolDemoModel(models.Model):
    name = models.CharField("name", max_length=200, default='')
    size = models.IntegerField("size", default=0)
    od_date = models.DateTimeField("od date", default=None)
    db_type = models.CharField("name", max_length=50, default='')
    remark = models.CharField("remark", max_length=100, default='')


