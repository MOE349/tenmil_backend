from django.contrib import admin
from .models import Tenant, Domain

admin.site.register(Tenant)
admin.site.register(Domain)
