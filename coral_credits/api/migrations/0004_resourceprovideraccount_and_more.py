# Generated by Django 5.0.6 on 2024-07-04 15:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_rename_consume_ref_consumer_consumer_ref_and_more"),
    ]

    operations = [
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
        migrations.AlterUniqueTogether(
            name="consumer",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="consumer",
            name="resource_provider_account",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="api.resourceprovideraccount",
            ),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name="consumer",
            unique_together={("consumer_ref", "resource_provider_account")},
        ),
        migrations.RemoveField(
            model_name="consumer",
            name="account",
        ),
        migrations.RemoveField(
            model_name="consumer",
            name="resource_provider",
        ),
    ]
