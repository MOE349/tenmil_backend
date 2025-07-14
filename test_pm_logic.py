#!/usr/bin/env python
"""
Test script for PM Automation logic (without database)
"""
import sys
import os

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Mock the necessary components for testing
class MockPMSettings:
    def __init__(self, interval_value=100, interval_unit='hours', 
                 start_threshold_value=500, lead_time_value=50, is_active=True):
        self.interval_value = interval_value
        self.interval_unit = interval_unit
        self.start_threshold_value = start_threshold_value
        self.lead_time_value = lead_time_value
        self.is_active = is_active
        self.next_trigger_value = start_threshold_value
        self.last_handled_trigger = None
    
    def get_next_trigger(self):
        return self.next_trigger_value
    
    def update_next_trigger(self, closing_value):
        self.next_trigger_value = closing_value + self.interval_value
        self.last_handled_trigger = closing_value

def test_pm_logic():
    """Test PM automation logic without database"""
    print("=== Testing PM Automation Logic ===")
    
    # Test case 1: Basic trigger calculation
    print("\n--- Test Case 1: Basic Trigger Calculation ---")
    pm_settings = MockPMSettings(
        interval_value=100,
        interval_unit='hours',
        start_threshold_value=500,
        lead_time_value=50
    )
    
    current_reading = 550
    early_create_window = pm_settings.next_trigger_value - pm_settings.lead_time_value
    
    print(f"PM Settings:")
    print(f"  - Interval: {pm_settings.interval_value} {pm_settings.interval_unit}")
    print(f"  - Start threshold: {pm_settings.start_threshold_value} {pm_settings.interval_unit}")
    print(f"  - Lead time: {pm_settings.lead_time_value} {pm_settings.interval_unit}")
    print(f"  - Next trigger: {pm_settings.next_trigger_value}")
    print(f"  - Early create window: {early_create_window}")
    print(f"  - Current reading: {current_reading}")
    
    # Calculate triggers
    triggers = []
    next_trigger = pm_settings.get_next_trigger()
    
    while next_trigger <= current_reading:
        if pm_settings.last_handled_trigger is None or next_trigger > pm_settings.last_handled_trigger:
            triggers.append(next_trigger)
        next_trigger += pm_settings.interval_value
    
    print(f"Calculated triggers: {triggers}")
    
    # Check early create window
    for trigger in triggers:
        early_window = trigger - pm_settings.lead_time_value
        should_create = current_reading >= early_window
        print(f"Trigger {trigger}: early window = {early_window}, should create = {should_create}")
    
    # Test case 2: Multiple triggers
    print("\n--- Test Case 2: Multiple Triggers ---")
    pm_settings2 = MockPMSettings(
        interval_value=50,
        interval_unit='hours',
        start_threshold_value=100,
        lead_time_value=25
    )
    
    current_reading2 = 200
    early_create_window2 = pm_settings2.next_trigger_value - pm_settings2.lead_time_value
    
    print(f"PM Settings:")
    print(f"  - Interval: {pm_settings2.interval_value} {pm_settings2.interval_unit}")
    print(f"  - Start threshold: {pm_settings2.start_threshold_value} {pm_settings2.interval_unit}")
    print(f"  - Lead time: {pm_settings2.lead_time_value} {pm_settings2.interval_unit}")
    print(f"  - Next trigger: {pm_settings2.next_trigger_value}")
    print(f"  - Early create window: {early_create_window2}")
    print(f"  - Current reading: {current_reading2}")
    
    # Calculate triggers
    triggers2 = []
    next_trigger2 = pm_settings2.get_next_trigger()
    
    while next_trigger2 <= current_reading2:
        if pm_settings2.last_handled_trigger is None or next_trigger2 > pm_settings2.last_handled_trigger:
            triggers2.append(next_trigger2)
        next_trigger2 += pm_settings2.interval_value
    
    print(f"Calculated triggers: {triggers2}")
    
    # Check early create window for each trigger
    for trigger in triggers2:
        early_window = trigger - pm_settings2.lead_time_value
        should_create = current_reading2 >= early_window
        print(f"Trigger {trigger}: early window = {early_window}, should create = {should_create}")
    
    # Test case 3: Edge case - reading just below early window
    print("\n--- Test Case 3: Edge Case ---")
    pm_settings3 = MockPMSettings(
        interval_value=100,
        interval_unit='hours',
        start_threshold_value=500,
        lead_time_value=50
    )
    
    current_reading3 = 449  # Just below early window (500 - 50 = 450)
    early_create_window3 = pm_settings3.next_trigger_value - pm_settings3.lead_time_value
    
    print(f"Current reading: {current_reading3}")
    print(f"Early create window: {early_create_window3}")
    print(f"Should create: {current_reading3 >= early_create_window3}")
    
    print("\n✅ PM Logic Tests Completed!")

if __name__ == "__main__":
    test_pm_logic() 