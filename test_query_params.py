#!/usr/bin/env python
"""
Test the query parameter processing logic
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.contrib.contenttypes.models import ContentType
from work_orders.models import WorkOrder
from configurations.base_features.views.base_api_view import BaseAPIView
from work_orders.platforms.base.views import WorkOrderBaseView


class QueryParamsTest(TestCase):
    """Test query parameter processing"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.view = WorkOrderBaseView()
        self.view.model_class = WorkOrder
    
    def test_get_request_params_nested_lookup(self):
        """Test that nested lookups are passed through correctly"""
        # Create a mock request with nested lookup
        request = self.factory.get('/work-orders/work-order?status__control__name=Active')
        
        # Test the get_request_params method
        params = self.view.get_request_params(request)
        
        print(f"Query params: {dict(request.GET)}")
        print(f"Processed params: {params}")
        
        # The nested lookup should be passed through as-is
        self.assertIn('status__control__name', params)
        self.assertEqual(params['status__control__name'], 'Active')
    
    def test_get_request_params_simple_lookup(self):
        """Test that simple lookups work correctly"""
        # Create a mock request with simple lookup
        request = self.factory.get('/work-orders/work-order?description=test')
        
        # Test the get_request_params method
        params = self.view.get_request_params(request)
        
        print(f"Query params: {dict(request.GET)}")
        print(f"Processed params: {params}")
        
        # Simple lookups should get __icontains added
        self.assertIn('description__icontains', params)
        self.assertEqual(params['description__icontains'], 'test')
    
    def test_get_request_params_mixed_lookups(self):
        """Test mixed simple and nested lookups"""
        # Create a mock request with both types of lookups
        request = self.factory.get('/work-orders/work-order?status__control__name=Active&description=test&priority=high')
        
        # Test the get_request_params method
        params = self.view.get_request_params(request)
        
        print(f"Query params: {dict(request.GET)}")
        print(f"Processed params: {params}")
        
        # Nested lookup should be passed through as-is
        self.assertIn('status__control__name', params)
        self.assertEqual(params['status__control__name'], 'Active')
        
        # Simple lookups should get __icontains added
        self.assertIn('description__icontains', params)
        self.assertEqual(params['description__icontains'], 'test')
        self.assertIn('priority__icontains', params)
        self.assertEqual(params['priority__icontains'], 'high')
    
    def test_get_request_params_multiple_nested(self):
        """Test multiple nested lookups"""
        # Create a mock request with multiple nested lookups
        request = self.factory.get('/work-orders/work-order?status__control__name=Active&status__name=Active&status__control__key=active')
        
        # Test the get_request_params method
        params = self.view.get_request_params(request)
        
        print(f"Query params: {dict(request.GET)}")
        print(f"Processed params: {params}")
        
        # All nested lookups should be passed through as-is
        self.assertIn('status__control__name', params)
        self.assertEqual(params['status__control__name'], 'Active')
        self.assertIn('status__name', params)
        self.assertEqual(params['status__name'], 'Active')
        self.assertIn('status__control__key', params)
        self.assertEqual(params['status__control__key'], 'active')
    
    def test_get_request_params_edge_cases(self):
        """Test edge cases"""
        # Test with no query params
        request = self.factory.get('/work-orders/work-order')
        params = self.view.get_request_params(request)
        self.assertEqual(params, {})
        
        # Test with empty query params
        request = self.factory.get('/work-orders/work-order?')
        params = self.view.get_request_params(request)
        self.assertEqual(params, {})
        
        # Test with pagination params (should be ignored)
        request = self.factory.get('/work-orders/work-order?_start=0&_end=10&status__control__name=Active')
        params = self.view.get_request_params(request)
        self.assertNotIn('_start', params)
        self.assertNotIn('_end', params)
        self.assertIn('status__control__name', params)
        self.assertEqual(params['status__control__name'], 'Active')


if __name__ == '__main__':
    # Run the test
    import django.test.utils
    django.test.utils.setup_test_environment()
    
    test = QueryParamsTest()
    test.setUp()
    
    print("=" * 50)
    print("RUNNING QUERY PARAMS TESTS")
    print("=" * 50)
    
    test.test_get_request_params_nested_lookup()
    test.test_get_request_params_simple_lookup()
    test.test_get_request_params_mixed_lookups()
    test.test_get_request_params_multiple_nested()
    test.test_get_request_params_edge_cases()
    
    print("=" * 50)
    print("TESTS COMPLETED")
    print("=" * 50) 