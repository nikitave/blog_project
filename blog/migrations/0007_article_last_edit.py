# Generated by Django 3.0.1 on 2020-06-08 05:16

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0006_remove_article_last_edited'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='last_edit',
            field=models.DateTimeField(default=datetime.datetime(2020, 6, 8, 5, 16, 25, 375817, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
