from assets.services import get_assets_by_gfk, get_content_type_and_asset_id, move_asset
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from assets.models import *
from assets.platforms.base.serializers import *
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from file_uploads.models import FileUpload


class AssetBaseView(BaseAPIView):
    serializer_class = AssetBaseSerializer
    model_class = Equipment
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        equipments_instance = Equipment.objects.all()
        equipments = list(EquipmentBaseSerializer(equipments_instance, many=True).data)
        attachments_instance = Attachment.objects.all()
        attachments = list(AttachmentBaseSerializer(attachments_instance, many=True).data)
        response = sorted(equipments + attachments, key=lambda x: x['created_at'], reverse=True)
        return self.format_response(data=response, status_code=200)

    def get_instance(self, pk, params=None):
        ct, instance= get_content_type_and_asset_id(pk, return_ct_instance=True, return_instance=True)
        if ct == ContentType.objects.get_for_model(Equipment):
            self.serializer_class = EquipmentBaseSerializer
        elif ct == ContentType.objects.get_for_model(Attachment):
            self.serializer_class = AttachmentBaseSerializer
        else:
            raise LocalBaseException(exception="Invalid asset type.")
        return instance

    def update(self, data, params,  pk, partial, *args, **kwargs):
        print(f"Asset update data: {data}")
        instance, response = super().update(data, params,  pk, partial, *args, **kwargs)    
        if "location" in data:
            print(f"update location: {data['location']}")
            move_asset(asset=instance, to_location=data["location"], user=self.get_request_user(self.request))
        return self.format_response(data=response, status_code=200)
    
    def set_image(self, request, pk, *args, **kwargs):
        """
        Set the main image for an asset from one of its uploaded files.
        Expects: {"file_id": "uuid-of-uploaded-file"} or {"file_id": null} to remove image
        """
        try:
            # Get the asset instance
            instance = self.get_instance(pk)
            
            # Get request data
            data = request.data
            file_id = data.get('file_id')
            
            if file_id is None:
                # Remove the current image
                instance.set_image(None)
                message = "Asset image removed successfully"
            else:
                # Get the file upload instance
                try:
                    file_upload = FileUpload.objects.get(id=file_id, is_deleted=False)
                except FileUpload.DoesNotExist:
                    raise LocalBaseException(
                        exception="File not found or has been deleted",
                        status_code=404
                    )
                
                # Set the image (this will validate that the file belongs to the asset)
                try:
                    instance.set_image(file_upload)
                    message = f"Asset image set to {file_upload.original_filename}"
                except ValueError as e:
                    raise LocalBaseException(
                        exception=str(e),
                        status_code=400
                    )
            
            # Return updated asset data
            response_data = self.serializer_class(instance).data
            response_data['message'] = message
            
            return self.format_response(data=response_data, status_code=200)
            
        except Exception as e:
            return self.handle_exception(e)
    

class EquipmentWeightClassBaseView(BaseAPIView):
    serializer_class = EquipmentWeightClassBaseSerializer
    model_class = EquipmentWeightClass

 
class EquipmentBaseView(AssetBaseView):
    serializer_class = EquipmentBaseSerializer
    model_class = Equipment

    def get_instance(self, pk, params=None):
        """Override to get Equipment instance directly"""
        return Equipment.objects.get(pk=pk)

class AttachmentBaseView(AssetBaseView):
    serializer_class = AttachmentBaseSerializer
    model_class = Attachment

    def get_instance(self, pk, params=None):
        """Override to get Attachment instance directly"""
        return Attachment.objects.get(pk=pk)


class EquipmentCategoryBaseView(BaseAPIView):
    serializer_class = EquipmentCategoryBaseSerializer
    model_class = EquipmentCategory


class AttachmentCategoryBaseView(BaseAPIView):
    serializer_class = AttachmentCategoryBaseSerializer
    model_class = AttachmentCategory


class AssetBaseMoveView(BaseAPIView):
    serializer_class = AssetMoveBaseSerializer
    model_class = AssetMovementLog
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        try:
            params = self.get_request_params(request)
            instances = self.get_queryset(params=params)
            response = self.serializer_class(instances, many=True).data
            return self.format_response(data=response, status_code=200)
        except Exception as e:
            self.handle_exception(e)


    