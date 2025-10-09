from rest_framework import serializers
from .models import (
    Bussiness, BusinessLocation, TaxRates, PickupStations, 
    ProductSettings, SaleSettings, PrefixSettings, ServiceTypes, BrandingSettings, Branch
)
from addresses.models import AddressBook, DeliveryRegion
from addresses.serializers import AddressBookSerializer as CentralizedAddressBookSerializer
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes

class BusinessLocationSerializer(serializers.ModelSerializer):
    state = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessLocation
        fields = '__all__'
    
    def get_state(self, obj):
        return str(obj.state) if obj.state else None
    
    def get_country(self, obj):
        return str(obj.country) if obj.country else None

class TaxRatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRates
        fields = '__all__'
        
class PickupStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PickupStations
        fields = '__all__'

class DeliveryAddressSerializer(serializers.ModelSerializer):
    pickupstations = PickupStationSerializer(many=True, read_only=True)
    
    class Meta:
        model = DeliveryRegion
        fields = '__all__'
        depth = 1


class PickupStationsSerializer(serializers.ModelSerializer):
    region_name = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PickupStations
        fields = '__all__'
        depth = 1
        
    def get_region_name(self, obj):
        return obj.region.name if obj.region else None
        
    def get_business_name(self, obj):
        return obj.business.name if obj.business else None

class PickupStationMinimalSerializer(serializers.ModelSerializer):
    """A minimal version of the pickup station serializer for embedding in addresses"""
    class Meta:
        model = PickupStations
        fields = ['id', 'pickup_location', 'description', 'open_hours', 'helpline', 'shipping_charge', 'google_pin']

# Using centralized AddressBookSerializer from addresses app

class ProductSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSettings
        fields = '__all__'

class SaleSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleSettings
        fields = '__all__'

class PrefixSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrefixSettings
        fields = '__all__'

class ServiceTypesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceTypes
        fields = '__all__'

class BrandingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandingSettings
        exclude = ('business',)
        

class BussinessSerializer(serializers.ModelSerializer):
    branches = serializers.SerializerMethodField()
    tax_rates = TaxRatesSerializer(many=True, read_only=True)
    prefix_settings = PrefixSettingsSerializer(many=True, read_only=True)
    product_settings = ProductSettingsSerializer(many=True, read_only=True)
    sale_settings = SaleSettingsSerializer(many=True, read_only=True)
    service_types = ServiceTypesSerializer(many=True, read_only=True)
    delivery_regions = DeliveryAddressSerializer(many=True, read_only=True)
    pickup_stations = PickupStationsSerializer(many=True, read_only=True)
    address_book = CentralizedAddressBookSerializer(many=True, read_only=True)
    timezone = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    branding = BrandingSettingsSerializer(read_only=True)
    branding_settings = serializers.SerializerMethodField()
    
    class Meta:
        model = Bussiness
        fields = '__all__'
        
    def get_branches(self, obj):
        """Get branches for this business"""
        from .models import Branch
        branches = Branch.objects.filter(business=obj, is_active=True)
        return [{
            'id': branch.id,
            'name': branch.name,
            'branch_code': branch.branch_code,
            'location': {
                'id': branch.location.id,
                'city': branch.location.city,
                'county': branch.location.county,
                'state': str(branch.location.state) if branch.location.state else None,
                'country': str(branch.location.country) if branch.location.country else None,
                'zip_code': branch.location.zip_code,
                'postal_code': branch.location.postal_code,
            },
            'is_main_branch': branch.is_main_branch,
            'is_active': branch.is_active,
            'created_at': branch.created_at
        } for branch in branches]
    
class BranchSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    class Meta:
        model = Branch
        fields = '__all__'

    def get_location(self, obj):
        return {
            'id': obj.location.id,
            'city': obj.location.city,
            'county': obj.location.county,
            'state': str(obj.location.state) if obj.location.state else None,
            'country': str(obj.location.country) if obj.location.country else None,
            'zip_code': obj.location.zip_code,
            'postal_code': obj.location.postal_code,
        }
