from configurations.base_features.serializers.base_serializer import BaseSerializer
from vendors.models import *


class VendorBaseSerializer(BaseSerializer):
    class Meta:
        model = Vendor
        fields = '__all__'


class ContactPersonnelBaseSerializer(BaseSerializer):
    class Meta:
        model = ContactPersonnel
        fields = '__all__'


