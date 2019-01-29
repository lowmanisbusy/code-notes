# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='is_default',
            field=models.BooleanField(verbose_name='是否默认', default=False),
        ),
    ]
