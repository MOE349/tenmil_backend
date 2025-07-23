from django.test import TestCase
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from pm_automation.models import PMSettings, PMIteration, PMIterationChecklist, PMUnitChoices
from work_orders.models import WorkOrder, WorkOrderChecklist, WorkOrderStatusNames
from core.models import WorkOrderStatusControls
from pm_automation.services import PMAutomationService
from pm_automation.signals import handle_pm_settings_save
from django.db.models.signals import post_save
import uuid

User = get_user_model()


class PMIterationSystemTestCase(TestCase):
    """Test cases for the PM Iteration System"""
    
    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        
        # Create work order status control and status
        self.status_control = WorkOrderStatusControls.objects.create(
            key='active',
            name='Active',
            color='#4caf50',
            order=1
        )
        self.active_status = WorkOrderStatusNames.objects.create(
            name='Active',
            control=self.status_control
        )
        
        # Create a mock asset content type (using User as a proxy)
        self.content_type = ContentType.objects.get_for_model(User)
        self.asset_id = str(uuid.uuid4())
        
        # Create PM Settings with 500 hour interval
        self.pm_settings = PMSettings.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            name="Preventive Maintenance",
            interval_value=500,
            interval_unit=PMUnitChoices.HOURS,
            start_threshold_value=0,
            start_threshold_unit=PMUnitChoices.HOURS,
            lead_time_value=10,
            lead_time_unit=PMUnitChoices.HOURS,
            is_active=True
        )
        
        # Create iterations manually (since signal might not work in tests)
        self.iteration_500 = PMIteration.objects.create(
            pm_settings=self.pm_settings,
            interval_value=500,
            name="500 Hours"
        )
        
        self.iteration_1000 = PMIteration.objects.create(
            pm_settings=self.pm_settings,
            interval_value=1000,
            name="1000 Hours"
        )
        
        self.iteration_2000 = PMIteration.objects.create(
            pm_settings=self.pm_settings,
            interval_value=2000,
            name="2000 Hours"
        )
        
        # Create checklist items for each iteration
        self.checklist_500 = PMIterationChecklist.objects.create(
            iteration=self.iteration_500,
            name="Change oil"
        )
        
        self.checklist_1000 = PMIterationChecklist.objects.create(
            iteration=self.iteration_1000,
            name="Change filter"
        )
        
        self.checklist_2000 = PMIterationChecklist.objects.create(
            iteration=self.iteration_2000,
            name="Sample oil"
        )
    
    def test_iteration_creation_and_ordering(self):
        """Test that iterations are created with proper ordering"""
        iterations = list(self.pm_settings.get_iterations())
        
        self.assertEqual(len(iterations), 3)
        self.assertEqual(iterations[0].interval_value, 500)
        self.assertEqual(iterations[1].interval_value, 1000)
        self.assertEqual(iterations[2].interval_value, 2000)
    
    def test_cumulative_checklist_for_500_hours(self):
        """Test that 500 hour iteration only includes its own checklist"""
        checklist_items = self.pm_settings.get_cumulative_checklist_for_iteration(self.iteration_500)
        
        self.assertEqual(len(checklist_items), 1)
        self.assertEqual(checklist_items[0].name, "Change oil")
    
    def test_cumulative_checklist_for_1000_hours(self):
        """Test that 1000 hour iteration includes 500 + 1000 hour checklists"""
        checklist_items = self.pm_settings.get_cumulative_checklist_for_iteration(self.iteration_1000)
        
        self.assertEqual(len(checklist_items), 2)
        checklist_names = [item.name for item in checklist_items]
        self.assertIn("Change oil", checklist_names)
        self.assertIn("Change filter", checklist_names)
    
    def test_cumulative_checklist_for_2000_hours(self):
        """Test that 2000 hour iteration includes all checklists"""
        checklist_items = self.pm_settings.get_cumulative_checklist_for_iteration(self.iteration_2000)
        
        self.assertEqual(len(checklist_items), 3)
        checklist_names = [item.name for item in checklist_items]
        self.assertIn("Change oil", checklist_names)
        self.assertIn("Change filter", checklist_names)
        self.assertIn("Sample oil", checklist_names)
    
    def test_initial_iteration_index(self):
        """Test that PM Settings starts with iteration index 0"""
        self.assertEqual(self.pm_settings.current_iteration_index, 0)
        current_iteration = self.pm_settings.get_current_iteration()
        self.assertEqual(current_iteration, self.iteration_500)
    
    def test_iteration_cycling(self):
        """Test that iterations cycle through in order"""
        # Start at 500 hours
        current = self.pm_settings.get_current_iteration()
        self.assertEqual(current, self.iteration_500)
        
        # Advance to 1000 hours
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertEqual(next_iteration, self.iteration_1000)
        self.assertEqual(self.pm_settings.current_iteration_index, 1)
        
        # Advance to 2000 hours
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertEqual(next_iteration, self.iteration_2000)
        self.assertEqual(self.pm_settings.current_iteration_index, 2)
        
        # Cycle back to 500 hours
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertEqual(next_iteration, self.iteration_500)
        self.assertEqual(self.pm_settings.current_iteration_index, 0)
    
    def test_work_order_creation_with_500_hour_checklist(self):
        """Test work order creation for 500 hour iteration"""
        # Set current iteration to 500 hours
        self.pm_settings.current_iteration_index = 0
        self.pm_settings.save()
        
        # Create work order
        work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="Test PM Work Order",
            is_auto_generated=True,
            trigger_meter_reading=500
        )
        
        # Copy checklist to work order
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order, self.iteration_500)
        
        # Verify checklist items
        checklist_items = WorkOrderChecklist.objects.filter(work_order=work_order)
        self.assertEqual(checklist_items.count(), 1)
        self.assertEqual(checklist_items[0].description, "Change oil")
        self.assertEqual(checklist_items[0].source_pm_iteration_checklist, self.checklist_500)
        self.assertFalse(checklist_items[0].is_custom)
    
    def test_work_order_creation_with_1000_hour_checklist(self):
        """Test work order creation for 1000 hour iteration"""
        # Set current iteration to 1000 hours
        self.pm_settings.current_iteration_index = 1
        self.pm_settings.save()
        
        # Create work order
        work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="Test PM Work Order",
            is_auto_generated=True,
            trigger_meter_reading=1000
        )
        
        # Copy checklist to work order
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order, self.iteration_1000)
        
        # Verify checklist items (should include both 500 and 1000 hour items)
        checklist_items = WorkOrderChecklist.objects.filter(work_order=work_order)
        self.assertEqual(checklist_items.count(), 2)
        
        checklist_descriptions = [item.description for item in checklist_items]
        self.assertIn("Change oil", checklist_descriptions)
        self.assertIn("Change filter", checklist_descriptions)
        
        # Verify sources
        oil_item = checklist_items.filter(description="Change oil").first()
        filter_item = checklist_items.filter(description="Change filter").first()
        self.assertEqual(oil_item.source_pm_iteration_checklist, self.checklist_500)
        self.assertEqual(filter_item.source_pm_iteration_checklist, self.checklist_1000)
    
    def test_work_order_creation_with_2000_hour_checklist(self):
        """Test work order creation for 2000 hour iteration"""
        # Set current iteration to 2000 hours
        self.pm_settings.current_iteration_index = 2
        self.pm_settings.save()
        
        # Create work order
        work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="Test PM Work Order",
            is_auto_generated=True,
            trigger_meter_reading=2000
        )
        
        # Copy checklist to work order
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order, self.iteration_2000)
        
        # Verify checklist items (should include all three items)
        checklist_items = WorkOrderChecklist.objects.filter(work_order=work_order)
        self.assertEqual(checklist_items.count(), 3)
        
        checklist_descriptions = [item.description for item in checklist_items]
        self.assertIn("Change oil", checklist_descriptions)
        self.assertIn("Change filter", checklist_descriptions)
        self.assertIn("Sample oil", checklist_descriptions)
    
    def test_full_pm_cycle_simulation(self):
        """Test the complete PM cycle as described in the example"""
        # Simulate the complete cycle from the example
        
        # 1. 500 hours - should create work order with "Change oil"
        self.pm_settings.current_iteration_index = 0
        self.pm_settings.save()
        
        work_order_500 = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="PM at 500 hours",
            is_auto_generated=True,
            trigger_meter_reading=500
        )
        
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order_500, self.iteration_500)
        
        # Verify 500 hour work order
        checklist_500 = WorkOrderChecklist.objects.filter(work_order=work_order_500)
        self.assertEqual(checklist_500.count(), 1)
        self.assertEqual(checklist_500[0].description, "Change oil")
        
        # Complete 500 hour work order and advance iteration
        work_order_500.is_closed = True
        work_order_500.completion_meter_reading = 500
        work_order_500.save()
        
        # Advance to next iteration (should be 1000 hours)
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertEqual(next_iteration, self.iteration_1000)
        
        # 2. 1000 hours - should create work order with "Change oil" + "Change filter"
        work_order_1000 = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="PM at 1000 hours",
            is_auto_generated=True,
            trigger_meter_reading=1000
        )
        
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order_1000, self.iteration_1000)
        
        # Verify 1000 hour work order
        checklist_1000 = WorkOrderChecklist.objects.filter(work_order=work_order_1000)
        self.assertEqual(checklist_1000.count(), 2)
        checklist_names_1000 = [item.description for item in checklist_1000]
        self.assertIn("Change oil", checklist_names_1000)
        self.assertIn("Change filter", checklist_names_1000)
        
        # Complete 1000 hour work order and advance iteration
        work_order_1000.is_closed = True
        work_order_1000.completion_meter_reading = 1000
        work_order_1000.save()
        
        # Advance to next iteration (should be 2000 hours)
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertEqual(next_iteration, self.iteration_2000)
        
        # 3. 2000 hours - should create work order with all three items
        work_order_2000 = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="PM at 2000 hours",
            is_auto_generated=True,
            trigger_meter_reading=2000
        )
        
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order_2000, self.iteration_2000)
        
        # Verify 2000 hour work order
        checklist_2000 = WorkOrderChecklist.objects.filter(work_order=work_order_2000)
        self.assertEqual(checklist_2000.count(), 3)
        checklist_names_2000 = [item.description for item in checklist_2000]
        self.assertIn("Change oil", checklist_names_2000)
        self.assertIn("Change filter", checklist_names_2000)
        self.assertIn("Sample oil", checklist_names_2000)
        
        # Complete 2000 hour work order and advance iteration
        work_order_2000.is_closed = True
        work_order_2000.completion_meter_reading = 2000
        work_order_2000.save()
        
        # Advance to next iteration (should cycle back to 500 hours)
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertEqual(next_iteration, self.iteration_500)
        self.assertEqual(self.pm_settings.current_iteration_index, 0)
    
    def test_iteration_validation(self):
        """Test that only valid interval multiples can be added"""
        # Try to create an iteration with invalid interval (750 hours is not a multiple of 500)
        with self.assertRaises(Exception):
            PMIteration.objects.create(
                pm_settings=self.pm_settings,
                interval_value=750,  # Not a multiple of 500
                name="750 Hours"
            )
        
        # Valid iterations should work
        iteration_1500 = PMIteration.objects.create(
            pm_settings=self.pm_settings,
            interval_value=1500,  # 3 * 500
            name="1500 Hours"
        )
        self.assertIsNotNone(iteration_1500)
    
    def test_custom_checklist_items(self):
        """Test that users can add custom checklist items to work orders"""
        work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="Test PM Work Order",
            is_auto_generated=True,
            trigger_meter_reading=500
        )
        
        # Add iteration checklist items
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order, self.iteration_500)
        
        # Add custom checklist item
        custom_item = WorkOrderChecklist.objects.create(
            work_order=work_order,
            description="Custom task added by user",
            is_custom=True
        )
        
        # Verify both iteration and custom items exist
        all_items = WorkOrderChecklist.objects.filter(work_order=work_order)
        self.assertEqual(all_items.count(), 2)
        
        iteration_items = all_items.filter(is_custom=False)
        custom_items = all_items.filter(is_custom=True)
        
        self.assertEqual(iteration_items.count(), 1)
        self.assertEqual(custom_items.count(), 1)
        self.assertEqual(custom_items[0].description, "Custom task added by user")


