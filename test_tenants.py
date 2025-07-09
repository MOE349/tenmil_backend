#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
django.setup()

from core.models import Tenant, Domain
from django.db import connection
from django_tenants.utils import schema_context

def test_tenant_setup():
    print("=== Testing Tenant Setup ===")
    
    # List all tenants
    print("\n1. All tenants in database:")
    tenants = Tenant.objects.all()
    for tenant in tenants:
        print(f"   - {tenant.schema_name}: {tenant.name}")
    
    # List all domains
    print("\n2. All domains in database:")
    domains = Domain.objects.all()
    for domain in domains:
        print(f"   - {domain.domain} -> {domain.tenant.schema_name}")
    
    # Test schema switching
    print("\n3. Testing schema switching:")
    
    # Test public schema
    with schema_context('public'):
        print(f"   - Public schema: {connection.schema_name}")
        tenant_count = Tenant.objects.count()
        print(f"   - Tenant count in public: {tenant_count}")
    
    # Test tenmil schema
    try:
        with schema_context('tenmil'):
            print(f"   - Tenmil schema: {connection.schema_name}")
            # Try to access a tenant-specific model
            from company.models import Site
            site_count = Site.objects.count()
            print(f"   - Site count in tenmil: {site_count}")
    except Exception as e:
        print(f"   - Error accessing tenmil schema: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_tenant_setup() 