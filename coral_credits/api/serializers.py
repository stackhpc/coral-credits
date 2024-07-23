from rest_framework import serializers

from coral_credits.api import models
from coral_credits.api.business_objects import (
    Allocation,
    ConsumerRequest,
    Context,
    Inventory,
    Lease,
    Reservation,
    ResourceRequest,
)


class ResourceClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ["id", "url", "name", "created"]


class ResourceProviderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceProvider
        fields = ["id", "url", "name", "created", "email", "info_url"]


class ResourceProviderAccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceProviderAccount
        fields = ["id", "url", "account", "provider", "project_id"]


class CreditAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CreditAccount
        fields = ["id", "url", "name", "email", "created"]


class CreditAllocationResourceSerializer(serializers.ModelSerializer):
    resource_class = ResourceClassSerializer()
    resource_hours = serializers.FloatField()

    class Meta:
        model = models.CreditAllocationResource
        fields = ["resource_class", "resource_hours"]

    def to_representation(self, instance):
        """Pass the context to the ResourceClassSerializer"""
        representation = super().to_representation(instance)
        resource_class_serializer = ResourceClassSerializer(
            instance.resource_class, context=self.context
        )
        representation["resource_class"] = resource_class_serializer.data
        return representation


class CreditAllocation(serializers.ModelSerializer):
    resources = CreditAllocationResourceSerializer(many=True)

    class Meta:
        model = models.CreditAllocation
        fields = ["name", "start", "end", "resources"]


class ResourceConsumptionRecord(serializers.ModelSerializer):
    resource_class = ResourceClassSerializer()

    class Meta:
        model = models.ResourceConsumptionRecord
        fields = ["resource_class", "resource_hours"]


class Consumer(serializers.ModelSerializer):
    resource_provider = ResourceProviderSerializer()
    resources = ResourceConsumptionRecord(many=True)

    class Meta:
        model = models.Consumer
        fields = ["consumer_ref", "resource_provider", "start", "end", "resources"]


class InventorySerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance.data

    def to_internal_value(self, data):
        return data

    def create(self, validated_data):
        return Inventory(data=validated_data)


class ResourceRequestSerializer(serializers.Serializer):
    inventories = InventorySerializer()
    # TODO(tylerchristie)
    # resource_provider_generation = serializers.IntegerField(required=False)

    def to_representation(self, instance):
        return {key: value for key, value in instance.__dict__.items()}

    def to_internal_value(self, data):
        return data

    def create(self, validated_data):
        inventories = InventorySerializer().create(validated_data.pop("inventories"))
        return ResourceRequest(inventories=inventories)


class AllocationSerializer(serializers.Serializer):
    id = serializers.CharField()
    hypervisor_hostname = serializers.UUIDField()
    extra = serializers.DictField()

    def create(self, validated_data):
        return Allocation(
            id=validated_data["id"],
            hypervisor_hostname=validated_data["hypervisor_hostname"],
            extra=validated_data.get("extra", {}),
        )


class ReservationSerializer(serializers.Serializer):
    resource_type = serializers.CharField()
    min = serializers.IntegerField()
    max = serializers.IntegerField()
    hypervisor_properties = serializers.CharField(required=False, allow_null=True)
    resource_properties = serializers.CharField(required=False, allow_null=True)
    allocations = serializers.ListField(
        child=AllocationSerializer(), required=False, allow_null=True
    )
    resource_requests = ResourceRequestSerializer()

    def create(self, validated_data):
        allocations = [
            AllocationSerializer().create(alloc)
            for alloc in validated_data.get("allocations", [])
        ]
        resource_requests = ResourceRequestSerializer().create(
            validated_data.pop("resource_requests")
        )
        return Reservation(
            **validated_data,
            allocations=allocations,
            resource_requests=resource_requests,
        )


class LeaseSerializer(serializers.Serializer):
    lease_id = serializers.UUIDField()
    lease_name = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    reservations = serializers.ListField(child=ReservationSerializer())

    def create(self, validated_data):
        reservations = [
            ReservationSerializer().create(res)
            for res in validated_data.pop("reservations")
        ]
        return Lease(
            lease_id=validated_data["lease_id"],
            lease_name=validated_data["lease_name"],
            start_date=validated_data["start_date"],
            end_time=validated_data["end_time"],
            reservations=reservations,
        )


class ContextSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    auth_url = serializers.URLField()
    region_name = serializers.CharField()

    def create(self, validated_data):
        return Context(
            user_id=validated_data["user_id"],
            project_id=validated_data["project_id"],
            auth_url=validated_data["auth_url"],
            region_name=validated_data["region_name"],
        )


class ConsumerRequestSerializer(serializers.Serializer):
    def __init__(self, *args, current_lease_required=False, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional field current_lease
        self.fields["current_lease"] = LeaseSerializer(
            required=current_lease_required, allow_null=(not current_lease_required)
        )

    context = ContextSerializer()
    lease = LeaseSerializer()

    def create(self, validated_data):
        context = ContextSerializer().create(validated_data["context"])
        lease = LeaseSerializer().create(validated_data["lease"])
        current_lease = (
            LeaseSerializer().create(validated_data["current_lease"])
            if "current_lease" in validated_data
            else None
        )
        return ConsumerRequest(
            context=context, lease=lease, current_lease=current_lease
        )

    def to_internal_value(self, data):
        # Custom validation or processing can be added here if needed
        return super().to_internal_value(data)

    def to_representation(self, instance):
        # Custom representation logic can be added here if needed
        return super().to_representation(instance)