class PMIterationEdgeCasesTestCase(TestCase):
    """Test edge cases for the PM Iteration System"""
    
    def setUp(self):
        """Set up test data for edge cases"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            name='Test User'
        )
        
        self.status_control = WorkOrderStatusControls.objects.create(
            key='active',
            name='Active',
            color='#4caf50',
            order=1
        )
        self.active_status = WorkOrderStatusNames.objects.create(
            name='Active',
            control=self.status_control
        )
        
        self.content_type = ContentType.objects.get_for_model(User)
        self.asset_id = str(uuid.uuid4())
        
        # Create PM Settings with no iterations initially
        self.pm_settings = PMSettings.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            name="Edge Case PM",
            interval_value=100,
            interval_unit=PMUnitChoices.HOURS,
            start_threshold_value=0,
            start_threshold_unit=PMUnitChoices.HOURS,
            lead_time_value=10,
            lead_time_unit=PMUnitChoices.HOURS,
            is_active=True
        )
    
    def test_no_iterations_handling(self):
        """Test behavior when no iterations exist"""
        # Try to get current iteration when none exist
        current_iteration = self.pm_settings.get_current_iteration()
        self.assertIsNone(current_iteration)
        
        # Try to advance iteration when none exist
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertIsNone(next_iteration)
        
        # Try to get cumulative checklist when no iterations exist
        checklist_items = self.pm_settings.get_cumulative_checklist_for_iteration(None)
        self.assertEqual(checklist_items, [])
    
    def test_single_iteration_cycling(self):
        """Test cycling with only one iteration"""
        # Create single iteration
        iteration = PMIteration.objects.create(
            pm_settings=self.pm_settings,
            interval_value=100,
            name="100 Hours"
        )
        
        # Should always return the same iteration
        current = self.pm_settings.get_current_iteration()
        self.assertEqual(current, iteration)
        
        # Advancing should still return the same iteration
        next_iteration = self.pm_settings.advance_to_next_iteration()
        self.assertEqual(next_iteration, iteration)
        self.assertEqual(self.pm_settings.current_iteration_index, 0)
    
    def test_iteration_with_no_checklist(self):
        """Test iteration that has no checklist items"""
        iteration = PMIteration.objects.create(
            pm_settings=self.pm_settings,
            interval_value=100,
            name="100 Hours"
        )
        
        # Get cumulative checklist for iteration with no items
        checklist_items = self.pm_settings.get_cumulative_checklist_for_iteration(iteration)
        self.assertEqual(checklist_items, [])
        
        # Create work order and copy checklist
        work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id=self.asset_id,
            status=self.active_status,
            maint_type='PM',
            priority='medium',
            description="Test PM Work Order",
            is_auto_generated=True,
            trigger_meter_reading=100
        )
        
        # Should not raise error even with no checklist items
        self.pm_settings.copy_iteration_checklist_to_work_order(work_order, iteration)
        
        # No checklist items should be created
        checklist_items = WorkOrderChecklist.objects.filter(work_order=work_order)
        self.assertEqual(checklist_items.count(), 0)
