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
            priority='medium',
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
            'description': 'Test item',
            'hrs_spent': -1
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hrs_spent', response.data)
    
    def test_create_checklist_invalid_hrs_spent_type(self):
        """Test POST with invalid hrs_spent (non-numeric)"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        data = {
            'description': 'Test item',
            'hrs_spent': 'invalid'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hrs_spent', response.data)
    
    def test_update_checklist_description(self):
        """Test PUT /work_order_checklists/:checklist_id - update description"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': self.checklist_item.pk})
        data = {
            'description': 'Updated description'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated description')
        self.assertEqual(response.data['hrs_spent'], 2)  # Should remain unchanged
    
    def test_update_checklist_hrs_spent(self):
        """Test PUT /work_order_checklists/:checklist_id - update hrs_spent"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': self.checklist_item.pk})
        data = {
            'hrs_spent': 8
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['hrs_spent'], 8)
        self.assertEqual(response.data['description'], 'Test checklist item')  # Should remain unchanged
    
    def test_update_checklist_completed_by(self):
        """Test PUT /work_order_checklists/:checklist_id - update completed_by"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': self.checklist_item.pk})
        data = {
            'completed_by_id': self.user.pk
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['completed_by']['id'], self.user.pk)
    
    def test_update_checklist_completion_date(self):
        """Test PUT /work_order_checklists/:checklist_id - update completion_date"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': self.checklist_item.pk})
        data = {
            'completion_date': '2024-01-15T10:30:00Z'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['completion_date'])
    
    def test_update_checklist_invalid_hrs_spent(self):
        """Test PUT with invalid hrs_spent"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': self.checklist_item.pk})
        data = {
            'hrs_spent': -5
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hrs_spent', response.data)
    
    def test_delete_checklist(self):
        """Test DELETE /work_order_checklists/:checklist_id"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': self.checklist_item.pk})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify the item is actually deleted
        self.assertFalse(WorkOrderChecklist.objects.filter(pk=self.checklist_item.pk).exists())
    
    def test_list_returns_correct_items(self):
        """Test that list returns only items for the specific work order"""
        # Create another work order
        work_order_2 = WorkOrder.objects.create(
            content_type=self.content_type,
            object_id='87654321-4321-4321-4321-210987654321',
            status=self.status,
            maint_type='PM',
            priority='medium',
            description='Another work order'
        )
        
        # Create checklist item for second work order
        WorkOrderChecklist.objects.create(
            work_order=work_order_2,
            description='Item for work order 2',
            hrs_spent=3
        )
        
        # List checklists for first work order
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': self.work_order.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['description'], 'Test checklist item')
    
    def test_create_checklist_nonexistent_work_order(self):
        """Test creating checklist for non-existent work order"""
        url = reverse('WorkOrderChecklist', kwargs={'work_order_pk': '99999999-9999-9999-9999-999999999999'})
        data = {
            'description': 'Test item'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_nonexistent_checklist(self):
        """Test updating non-existent checklist"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': '99999999-9999-9999-9999-999999999999'})
        data = {
            'description': 'Updated description'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_delete_nonexistent_checklist(self):
        """Test deleting non-existent checklist"""
        url = reverse('WorkOrderChecklist', kwargs={'pk': '99999999-9999-9999-9999-999999999999'})
        
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
