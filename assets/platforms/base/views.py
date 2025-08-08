from assets.services import get_assets_by_gfk, get_content_type_and_asset_id, move_asset
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.mixins.file_attachment_mixins import FileAttachmentViewMixin
from assets.models import *
from assets.platforms.base.serializers import *
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType


class AssetBaseView(FileAttachmentViewMixin, BaseAPIView):
    serializer_class = AssetBaseSerializer
    model_class = Equipment
    http_method_names = ["get", "post", "put", "patch", "delete"]

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
        
        # Capture current location before update for move tracking
        instance = self.get_instance(pk)
        previous_is_online = getattr(instance, 'is_online', None)
        current_location = instance.location if hasattr(instance, 'location') else None
        
        instance, response = super().update(data, params,  pk, partial, return_instance=True, *args, **kwargs)

        # Log online status changes done directly from Asset update (no work order context)
        try:
            if 'is_online' in data and previous_is_online is not None:
                new_state = getattr(instance, 'is_online', previous_is_online)
                if new_state != previous_is_online:
                    from assets.models import AssetOnlineStatusLog
                    # Rules:
                    # - If asset goes online -> do not create a new log; if it was offline and has logs, fill the latest log's online_user if empty.
                    # - If asset goes offline -> create a new log with offline_user (work_order is null for asset view changes)
                    if previous_is_online is False and new_state is True:
                        latest_log = AssetOnlineStatusLog.objects.filter(
                            content_type=ContentType.objects.get_for_model(instance.__class__),
                            object_id=instance.id
                        ).order_by('-created_at').first()
                        if latest_log and latest_log.online_user is None:
                            latest_log.online_user = params.get('user')
                            latest_log.save(update_fields=["online_user", "updated_at"])    
                    elif previous_is_online is True and new_state is False:
                        AssetOnlineStatusLog.objects.create(
                            content_type=ContentType.objects.get_for_model(instance.__class__),
                            object_id=instance.id,
                            offline_user=params.get('user'),
                            work_order=None
                        )
        except Exception as e:
            # Do not block asset update on logging errors
            print(f"Failed to log asset is_online change: {e}")

        if "location" in data and data["location"]:
            print(f"update location: {data['location']}")
            # Convert location ID to Location instance
            from company.models import Location
            try:
                to_location = Location.objects.get(pk=data["location"])
                move_asset(asset=instance, from_location=current_location, to_location=to_location, user=self.get_request_user(self.request))
            except Location.DoesNotExist:
                raise LocalBaseException(exception=f"Location with ID {data['location']} not found", status_code=400)
        return self.format_response(data=response, status_code=200)
    
    # FileAttachmentViewMixin automatically provides:
    # - set_image(request, pk): Method to set main image from uploaded files
    

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


class AssetOnlineStatusLogBaseView(BaseAPIView):
    serializer_class = AssetOnlineStatusLogBaseSerializer
    model_class = AssetOnlineStatusLog
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        try:
            params = self.get_request_params(request)
            # Support querying by asset via unified `asset` param (id string)
            instances = self.get_queryset(params=params)
            response = self.serializer_class(instances, many=True).data
            return self.format_response(data=response, status_code=200)
        except Exception as e:
            return self.handle_exception(e)

    