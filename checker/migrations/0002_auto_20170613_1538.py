# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-13 15:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('checker', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='checkhistory',
            managers=[
            ],
        ),
        migrations.RenameField(
            model_name='checkhistory',
            old_name='respository',
            new_name='repository',
        ),
    ]
