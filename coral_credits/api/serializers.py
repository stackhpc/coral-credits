from typing import Type

from rest_framework import serializers

from coral_credits.api import models
from coral_credits.api.business_objects import (
    Allocation,
    BaseReservation,
    ConsumerRequest,
    Context,
    FlavorReservation,
    Lease,
    PhysicalReservation,
    ResourceRequest,
    VirtualReservation,
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


class CreditAllocationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.CreditAllocation
        fields = ["id", "name", "created", "account", "start", "end"]


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


class ResourceRequestSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance.resources

    def to_internal_value(self, data):
        return {"resources": data}

    def create(self, validated_data):
        return ResourceRequest(**validated_data)


class AllocationSerializer(serializers.Serializer):
    id = serializers.CharField()
    hypervisor_hostname = serializers.CharField()
    extra = serializers.DictField(required=False, allow_null=True)

    def create(self, validated_data):
        return Allocation(
            id=validated_data["id"],
            hypervisor_hostname=validated_data["hypervisor_hostname"],
            extra=validated_data.get("extra", {}),
        )


class BaseReservationSerializer(serializers.Serializer):
    resource_type = serializers.CharField()
    allocations = serializers.ListField(child=AllocationSerializer(), required=False)

    def create(self, validated_data):
        allocations = [
            AllocationSerializer().create(alloc)
            for alloc in validated_data.pop("allocations", [])
        ]
        return ReservationFactory.get_instance(
            **validated_data,
            allocations=allocations,
        )


class PhysicalReservationSerializer(BaseReservationSerializer):
    min = serializers.IntegerField()
    max = serializers.IntegerField()
    hypervisor_properties = serializers.CharField(required=False, allow_blank=True)
    resource_properties = serializers.CharField(required=False, allow_blank=True)


class FlavorReservationSerializer(BaseReservationSerializer):
    amount = serializers.IntegerField()
    flavor_id = serializers.CharField()
    affinity = serializers.CharField(required=False, default="None")


class VirtualReservationSerializer(BaseReservationSerializer):
    amount = serializers.IntegerField()
    vcpus = serializers.IntegerField()
    memory_mb = serializers.IntegerField()
    disk_gb = serializers.IntegerField()
    affinity = serializers.CharField(required=False, default="None")
    resource_properties = serializers.CharField(required=False, allow_blank=True)


class ReservationFactory:
    @staticmethod
    def get_serializer(resource_type: str) -> Type[BaseReservationSerializer]:
        serializers = {
            "physical:host": PhysicalReservationSerializer,
            "flavor:instance": FlavorReservationSerializer,
            "virtual:instance": VirtualReservationSerializer,
        }
        serializer = serializers.get(resource_type)
        if not serializer:
            raise serializers.ValidationError(f"Unknown resource_type: {resource_type}")
        return serializer

    @staticmethod
    def get_instance(**kwargs) -> BaseReservation:
        print("PRINTING!!!")
        print(kwargs)
        resource_type = kwargs.get("resource_type")

        reservation_classes = {
            "physical:host": PhysicalReservation,
            "flavor:instance": FlavorReservation,
            "virtual:instance": VirtualReservation,
        }

        reservation_class = reservation_classes.get(resource_type)
        if not reservation_class:
            raise ValueError(f"Unknown resource_type: {resource_type}")

        return reservation_class(**kwargs)


class ReservationField(serializers.Field):
    def to_internal_value(self, data):
        resource_type = data.get("resource_type")
        serializer_class = ReservationFactory.get_serializer(resource_type)
        serializer = serializer_class(data=data)

        if serializer.is_valid():
            return serializer.validated_data
        else:
            raise serializers.ValidationError(serializer.errors)

    def to_representation(self, instance):
        if isinstance(instance, dict):
            resource_type = instance.get("resource_type")
            serializer_class = ReservationFactory.get_serializer(resource_type)
            return serializer_class(instance).data
        return instance


class LeaseSerializer(serializers.Serializer):
    def __init__(self, *args, dry_run=False, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional field id
        self.fields["id"] = serializers.UUIDField(
            required=(not dry_run), allow_null=dry_run
        )

    name = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    before_end_date = serializers.DateTimeField(required=False, allow_null=True)
    reservations = serializers.ListField(child=ReservationField())
    resource_requests = ResourceRequestSerializer()

    def create(self, validated_data):
        reservations = []
        for res_data in validated_data.pop("reservations"):
            resource_type = res_data.get("resource_type")
            serializer_class = ReservationFactory.get_serializer(resource_type)
            serializer = serializer_class(data=res_data)
            if serializer.is_valid():
                reservations.append(serializer.create(serializer.validated_data))
            else:
                raise serializers.ValidationError(serializer.errors)

        resource_requests = ResourceRequestSerializer().create(
            validated_data.pop("resource_requests")
        )
        return Lease(
            id=validated_data["id"],
            name=validated_data["name"],
            start_date=validated_data["start_date"],
            end_date=validated_data["end_date"],
            reservations=reservations,
            resource_requests=resource_requests,
        )


class ContextSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    auth_url = serializers.URLField()
    region_name = serializers.CharField(required=False, allow_null=True)

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
