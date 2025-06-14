# Generated by Django 4.2.5 on 2025-05-28 14:28

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('myapp', '0003_remove_expense_involved_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='excluded_members',
            field=models.ManyToManyField(blank=True, help_text='Members who should not be included in this expense split', related_name='excluded_expenses', to=settings.AUTH_USER_MODEL),
        ),
    ]
