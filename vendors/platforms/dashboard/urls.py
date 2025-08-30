from django.urls import path
from vendors.platforms.dashboard.views import *


urlpatterns = [
path('vendor', VendorDashboardView.as_view(), name='Vendor'), 
path('contact_personnel', ContactPersonnelDashboardView.as_view(), name='ContactPersonnel'), 

]