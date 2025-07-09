#!/usr/bin/env python
"""
Test tenant detection with the current setup.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
django.setup()

from django.test import RequestFactory
from django.conf import settings
from configurations.base_features.middlewares.subdomain_middleware import SubdomainTenantMiddleware
from core.models import Tenant, Domain
from django_tenants.utils import get_tenant

def test_tenant_detection():
    """Test tenant detection with current setup."""
    print("=== Testing Tenant Detection ===")
    
    # Show current setup
    print("\n1. Current setup:")
    print(f"   BASE_DOMAIN: {settings.BASE_DOMAIN}")
    tenants = Tenant.objects.all()
    for tenant in tenants:
        print(f"   Tenant: {tenant.schema_name} -> {tenant.name}")
        domains = Domain.objects.filter(tenant=tenant)
        for domain in domains:
            print(f"     Domain: {domain.domain}")
    
    # Test middleware
    print("\n2. Testing middleware:")
    factory = RequestFactory()
    mock_get_response = lambda request: None
    middleware = SubdomainTenantMiddleware(mock_get_response)
    
    test_cases = [
        ("api.alfrih.com", "public"),
        ("tenmil.api.alfrih.com", "tenmil"),
    ]
    
    for host, expected_schema in test_cases:
        print(f"\n   Testing: {host}")
        
        # Create request
        request = factory.get('/')
        request.META['HTTP_HOST'] = host
        
        # Mock django-tenants setting the tenant
        try:
            tenant = Tenant.objects.get(schema_name=expected_schema)
            request.tenant = tenant
            request.schema_name = tenant.schema_name
            print(f"     ✓ Tenant set: {tenant.schema_name}")
        except Tenant.DoesNotExist:
            print(f"     ✗ Tenant not found: {expected_schema}")
            continue
        
        # Test middleware
        response = middleware.process_request(request)
        
        if response:
            print(f"     ✗ Middleware returned response: {response.status_code}")
        else:
            print(f"     ✓ Middleware processed successfully")
            print(f"       - tenant: {getattr(request, 'tenant', None)}")
            print(f"       - schema_name: {getattr(request, 'schema_name', None)}")
            print(f"       - is_admin_subdomain: {getattr(request, 'is_admin_subdomain', None)}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_tenant_detection() 