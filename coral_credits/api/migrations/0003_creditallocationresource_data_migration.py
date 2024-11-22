from django.db import migrations


def copy_resource_hours(apps, schema_editor):
    CreditAllocationResource = apps.get_model("api", "CreditAllocationResource")
    for resource in CreditAllocationResource.objects.all():
        # This is the best we can do if we never previously saved the original
        # resource hours in an older db version.
        resource.original_resource_hours = resource.resource_hours
        resource.save()


def reverse_copy(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0002_creditallocationresource_original_resource_hours"),
    ]

    operations = [
        migrations.RunPython(copy_resource_hours, reverse_copy),
    ]
