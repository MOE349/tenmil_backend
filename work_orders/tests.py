from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from work_orders.models import WorkOrder, WorkOrderChecklist, WorkOrderStatusNames
from tenant_users.models import TenantUser
from core.models import WorkOrderStatusControls
from datetime import datetime, timezone
import json


class WorkOrderChecklistTestCase(APITestCase):
    """Test cases for WorkOrderChecklist CRUD operations"""
    
    def setUp(self):
        """Set up test data"""
        # Create tenant user
        self.user = TenantUser.objects.create(
            email='test@example.com',
            name='Test User',
            tenant_id=1  # Assuming tenant exists
        )
        
        # Create work order status
        self.status_control = WorkOrderStatusControls.objects.create(
            key='active',
            name='Active',
            color='#4caf50',
            order=1
        )
        self.status = WorkOrderStatusNames.objects.create(
            name='Active',
            control=self.status_control
        )
        
        # Create content type for asset
        self.content_type = ContentType.objects.get_for_model(WorkOrder)
        
        # Create work order
        self.work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id='12345678-1234-1234-1234-123456789012',
            status=self.status,
            maint_type='PM',
            description='Test work order'
        )
        
        # Create checklist item
        self.checklist_item = WorkOrderChecklist.objects.create(
            work_order=self.work_order,
            description='Test checklist item',
            hrs_spent=2
        )
    
    def test_list_checklists(self):
        """Test GET /work_orders/:work_order_id/checklists"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['description'], 'Test checklist item')
        self.assertEqual(response.data[0]['hrs_spent'], 2)
    
    def test_create_checklist_minimal_fields(self):
        """Test POST /work_orders/:work_order_id/checklists with minimal fields"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        data = {
            'description': 'New checklist item'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], 'New checklist item')
        self.assertIsNone(response.data['hrs_spent'])
        self.assertIsNone(response.data['completed_by'])
        self.assertIsNone(response.data['completion_date'])
    
    def test_create_checklist_all_fields(self):
        """Test POST /work_orders/:work_order_id/checklists with all fields"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        data = {
            'description': 'Complete checklist item',
            'hrs_spent': 5,
            'completed_by_id': self.user.pk,
            'completion_date': '2024-01-15T10:30:00Z'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], 'Complete checklist item')
        self.assertEqual(response.data['hrs_spent'], 5)
        self.assertEqual(response.data['completed_by']['id'], self.user.pk)
    
    def test_create_checklist_invalid_hrs_spent(self):
        """Test POST with invalid hrs_spent (negative number)"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        data = {
            'description': 'Invalid checklist item',
            'hrs_spent': -1
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hrs_spent', response.data)
    
    def test_create_checklist_invalid_hrs_spent_type(self):
        """Test POST with invalid hrs_spent type (string instead of number)"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        data = {
            'description': 'Invalid checklist item',
            'hrs_spent': 'not_a_number'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hrs_spent', response.data)
    
    def test_update_checklist_description(self):
        """Test PATCH /work_orders/:work_order_id/checklists/:id with description"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': self.checklist_item.pk})
        data = {
            'description': 'Updated checklist item'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated checklist item')
    
    def test_update_checklist_hrs_spent(self):
        """Test PATCH /work_orders/:work_order_id/checklists/:id with hrs_spent"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': self.checklist_item.pk})
        data = {
            'hrs_spent': 8
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['hrs_spent'], 8)
    
    def test_update_checklist_completed_by(self):
        """Test PATCH /work_orders/:work_order_id/checklists/:id with completed_by"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': self.checklist_item.pk})
        data = {
            'completed_by_id': self.user.pk
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['completed_by']['id'], self.user.pk)
    
    def test_update_checklist_completion_date(self):
        """Test PATCH /work_orders/:work_order_id/checklists/:id with completion_date"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': self.checklist_item.pk})
        data = {
            'completion_date': '2024-01-20T15:45:00Z'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['completion_date'], '2024-01-20T15:45:00Z')
    
    def test_update_checklist_invalid_hrs_spent(self):
        """Test PATCH with invalid hrs_spent (negative number)"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': self.checklist_item.pk})
        data = {
            'hrs_spent': -5
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hrs_spent', response.data)
    
    def test_delete_checklist(self):
        """Test DELETE /work_orders/:work_order_id/checklists/:id"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': self.checklist_item.pk})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(WorkOrderChecklist.objects.filter(pk=self.checklist_item.pk).exists())
    
    def test_list_returns_correct_items(self):
        """Test that list returns only items for the specified work order"""
        # Create another work order with its own checklist
        other_work_order = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id='87654321-4321-4321-4321-210987654321',
            status=self.status,
            maint_type='CM',
            priority='high',
            description='Other work order'
        )
        other_checklist = WorkOrderChecklist.objects.create(
            work_order=other_work_order,
            description='Other checklist item',
            hrs_spent=3
        )
        
        # Test that only the first work order's checklist is returned
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['description'], 'Test checklist item')
        
        # Test that the other work order's checklist is not returned
        self.assertNotEqual(response.data[0]['description'], 'Other checklist item')
    
    def test_create_checklist_nonexistent_work_order(self):
        """Test POST to nonexistent work order returns 404"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': '99999999-9999-9999-9999-999999999999'})
        data = {
            'description': 'Test checklist item'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_nonexistent_checklist(self):
        """Test PATCH to nonexistent checklist returns 404"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': '99999999-9999-9999-9999-999999999999'})
        data = {
            'description': 'Updated checklist item'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_delete_nonexistent_checklist(self):
        """Test DELETE to nonexistent checklist returns 404"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk, 'pk': '99999999-9999-9999-9999-999999999999'})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class WorkOrderNestedLookupTestCase(TestCase):
    """Test cases for WorkOrder nested lookup filtering using ORM directly"""
    
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
        """Test filtering work orders by status__control__name='Active' using ORM"""
        work_orders = WorkOrder.objects.filter(status__control__name='Active')
        
        print(f"Found {work_orders.count()} work orders with Active status")
        for wo in work_orders:
            print(f"Work order: {wo.description}, Status: {wo.status.name}, Control: {wo.status.control.name}")
        
        self.assertEqual(work_orders.count(), 1)
        self.assertEqual(work_orders.first().description, 'Active work order')
    
    def test_filter_by_status_control_name_closed(self):
        """Test filtering work orders by status__control__name='Closed' using ORM"""
        work_orders = WorkOrder.objects.filter(status__control__name='Closed')
        
        self.assertEqual(work_orders.count(), 1)
        self.assertEqual(work_orders.first().description, 'Closed work order')
    
    def test_filter_by_status_control_name_nonexistent(self):
        """Test filtering work orders by nonexistent status__control__name using ORM"""
        work_orders = WorkOrder.objects.filter(status__control__name='Nonexistent')
        
        self.assertEqual(work_orders.count(), 0)
    
    def test_filter_by_status_name(self):
        """Test filtering work orders by status__name using ORM"""
        work_orders = WorkOrder.objects.filter(status__name='Active')
        
        self.assertEqual(work_orders.count(), 1)
        self.assertEqual(work_orders.first().description, 'Active work order')
    
    def test_filter_by_control_key(self):
        """Test filtering work orders by status__control__key using ORM"""
        work_orders = WorkOrder.objects.filter(status__control__key='active')
        
        self.assertEqual(work_orders.count(), 1)
        self.assertEqual(work_orders.first().description, 'Active work order')
    
    def test_list_all_work_orders(self):
        """Test listing all work orders without filters using ORM"""
        work_orders = WorkOrder.objects.all()
        
        self.assertEqual(work_orders.count(), 2)
    
    def test_debug_nested_lookup_issue(self):
        """Debug the nested lookup issue by testing the exact query that's failing"""
        # This test reproduces the exact issue from the error
        try:
            # Test the exact query that was failing in the API
            work_orders = WorkOrder.objects.filter(status__control__name='Active')
            count = work_orders.count()
            print(f"Successfully filtered by status__control__name='Active': {count} results")
            
            # Test with a different value to see if it's a specific value issue
            work_orders_closed = WorkOrder.objects.filter(status__control__name='Closed')
            count_closed = work_orders_closed.count()
            print(f"Successfully filtered by status__control__name='Closed': {count_closed} results")
            
            # Test the relationship manually
            active_status = WorkOrderStatusNames.objects.filter(control__name='Active').first()
            if active_status:
                print(f"Found active status: {active_status.name} with control: {active_status.control.name}")
                work_orders_manual = WorkOrder.objects.filter(status=active_status)
                print(f"Manual filter by status object: {work_orders_manual.count()} results")
            
        except Exception as e:
            print(f"Error in nested lookup test: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise
