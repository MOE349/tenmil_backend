from django.urls import path
from vendors.platforms.api.views import *


urlpatterns = [
path('vendor', VendorApiView.as_view(), name='Vendor'), 
path('contact_personnel', ContactPersonnelApiView.as_view(), name='ContactPersonnel'), 

]