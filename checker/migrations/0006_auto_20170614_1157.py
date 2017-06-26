# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-14 11:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0005_auto_20170614_1105'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='report',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='issue',
            name='url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='issue',
            name='author_email',
            field=models.EmailField(blank=True, max_length=255),
        ),
    ]
