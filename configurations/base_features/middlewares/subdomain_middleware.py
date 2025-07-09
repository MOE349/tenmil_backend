"""
Subdomain Tenant Middleware

This middleware works in conjunction with django-tenants to provide additional
tenant validation and request attributes. It runs AFTER django-tenants middleware
has already detected and set the tenant.

Best Practices:
- Minimal logic in middleware
- Proper error handling and logging
- Clear separation of concerns
- Type hints for better maintainability
- Comprehensive documentation
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django_tenants.utils import get_tenant
from core.models import Tenant

logger = logging.getLogger(__name__)


class SubdomainTenantMiddleware(MiddlewareMixin):
    """
    Middleware that validates tenant access and sets custom request attributes.
    
    This middleware runs AFTER django-tenants middleware and provides:
    1. Additional tenant validation
    2. Custom request attributes for tenant-specific features
    3. Admin subdomain detection
    4. Comprehensive logging for debugging
    
    Expected behavior:
    - For admin domains (api.alfrih.com): Sets public schema
    - For tenant domains (tenant.api.alfrih.com): Validates tenant exists
    - For invalid domains: Returns 404 with proper error message
    
    Attributes added to request:
    - request.tenant: The validated tenant object
    - request.schema_name: The tenant's schema name
    - request.is_admin_subdomain: Boolean indicating admin domain
    - request.tenant_features: Dict of tenant-specific features/flags
    """
    
    def __init__(self, get_response=None):
        """Initialize middleware with optional get_response function."""
        super().__init__(get_response)
        self._validate_settings()
    
    def _validate_settings(self) -> None:
        """Validate required settings are configured."""
        if not hasattr(settings, 'BASE_DOMAIN'):
            raise ValueError("BASE_DOMAIN setting is required for SubdomainTenantMiddleware")
    
    def _extract_subdomain(self, host: str) -> str:
        """
        Extract subdomain from host string.
        
        Args:
            host: Full host string (e.g., 'tenant.api.alfrih.com')
            
        Returns:
            Subdomain string (e.g., 'tenant')
        """
        return host.split('.')[0]
    
    def _is_admin_subdomain(self, host: str) -> bool:
        """
        Determine if the host is an admin subdomain.
        
        Args:
            host: Full host string
            
        Returns:
            True if admin subdomain, False otherwise
        """
        # Only the exact BASE_DOMAIN is admin, not subdomains of it
        return host == settings.BASE_DOMAIN
    
    def _get_tenant_features(self, tenant: Tenant) -> Dict[str, Any]:
        """
        Get tenant-specific features and flags.
        
        Args:
            tenant: Tenant object
            
        Returns:
            Dictionary of tenant features
        """
        # This can be extended to fetch from database or cache
        return {
            "enable_reports": True,
            "max_users": 10,
            "tenant_id": str(tenant.id),
            "tenant_name": tenant.name,
            "on_trial": tenant.on_trial,
            "paid_until": str(tenant.paid_until) if tenant.paid_until else None,
        }
    
    def _handle_admin_subdomain(self, request: HttpRequest, host: str) -> None:
        """
        Handle requests to admin subdomain.
        
        Args:
            request: Django request object
            host: Full host string
        """
        request.is_admin_subdomain = True
        request.tenant = None
        request.schema_name = "public"
        request.tenant_features = {
            "is_admin": True,
            "enable_reports": True,
            "max_users": 1000,  # Higher limits for admin
        }
        
        logger.debug(f"Admin subdomain detected: {host}")
    
    def _validate_tenant_subdomain(self, request: HttpRequest, host: str, subdomain: str) -> Optional[HttpResponse]:
        """
        Validate tenant subdomain and set request attributes.
        
        Args:
            request: Django request object
            host: Full host string
            subdomain: Extracted subdomain
            
        Returns:
            HttpResponse if validation fails, None if successful
        """
        try:
            # Get tenant that django-tenants has already set
            tenant = get_tenant(request)
            
            # Check if tenant exists
            if tenant is None:
                logger.warning(f"No tenant found for subdomain: '{subdomain}' from host '{host}'")
                return HttpResponse(
                    "Invalid tenant subdomain.", 
                    status=404,
                    content_type="text/plain"
                )
            
            # Validate tenant matches expected subdomain
            if tenant.schema_name != subdomain:
                logger.warning(
                    f"Tenant mismatch: expected '{subdomain}', got '{tenant.schema_name}' "
                    f"from host '{host}'"
                )
                return HttpResponse(
                    "Invalid tenant subdomain.", 
                    status=404,
                    content_type="text/plain"
                )
            
            # Set request attributes
            request.tenant = tenant
            request.schema_name = tenant.schema_name
            request.is_admin_subdomain = False
            request.tenant_features = self._get_tenant_features(tenant)
            
            logger.debug(f"Tenant validated: {tenant.schema_name} for host: {host}")
            return None
            
        except Exception as e:
            logger.exception(f"Tenant validation error for host '{host}': {str(e)}")
            return HttpResponse(
                "Internal server error.", 
                status=500,
                content_type="text/plain"
            )
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Process the request and set tenant-related attributes.
        
        Args:
            request: Django request object
            
        Returns:
            HttpResponse if request should be terminated, None to continue
        """
        # Extract host and subdomain
        host = request.get_host().split(":")[0]
        subdomain = self._extract_subdomain(host)
        
        logger.debug(f"Processing request for host: {host}, subdomain: {subdomain}")
        
        # Handle admin subdomain
        if self._is_admin_subdomain(host):
            self._handle_admin_subdomain(request, host)
            return None
        
        # Validate tenant subdomain
        return self._validate_tenant_subdomain(request, host, subdomain)
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Process the response (optional post-processing).
        
        Args:
            request: Django request object
            response: Django response object
            
        Returns:
            Modified response object
        """
        # Add tenant info to response headers for debugging (only in DEBUG mode)
        if settings.DEBUG:
            tenant_info = getattr(request, 'tenant', None)
            if tenant_info:
                response['X-Tenant'] = tenant_info.schema_name
                response['X-Tenant-ID'] = str(tenant_info.id)
            else:
                response['X-Tenant'] = 'public'
        
        return response
