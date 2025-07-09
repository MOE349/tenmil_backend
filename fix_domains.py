#!/usr/bin/env python
"""
Fix domain configuration to match BASE_DOMAIN setting.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
django.setup()

from core.models import Tenant, Domain
from django.conf import settings

def fix_domains():
    """Update domains to match BASE_DOMAIN setting."""
    print("=== Fixing Domain Configuration ===")
    
    # Get current domains
    print("\n1. Current domains:")
    domains = Domain.objects.all()
    for domain in domains:
        print(f"   - {domain.domain} -> {domain.tenant.schema_name}")
    
    # Update domains to match BASE_DOMAIN
    print(f"\n2. Updating domains to use BASE_DOMAIN: {settings.BASE_DOMAIN}")
    
    # Update public tenant domain
    try:
        public_tenant = Tenant.objects.get(schema_name='public')
        public_domain, created = Domain.objects.get_or_create(
            tenant=public_tenant,
            defaults={'domain': settings.BASE_DOMAIN, 'is_primary': True}
        )
        if not created:
            public_domain.domain = settings.BASE_DOMAIN
            public_domain.save()
        print(f"   ✓ Public domain: {public_domain.domain}")
    except Tenant.DoesNotExist:
        print("   ✗ Public tenant not found")
    
    # Update tenmil tenant domain
    try:
        tenmil_tenant = Tenant.objects.get(schema_name='tenmil')
        tenmil_domain, created = Domain.objects.get_or_create(
            tenant=tenmil_tenant,
            defaults={'domain': f"tenmil.{settings.BASE_DOMAIN}", 'is_primary': True}
        )
        if not created:
            tenmil_domain.domain = f"tenmil.{settings.BASE_DOMAIN}"
            tenmil_domain.save()
        print(f"   ✓ Tenmil domain: {tenmil_domain.domain}")
    except Tenant.DoesNotExist:
        print("   ✗ Tenmil tenant not found")
    
    # Show updated domains
    print("\n3. Updated domains:")
    domains = Domain.objects.all()
    for domain in domains:
        print(f"   - {domain.domain} -> {domain.tenant.schema_name}")
    
    print("\n=== Domain Fix Complete ===")

if __name__ == "__main__":
    fix_domains() 