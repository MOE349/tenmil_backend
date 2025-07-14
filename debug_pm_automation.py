#!/usr/bin/env python
"""
Debug script for PM Automation issues
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
django.setup()

from pm_automation.models import PMSettings, PMTrigger
from meter_readings.models import MeterReading
from work_orders.models import WorkOrder
from assets.models import Equipment
from tenant_users.models import TenantUser
from django.contrib.contenttypes.models import ContentType
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_pm_automation():
    """Debug PM automation issues"""
    print("=== PM Automation Debug Report ===")
    
    # 1. Check PM Settings
    print("\n1. PM Settings Analysis:")
    pm_settings = PMSettings.objects.all()
    print(f"Total PM Settings: {pm_settings.count()}")
    
    for pm in pm_settings:
        print(f"  - ID: {pm.id}")
        print(f"    Asset: {pm.asset}")
        print(f"    Active: {pm.is_active}")
        print(f"    Interval: {pm.interval_value} {pm.interval_unit}")
        print(f"    Start Threshold: {pm.start_threshold_value} {pm.start_threshold_unit}")
        print(f"    Lead Time: {pm.lead_time_value} {pm.lead_time_unit}")
        print(f"    Next Trigger: {pm.next_trigger_value}")
        print(f"    Last Handled: {pm.last_handled_trigger}")
        print()
    
    # 2. Check PM Triggers
    print("\n2. PM Triggers Analysis:")
    triggers = PMTrigger.objects.all()
    print(f"Total PM Triggers: {triggers.count()}")
    
    for trigger in triggers:
        print(f"  - ID: {trigger.id}")
        print(f"    PM Settings: {trigger.pm_settings.id}")
        print(f"    Trigger Value: {trigger.trigger_value} {trigger.trigger_unit}")
        print(f"    Work Order: {trigger.work_order.id if trigger.work_order else 'None'}")
        print(f"    Handled: {trigger.is_handled}")
        print()
    
    # 3. Check Meter Readings
    print("\n3. Recent Meter Readings:")
    recent_readings = MeterReading.objects.all().order_by('-created_at')[:5]
    print(f"Recent Meter Readings: {recent_readings.count()}")
    
    for reading in recent_readings:
        print(f"  - ID: {reading.id}")
        print(f"    Asset: {reading.asset}")
        print(f"    Reading: {reading.meter_reading}")
        print(f"    Created: {reading.created_at}")
        print(f"    Created By: {reading.created_by}")
        print()
    
    # 4. Check PM Work Orders
    print("\n4. PM Work Orders:")
    pm_work_orders = WorkOrder.objects.filter(maint_type='PM')
    print(f"PM Work Orders: {pm_work_orders.count()}")
    
    for wo in pm_work_orders:
        print(f"  - ID: {wo.id}")
        print(f"    Code: {wo.code}")
        print(f"    Asset: {wo.asset}")
        print(f"    Status: {wo.status.name}")
        print(f"    Closed: {wo.is_closed}")
        print(f"    Description: {wo.description}")
        print()
    
    # 5. Check for duplicate PM settings
    print("\n5. Duplicate PM Settings Check:")
    content_types = ContentType.objects.filter(
        app_label__in=['assets']
    )
    
    for ct in content_types:
        pm_count = PMSettings.objects.filter(content_type=ct).count()
        if pm_count > 1:
            print(f"  ⚠️  Content Type {ct.app_label}.{ct.model} has {pm_count} PM settings")
            pms = PMSettings.objects.filter(content_type=ct)
            for pm in pms:
                print(f"    - PM Settings ID: {pm.id}, Asset: {pm.asset}")
        else:
            print(f"  ✅ Content Type {ct.app_label}.{ct.model} has {pm_count} PM settings")
    
    # 6. Test PM Automation Logic
    print("\n6. PM Automation Logic Test:")
    if pm_settings.exists():
        pm = pm_settings.first()
        print(f"Testing with PM Settings ID: {pm.id}")
        print(f"Asset: {pm.asset}")
        print(f"Interval: {pm.interval_value} {pm.interval_unit}")
        print(f"Start Threshold: {pm.start_threshold_value}")
        print(f"Lead Time: {pm.lead_time_value}")
        print(f"Next Trigger: {pm.next_trigger_value}")
        
        # Calculate early create window
        early_window = pm.next_trigger_value - pm.lead_time_value
        print(f"Early Create Window: {early_window}")
        
        # Test with different meter readings
        test_readings = [early_window - 10, early_window, early_window + 10]
        for reading in test_readings:
            should_create = reading >= early_window
            print(f"  Meter Reading {reading}: Should create = {should_create}")
    
    print("\n=== Debug Report Complete ===")

def fix_duplicate_pm_settings():
    """Fix duplicate PM settings by keeping only the most recent one"""
    print("\n=== Fixing Duplicate PM Settings ===")
    
    content_types = ContentType.objects.filter(
        app_label__in=['assets']
    )
    
    for ct in content_types:
        pm_settings = PMSettings.objects.filter(content_type=ct)
        if pm_settings.count() > 1:
            print(f"Found {pm_settings.count()} PM settings for {ct.app_label}.{ct.model}")
            
            # Keep the most recent one
            latest_pm = pm_settings.order_by('-created_at').first()
            duplicates = pm_settings.exclude(id=latest_pm.id)
            
            print(f"Keeping PM Settings ID: {latest_pm.id}")
            print(f"Deleting {duplicates.count()} duplicates")
            
            for duplicate in duplicates:
                print(f"  - Deleting PM Settings ID: {duplicate.id}")
                duplicate.delete()
    
    print("Duplicate PM settings cleanup complete!")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "fix":
        fix_duplicate_pm_settings()
    else:
        debug_pm_automation() 