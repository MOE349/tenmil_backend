from django.urls import path
from vendors.platforms.mobile.views import *


urlpatterns = [
path('vendor', VendorMobileView.as_view(), name='Vendor'), 
path('contact_personnel', ContactPersonnelMobileView.as_view(), name='ContactPersonnel'), 

]