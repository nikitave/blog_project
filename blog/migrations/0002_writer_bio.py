# Generated by Django 3.0.1 on 2020-06-03 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='writer',
            name='bio',
            field=models.CharField(default=0, max_length=1000),
            preserve_default=False,
        ),
    ]
