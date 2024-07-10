from rest_framework import serializers

from coral_credits.api import models


class ResourceClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ["url", "name", "created"]


class ResourceProviderSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.ResourceProvider
        fields = ["url", "name", "created", "email", "info_url"]


class CreditAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CreditAccount
        fields = ["url", "name", "email", "created"]


class ResourceClass(serializers.ModelSerializer):
    class Meta:
        model = models.ResourceClass
        fields = ["name"]


class CreditAllocationResource(serializers.ModelSerializer):
    resource_class = ResourceClass()

    class Meta:
        model = models.CreditAllocationResource
        fields = ["resource_class", "resource_hours"]


class CreditAllocation(serializers.ModelSerializer):
    resources = CreditAllocationResource(many=True)

    class Meta:
        model = models.CreditAllocation
        fields = ["name", "start", "end", "resources"]


class ResourceConsumptionRecord(serializers.ModelSerializer):
    resource_class = ResourceClass()

    class Meta:
        model = models.ResourceConsumptionRecord
        fields = ["resource_class", "resource_hours"]


class Consumer(serializers.ModelSerializer):
    resource_provider = ResourceProviderSerializer()
    resources = ResourceConsumptionRecord(many=True)

    class Meta:
        model = models.Consumer
        fields = ["consumer_ref", "resource_provider", "start", "end", "resources"]


class ContextSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    auth_url = serializers.URLField()
    region_name = serializers.CharField()


class InventorySerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {key: value for key, value in instance.items()}

    def to_internal_value(self, data):
        return data


class ResourceRequestSerializer(serializers.Serializer):
    inventories = InventorySerializer()
    # TODO(tylerchristie)
    # resource_provider_generation = serializers.IntegerField(required=False)

    def to_representation(self, instance):
        return {key: value for key, value in instance.items()}

    def to_internal_value(self, data):
        return data



class AllocationSerializer(serializers.Serializer):
    id = serializers.CharField()
    hypervisor_hostname = serializers.UUIDField()
    extra = serializers.DictField()


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


class LeaseSerializer(serializers.Serializer):
    lease_id = serializers.UUIDField()
    lease_name = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    reservations = serializers.ListField(child=ReservationSerializer())


class ConsumerRequest(serializers.Serializer):
    def __init__(self, *args, current_lease_required=False, **kwargs):
        super().__init__(*args, **kwargs)
        # current_lease required on update but not create
        self.fields["current_lease"] = LeaseSerializer(
            required=current_lease_required, allow_null=(not current_lease_required)
        )

    context = ContextSerializer()
    lease = LeaseSerializer()

    def to_internal_value(self, data):
        # Custom validation or processing can be added here if needed
        return super().to_internal_value(data)

    def to_representation(self, instance):
        # Custom representation logic can be added here if needed
        return super().to_representation(instance)
