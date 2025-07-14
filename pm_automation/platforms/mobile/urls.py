from django.urls import path
from pm_automation.platforms.mobile.views import *


urlpatterns = [
path('pmsettings', PmsettingsMobileView.as_view(), name='Pmsettings'), 
path('pmtrigger', PmtriggerMobileView.as_view(), name='Pmtrigger'), 

]