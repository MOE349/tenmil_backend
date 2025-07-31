from django.urls import path
from .views import FileUploadView

app_name = 'file_uploads'

urlpatterns = [
    # File CRUD operations
    path('files/', FileUploadView.as_view(), name='file-list'),
    path('files/<uuid:pk>/', FileUploadView.as_view(), name='file-detail'),
    
    # Custom action URLs
    path('files/<uuid:pk>/download/', FileUploadView.as_view(), {'action': 'download'}, name='file-download'),
    path('files/<uuid:pk>/serve/', FileUploadView.as_view(), {'action': 'serve'}, name='file-serve'),
    path('files/<uuid:pk>/hard-delete/', FileUploadView.as_view(), {'action': 'hard_delete'}, name='file-hard-delete'),
    path('stats/', FileUploadView.as_view(), {'action': 'stats'}, name='file-stats'),
]