# Generated by Django 5.0.8 on 2024-08-14 15:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CreditAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("email", models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name="ResourceClass",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="ResourceProvider",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, unique=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("email", models.EmailField(max_length=254)),
                ("info_url", models.URLField()),
            ],
        ),
        migrations.CreateModel(
            name="CreditAllocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("start", models.DateTimeField()),
                ("end", models.DateTimeField()),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="api.creditaccount",
                    ),
                ),
            ],
            options={
                "unique_together": {("account", "start"), ("name", "account")},
            },
        ),
        migrations.CreateModel(
            name="ResourceProviderAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("project_id", models.UUIDField()),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.creditaccount",
                    ),
                ),
                (
                    "provider",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="api.resourceprovider",
                    ),
                ),
            ],
            options={
                "unique_together": {
                    ("account", "provider"),
                    ("provider", "project_id"),
                },
            },
        ),
        migrations.CreateModel(
            name="Consumer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("consumer_ref", models.CharField(max_length=200)),
                ("consumer_uuid", models.UUIDField()),
                ("user_ref", models.UUIDField()),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("start", models.DateTimeField()),
                ("end", models.DateTimeField()),
                (
                    "resource_provider_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="api.resourceprovideraccount",
                    ),
                ),
            ],
            options={
                "unique_together": {("consumer_uuid", "resource_provider_account")},
            },
        ),
        migrations.CreateModel(
            name="CreditAllocationResource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("resource_hours", models.FloatField()),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "allocation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resources",
                        to="api.creditallocation",
                    ),
                ),
                (
                    "resource_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="api.resourceclass",
                    ),
                ),
            ],
            options={
                "ordering": ("allocation__start",),
                "unique_together": {("allocation", "resource_class")},
            },
        ),
        migrations.CreateModel(
            name="ResourceConsumptionRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("resource_hours", models.FloatField()),
                (
                    "consumer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resources",
                        to="api.consumer",
                    ),
                ),
                (
                    "resource_class",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="api.resourceclass",
                    ),
                ),
            ],
            options={
                "ordering": ("consumer__start",),
                "unique_together": {("consumer", "resource_class")},
            },
        ),
    ]
