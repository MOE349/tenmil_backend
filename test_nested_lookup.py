#!/usr/bin/env python
"""
Standalone test to debug the nested lookup issue
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
django.setup()

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from work_orders.models import WorkOrder, WorkOrderStatusNames
from core.models import WorkOrderStatusControls


class NestedLookupTest(TestCase):
    """Test nested lookup filtering"""
    
    def setUp(self):
        """Set up test data"""
        # Create status controls
        self.active_control = WorkOrderStatusControls.objects.create(
            key='active',
            name='Active',
            color='#4caf50',
            order=1
        )
        self.closed_control = WorkOrderStatusControls.objects.create(
            key='closed',
            name='Closed',
            color='#f44336',
            order=2
        )
        
        # Create status names
        self.active_status = WorkOrderStatusNames.objects.create(
            name='Active',
            control=self.active_control
        )
        self.closed_status = WorkOrderStatusNames.objects.create(
            name='Closed',
            control=self.closed_control
        )
        
        # Create content type for asset
        self.content_type = ContentType.objects.get_for_model(WorkOrder)
        
        # Create work orders with different statuses
        self.active_work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id='12345678-1234-1234-1234-123456789012',
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description='Active work order'
        )
        
        self.closed_work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id='87654321-4321-4321-4321-210987654321',
            status=self.closed_status,
            maint_type='CM',
            priority='high',
            description='Closed work order'
        )
    
    def test_filter_by_status_control_name_active(self):
        """Test filtering work orders by status__control__name='Active'"""
        print("Testing status__control__name='Active' filter...")
        
        try:
            work_orders = WorkOrder.objects.filter(status__control__name='Active')
            count = work_orders.count()
            print(f"Successfully filtered by status__control__name='Active': {count} results")
            
            for wo in work_orders:
                print(f"  - Work order: {wo.description}")
                print(f"    Status: {wo.status.name}")
                print(f"    Control: {wo.status.control.name}")
            
            self.assertEqual(count, 1)
            self.assertEqual(work_orders.first().description, 'Active work order')
            
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def test_filter_by_status_control_name_closed(self):
        """Test filtering work orders by status__control__name='Closed'"""
        print("Testing status__control__name='Closed' filter...")
        
        try:
            work_orders = WorkOrder.objects.filter(status__control__name='Closed')
            count = work_orders.count()
            print(f"Successfully filtered by status__control__name='Closed': {count} results")
            
            self.assertEqual(count, 1)
            self.assertEqual(work_orders.first().description, 'Closed work order')
            
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def test_filter_by_status_name(self):
        """Test filtering work orders by status__name"""
        print("Testing status__name filter...")
        
        try:
            work_orders = WorkOrder.objects.filter(status__name='Active')
            count = work_orders.count()
            print(f"Successfully filtered by status__name='Active': {count} results")
            
            self.assertEqual(count, 1)
            self.assertEqual(work_orders.first().description, 'Active work order')
            
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def test_manual_relationship_traversal(self):
        """Test manual relationship traversal"""
        print("Testing manual relationship traversal...")
        
        try:
            # Get all work orders
            all_work_orders = WorkOrder.objects.all()
            print(f"Total work orders: {all_work_orders.count()}")
            
            for wo in all_work_orders:
                print(f"Work order: {wo.description}")
                print(f"  Status: {wo.status.name}")
                print(f"  Control: {wo.status.control.name}")
                print(f"  Control key: {wo.status.control.key}")
            
            # Test the relationship manually
            active_status = WorkOrderStatusNames.objects.filter(control__name='Active').first()
            if active_status:
                print(f"Found active status: {active_status.name} with control: {active_status.control.name}")
                work_orders_manual = WorkOrder.objects.filter(status=active_status)
                print(f"Manual filter by status object: {work_orders_manual.count()} results")
            
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == '__main__':
    # Run the test
    import django.test.utils
    django.test.utils.setup_test_environment()
    
    test = NestedLookupTest()
    test.setUp()
    
    print("=" * 50)
    print("RUNNING NESTED LOOKUP TESTS")
    print("=" * 50)
    
    test.test_manual_relationship_traversal()
    test.test_filter_by_status_name()
    test.test_filter_by_status_control_name_closed()
    test.test_filter_by_status_control_name_active()
    
    print("=" * 50)
    print("TESTS COMPLETED")
    print("=" * 50) 