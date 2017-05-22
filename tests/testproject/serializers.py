from drf_hal_json.serializers import HalModelSerializer
from rest_framework import serializers

from .models import CustomResource, TestResource, RelatedResource1, RelatedResource2, RelatedResource3


class TestResourceSerializer(HalModelSerializer):
    class Meta:
        model = TestResource
        fields = ('id', 'name', 'related_resource_1')
        nested_fields = {
            'related_resource_2': (
                ['name'],
                {
                    'related_resources_1': (
                        ['id', 'name'],
                        {}
                    )
                })
        }


class RelatedResource1Serializer(HalModelSerializer):
    class Meta:
        model = RelatedResource1


class RelatedResource2Serializer(HalModelSerializer):
    class Meta:
        model = RelatedResource2


class RelatedResource3Serializer(HalModelSerializer):
    class Meta:
        model = RelatedResource3


# Test fails if using HalModelSerializer:
#
# class CustomResourceSerializer(serializers.HyperlinkedModelSerializer):
class CustomResourceSerializer(HalModelSerializer):
    related_resource_3 = serializers.HyperlinkedIdentityField(
        read_only=True, view_name='relatedresource3-detail', lookup_field='name')

    class Meta:
        model = CustomResource
        fields = ('name', 'related_resource_3')
