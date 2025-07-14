#!/usr/bin/env python
"""
Test script for PM Automation functionality
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
django.setup()

from pm_automation.services import PMAutomationService
from pm_automation.models import PMSettings, PMUnitChoices
from meter_readings.models import MeterReading
from work_orders.models import WorkOrder
from assets.models import Equipment, EquipmentCategory
from tenant_users.models import TenantUser
from company.models import Site, Location
from django.contrib.contenttypes.models import ContentType
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pm_automation():
    """Test PM automation functionality"""
    print("=== Testing PM Automation ===")
    
    # Check if we have any sites/locations
    sites = Site.objects.all()
    print(f"Found {sites.count()} sites")
    
    locations = Location.objects.all()
    print(f"Found {locations.count()} locations")
    
    # Check if we have any equipment categories
    categories = EquipmentCategory.objects.all()
    print(f"Found {categories.count()} equipment categories")
    
    # Get the first equipment asset
    try:
        equipment = Equipment.objects.first()
        if not equipment:
            print("No equipment found. Creating test equipment...")
            
            # Create test data if needed
            if not sites.exists():
                site = Site.objects.create(name="Test Site", code="TEST")
                print(f"Created test site: {site}")
            else:
                site = sites.first()
            
            if not locations.exists():
                location = Location.objects.create(
                    name="Test Location", 
                    slug="test-location",
                    site=site
                )
                print(f"Created test location: {location}")
            else:
                location = locations.first()
            
            if not categories.exists():
                category = EquipmentCategory.objects.create(
                    name="Test Category",
                    slug="test-category"
                )
                print(f"Created test category: {category}")
            else:
                category = categories.first()
            
            # Create test equipment
            equipment = Equipment.objects.create(
                code="TEST001",
                name="Test Equipment",
                description="Test equipment for PM automation",
                location=location,
                category=category
            )
            print(f"Created test equipment: {equipment}")
        
        print(f"Using equipment: {equipment}")
        
        # Get or create a test user
        user = TenantUser.objects.first()
        if not user:
            print("No users found. Please create a user first.")
            return
        
        print(f"Using user: {user}")
        
        # Create PM settings for the equipment
        content_type = ContentType.objects.get_for_model(Equipment)
        
        pm_settings, created = PMSettings.objects.get_or_create(
            content_type=content_type,
            object_id=equipment.id,
            defaults={
                'interval_value': 100,
                'interval_unit': PMUnitChoices.HOURS,
                'start_threshold_value': 500,
                'start_threshold_unit': PMUnitChoices.HOURS,
                'lead_time_value': 50,
                'lead_time_unit': PMUnitChoices.HOURS,
                'is_active': True,
                'next_trigger_value': 500
            }
        )
        
        if created:
            print(f"Created PM settings: {pm_settings}")
        else:
            print(f"Using existing PM settings: {pm_settings}")
        
        # Test meter reading that should trigger PM
        test_reading = 550  # This should be >= early create window (500 - 50 = 450)
        asset_id = f"{content_type.app_label}.{content_type.model}.{equipment.id}"
        
        print(f"\nTesting meter reading: {test_reading} hours")
        print(f"Asset ID: {asset_id}")
        print(f"Early create window: {pm_settings.next_trigger_value - pm_settings.lead_time_value}")
        
        # Process the meter reading
        created_work_orders = PMAutomationService.process_meter_reading(
            asset_id=asset_id,
            meter_reading_value=test_reading,
            meter_reading_unit='hours',
            user=user
        )
        
        if created_work_orders:
            print(f"✅ Successfully created {len(created_work_orders)} work order(s)")
            for wo in created_work_orders:
                print(f"  - Work Order {wo.id}: {wo.description}")
        else:
            print("❌ No work orders were created")
        
        # Check PM status
        status = PMAutomationService.get_asset_pm_status(asset_id)
        if status:
            print(f"\nPM Status:")
            print(f"  - Next trigger: {status['next_trigger']}")
            print(f"  - Open work orders: {status['open_work_orders'].count()}")
            print(f"  - Pending triggers: {status['pending_triggers'].count()}")
            print(f"  - Is active: {status['is_active']}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pm_automation() 