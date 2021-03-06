from collections import OrderedDict
from copy import deepcopy

from rest_framework.fields import empty
from rest_framework.relations import HyperlinkedIdentityField, HyperlinkedRelatedField, ManyRelatedField, RelatedField
from rest_framework.serializers import BaseSerializer, HyperlinkedModelSerializer
from rest_framework.utils.field_mapping import get_nested_relation_kwargs

from drf_hal_json import URL_FIELD_NAME, EMBEDDED_FIELD_NAME, LINKS_FIELD_NAME


class HalEmbeddedSerializer(HyperlinkedModelSerializer):
    pass


class HalHyperlinkedModelSerializer(HyperlinkedModelSerializer):
    def to_representation(self, instance):
        representation = super(HyperlinkedModelSerializer, self).to_representation(instance)
        hal_representation = OrderedDict((k, {'href': v}) for (k, v) in representation.items())
        return hal_representation


class HalModelSerializer(HyperlinkedModelSerializer):
    """
    Serializer for HAL representation of django models
    """
    serializer_related_field = HyperlinkedRelatedField
    links_serializer_class = HalHyperlinkedModelSerializer
    embedded_serializer_class = HalEmbeddedSerializer

    def __init__(self, instance=None, data=empty, **kwargs):
        super(HalModelSerializer, self).__init__(instance, data, **kwargs)
        self.nested_serializer_class = self.__class__
        if data != empty and not LINKS_FIELD_NAME in data:
            data[LINKS_FIELD_NAME] = dict()  # put links in data, so that field validation does not fail

    def get_fields(self):
        fields = super(HalModelSerializer, self).get_fields()

        embedded_field_names = list()
        embedded_fields = {}
        link_field_names = list()
        link_fields = {}
        resulting_fields = OrderedDict()
        resulting_fields[LINKS_FIELD_NAME] = None  # assign it here because of the order -> links first

        for field_name, field in fields.items():
            if self._is_link_field(field):
                link_field_names.append(field_name)
                link_fields[field_name] = field
            elif self._is_embedded_field(field):
                # if a related resource is embedded, it should still
                # get a link in the parent object

                try:
                    link_fields[field_name] = deepcopy(field[LINKS_FIELD_NAME][URL_FIELD_NAME])
                except TypeError:
                    # List fields are not subscriptable -- we won't have links to an embedded field that is an array
                    pass

                embedded_field_names.append(field_name)
                embedded_fields[field_name] = field
            else:
                resulting_fields[field_name] = field

        links_serializer = self._get_links_serializer(self.Meta.model, link_field_names, link_fields)
        if not links_serializer:
            # in case the class is overridden and the inheriting class wants no links to be serialized, the links field is removed
            del resulting_fields[LINKS_FIELD_NAME]
        else:
            resulting_fields[LINKS_FIELD_NAME] = links_serializer
        if embedded_field_names:
            resulting_fields[EMBEDDED_FIELD_NAME] = self._get_embedded_serializer(self.Meta.model,
                                                                                  getattr(self.Meta, "depth", 0),
                                                                                  embedded_field_names,
                                                                                  embedded_fields)
        return resulting_fields

    def _get_links_serializer(self, model_cls, link_field_names, fields):
        class HalNestedLinksSerializer(self.links_serializer_class):
            serializer_related_field = self.serializer_related_field

            class Meta:
                model = model_cls
                fields = link_field_names
                extra_kwargs = getattr(self.Meta, 'extra_kwargs', {})

            def get_fields(self):
                return fields

        return HalNestedLinksSerializer(instance=self.instance, source="*")

    def _get_embedded_serializer(self, model_cls, embedded_depth, embedded_field_names, fields):
        defined_nested_fields = getattr(self.Meta, "nested_fields", None)
        nested_class = self.__class__

        class HalNestedEmbeddedSerializer(self.embedded_serializer_class):
            nested_serializer_class = nested_class

            class Meta:
                model = model_cls
                fields = embedded_field_names
                nested_fields = defined_nested_fields
                depth = embedded_depth
                extra_kwargs = getattr(self.Meta, 'extra_kwargs', {})

            def get_fields(self):
                return fields

        return HalNestedEmbeddedSerializer(source="*")

    @staticmethod
    def _is_link_field(field):
        return isinstance(field, RelatedField) or isinstance(field, ManyRelatedField) \
               or isinstance(field, HyperlinkedIdentityField)

    @staticmethod
    def _is_embedded_field(field):
        return isinstance(field, BaseSerializer)

    def build_nested_field(self, field_name, relation_info, nested_depth):
        """
        Create nested fields for forward and reverse relationships.
        """
        class NestedSerializer(HalModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = '__all__'

        field_class = NestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)

        return field_class, field_kwargs
