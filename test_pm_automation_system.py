#!/usr/bin/env python
"""
Comprehensive test script for PM Automation System
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

def test_pm_automation_system():
    """Test the complete PM automation system"""
    print("=== Testing PM Automation System ===")
    
    # 1. Setup test data
    print("\n1. Setting up test data...")
    
    # Create test site and location
    site, created = Site.objects.get_or_create(
        name="Test Site",
        defaults={'code': "TEST"}
    )
    print(f"Site: {site}")
    
    location, created = Location.objects.get_or_create(
        name="Test Location",
        defaults={'slug': "test-location", 'site': site}
    )
    print(f"Location: {location}")
    
    # Create test category
    category, created = EquipmentCategory.objects.get_or_create(
        name="Test Category",
        defaults={'slug': "test-category"}
    )
    print(f"Category: {category}")
    
    # Create test equipment
    equipment, created = Equipment.objects.get_or_create(
        code="TEST001",
        defaults={
            'name': "Test Equipment",
            'description': "Test equipment for PM automation",
            'location': location,
            'category': category
        }
    )
    print(f"Equipment: {equipment}")
    
    # Get or create test user
    user = TenantUser.objects.first()
    if not user:
        print("No users found. Please create a user first.")
        return
    print(f"User: {user}")
    
    # 2. Create PM Settings
    print("\n2. Creating PM Settings...")
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
        print(f"✅ Created PM settings: {pm_settings}")
    else:
        print(f"✅ Using existing PM settings: {pm_settings}")
    
    # 3. Test meter reading that should trigger PM
    print("\n3. Testing meter reading that should trigger PM...")
    test_reading = 550  # This should be >= early create window (500 - 50 = 450)
    asset_id = f"{content_type.app_label}.{content_type.model}.{equipment.id}"
    
    print(f"Test reading: {test_reading} hours")
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
    
    # 4. Check PM status
    print("\n4. Checking PM status...")
    status = PMAutomationService.get_asset_pm_status(asset_id)
    if status:
        print(f"✅ PM Status:")
        print(f"  - PM Settings Count: {status['pm_settings_count']}")
        print(f"  - Has Active Settings: {status['has_active_settings']}")
        print(f"  - Open Work Orders: {status['open_work_orders'].count()}")
        print(f"  - Pending Triggers: {status['pending_triggers'].count()}")
    else:
        print("❌ No PM status found")
    
    # 5. Test meter reading that should NOT trigger PM
    print("\n5. Testing meter reading that should NOT trigger PM...")
    low_reading = 400  # This should be < early create window (500 - 50 = 450)
    
    print(f"Low reading: {low_reading} hours")
    print(f"Early create window: {pm_settings.next_trigger_value - pm_settings.lead_time_value}")
    
    created_work_orders_low = PMAutomationService.process_meter_reading(
        asset_id=asset_id,
        meter_reading_value=low_reading,
        meter_reading_unit='hours',
        user=user
    )
    
    if created_work_orders_low:
        print(f"❌ Unexpectedly created {len(created_work_orders_low)} work order(s)")
    else:
        print("✅ Correctly did not create work orders for low reading")
    
    # 6. Test work order completion
    print("\n6. Testing work order completion...")
    if created_work_orders:
        work_order = created_work_orders[0]
        completion_reading = 600
        
        print(f"Completing work order {work_order.id} with reading {completion_reading}")
        
        # Update work order to closed status
        from work_orders.models import WorkOrderStatusNames
        closed_status = WorkOrderStatusNames.objects.filter(control__name='Closed').first()
        if not closed_status:
            from core.models import WorkOrderStatusControls
            closed_control = WorkOrderStatusControls.objects.filter(key='closed').first()
            if not closed_control:
                closed_control = WorkOrderStatusControls.objects.create(
                    key='closed',
                    name='Closed',
                    color='#f44336',
                    order=2
                )
            closed_status = WorkOrderStatusNames.objects.create(
                name='Closed',
                control=closed_control
            )
        
        work_order.status = closed_status
        work_order.is_closed = True
        work_order.completion_meter_reading = completion_reading
        work_order.save()
        
        print(f"✅ Updated work order {work_order.id} to closed status")
        
        # Check if PM settings were updated
        pm_settings.refresh_from_db()
        print(f"✅ PM Settings next trigger updated to: {pm_settings.next_trigger_value}")
    
    print("\n=== PM Automation System Test Complete ===")

if __name__ == "__main__":
    test_pm_automation_system() 