from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.views.system_level_view import SystemLevelView
from core.models import HighLevelMaintenanceType
from meter_readings.models import MeterReading
from work_orders.models import *
from work_orders.platforms.base.serializers import *
from work_orders.services import WorkOrderService


class WorkOrderBaseView(BaseAPIView):
    serializer_class = WorkOrderBaseSerializer
    model_class = WorkOrder


    def handle_post_data(self, request):        
        data =  super().handle_post_data(request)
        # data = self.validate_post_data(data)
        data['trigger_meter_reading'] = MeterReading.objects.filter(
            content_type=data.get('content_type'),
            object_id=data.get('object_id')
        ).order_by('-created_at').first().meter_reading or None
        return data
    
    # def validate_post_data(self, data):
    #     opened_work_orders = WorkOrder.objects.filter(status__control__name='Active', object_id=data.get('object_id'))
    #     if opened_work_orders.exists():
    #         raise LocalBaseException(exception="There is an opened work order, please close it first")
    #     return data
    
    def create(self, data, params, return_instance=False, *args, **kwargs):
        if "status" not in data:
            data['status'] = WorkOrderStatusNames.objects.get(name="Active").pk
        # Code will be auto-generated in the model's save method
        instance, response = super().create(data, params, return_instance=True, *args, **kwargs)
        WorkOrderLog.objects.create(work_order=instance, amount=0, log_type=WorkOrderLog.LogTypeChoices.CREATED, user=params['user'], description="Work Order Created")
        return self.format_response(data=response, status_code=201)
    
    def handle_update_data(self, request):
        data = super().handle_update_data(request)
        return data

    def update(self, data, params,  pk, partial,  *args, **kwargs):
        amount = data.pop('amount', 0)
        status = data.get('status', None)
        if status:
            status_instance = WorkOrderStatusNames.objects.get_object_or_404(id=status, raise_exception=True)
        else:
            status_instance = WorkOrderStatusNames.objects.get_object_or_404(name="Active", raise_exception=True)
        status = status_instance.control.name if status_instance else "Active"
        
        """Update an object"""
        user_lang = params.pop('lang', 'en')
        instance = self.get_instance(pk)

        # Handle asset online status update from payload key 'asset__is_online'
        try:
            asset_is_online = data.pop('asset__is_online', None)
            print(f"asset__is_online payload: {asset_is_online}")
            if asset_is_online is not None:
                # Coerce to boolean from common string/number representations
                desired_is_online = None
                if isinstance(asset_is_online, str):
                    normalized = asset_is_online.strip().lower()
                    if normalized in ["true", "1", "yes", "y", "on"]:
                        desired_is_online = True
                    elif normalized in ["false", "0", "no", "n", "off"]:
                        desired_is_online = False
                    else:
                        raise LocalBaseException(exception="asset__is_online must be a boolean value", status_code=400)
                elif isinstance(asset_is_online, (int, float)):
                    desired_is_online = bool(asset_is_online)
                elif isinstance(asset_is_online, bool):
                    desired_is_online = asset_is_online
                else:
                    raise LocalBaseException(exception="asset__is_online must be a boolean value", status_code=400)

                # Update related asset/logs if available following business rules
                try:
                    # Resolve asset robustly (prefer explicit helper over GFK to avoid lazy/GFK edge cases)
                    from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
                    related_asset = get_object_by_content_type_and_id(instance.content_type.id, instance.object_id)
                    if not related_asset:
                        # Fallback to GFK
                        related_asset = getattr(instance, 'asset', None)
                    print(f"Resolved asset: {related_asset} (has is_online: {hasattr(related_asset, 'is_online')})")

                    if related_asset is not None and hasattr(related_asset, 'is_online'):
                        current_is_online = bool(related_asset.is_online)
                        print(f"current_is_online: {current_is_online}, desired_is_online: {desired_is_online}, asset_id={getattr(related_asset, 'id', None)}")
                        if desired_is_online == current_is_online:
                            print("No change to asset.is_online")
                        elif desired_is_online is False and current_is_online is True:
                            # Online -> Offline from Work Order: create a new log with offline_user and set work_order
                            from assets.models import AssetOnlineStatusLog
                            AssetOnlineStatusLog.objects.create(
                                content_type=instance.content_type,
                                object_id=instance.object_id,
                                offline_user=params.get('user'),
                                work_order=instance,
                            )
                            related_asset.is_online = False
                            related_asset.save(update_fields=["is_online"]) 
                            print(f"Asset set offline and saved. New is_online={related_asset.is_online}")
                            try:
                                # Double-check from DB
                                refreshed = related_asset.__class__.objects.get(pk=related_asset.pk)
                                print(f"Refreshed is_online from DB: {refreshed.is_online}")
                            except Exception as _e:
                                pass
                        elif desired_is_online is True and current_is_online is False:
                            # Offline -> Online from Work Order: only if latest log for THIS work order has no online_user
                            from assets.models import AssetOnlineStatusLog
                            latest_log_for_wo = AssetOnlineStatusLog.objects.filter(
                                content_type=instance.content_type,
                                object_id=instance.object_id,
                                work_order=instance
                            ).order_by('-created_at').first()
                            if latest_log_for_wo and latest_log_for_wo.online_user is None:
                                latest_log_for_wo.online_user = params.get('user')
                                latest_log_for_wo.save(update_fields=["online_user", "updated_at"])                                
                                related_asset.is_online = True
                                related_asset.save(update_fields=["is_online"]) 
                                print("Asset set online and saved from WO flow")
                            else:
                                # If no matching log or it belongs to another WO or already closed, ignore
                                print("No matching WO log to bring asset online; skipping")
                except Exception as e:
                    # Do not block work order update on asset update failure
                    print(f"Failed to update related asset is_online: {e}")
        except LocalBaseException:
            # Re-raise validation error for clear API feedback
            raise

        if status == "Closed":
            # Check if completion meter reading is provided
            completion_reading = data.get('completion_meter_reading')
            if (completion_reading is None or completion_reading == '') and not instance.completion_meter_reading:
                # We'll handle this after getting the instance
                needs_meter_reading = True
            else:
                needs_meter_reading = False
            
        elif status != 'Closed' and instance.status.control.name == "Closed":
            instance.is_reopened = True
            instance.save()
            WorkOrderLog.objects.create(work_order=instance, amount=amount, log_type=WorkOrderLog.LogTypeChoices.REOPENED, user=params['user'], description="Work Order Reopened")
        
        # Handle completion meter reading for closed status
        if status == "Closed" and needs_meter_reading:
            from meter_readings.models import MeterReading
            latest_meter_reading = MeterReading.objects.filter(
                content_type=instance.content_type,
                object_id=instance.object_id
            ).order_by('-created_at').first()
            
            if latest_meter_reading:
                data['completion_meter_reading'] = latest_meter_reading.meter_reading
                print(f"Auto-filled completion meter reading: {latest_meter_reading.meter_reading}")
            else:
                raise LocalBaseException(exception="No meter readings found for this asset")
        
        # Create new meter reading if user provided completion_meter_reading
        elif status == "Closed" and not needs_meter_reading:
            completion_reading = data.get('completion_meter_reading')
            if completion_reading is not None and str(completion_reading).strip() != '':
                print(f"User provided completion meter reading: {completion_reading}")
                self._create_meter_reading_from_completion(instance, completion_reading, params.get('user'))
        
        is_closed = instance.is_closed
        serializer = self.serializer_class(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = serializer.data
        if status == "Closed":
            instance.is_closed = True
            instance.status = status_instance
            
            # Auto-set completion_end_date if not provided by user
            if not instance.completion_end_date:
                from django.utils import timezone
                
                # Get the asset's timezone for consistent date calculation
                asset_timezone = None
                try:
                    # Try to get asset timezone if PM settings exist for this work order
                    from pm_automation.models import PMSettings
                    pm_settings = PMSettings.objects.filter(
                        content_type=instance.content_type,
                        object_id=instance.object_id
                    ).first()
                    
                    if pm_settings:
                        asset_timezone = pm_settings.get_asset_timezone()
                        print(f"Using PM settings asset timezone: {asset_timezone}")
                    else:
                        # Try to get timezone directly from asset
                        try:
                            asset = instance.asset
                            if hasattr(asset, 'site') and asset.site:
                                asset_timezone = asset.site.get_effective_timezone()
                                print(f"Using asset site timezone: {asset_timezone}")
                            elif hasattr(asset, 'location') and asset.location and asset.location.site:
                                asset_timezone = asset.location.site.get_effective_timezone()
                                print(f"Using asset location site timezone: {asset_timezone}")
                        except Exception:
                            pass
                        
                        # Fallback to company timezone
                        if not asset_timezone:
                            try:
                                from company.models import CompanyProfile
                                company_profile = CompanyProfile.get_or_create_default()
                                asset_timezone = company_profile.get_timezone_object()
                                print(f"Using company timezone: {asset_timezone}")
                            except Exception:
                                pass
                    
                except Exception as e:
                    print(f"Could not get asset timezone: {e}")
                
                # Convert current time to asset timezone, then get the date
                current_time = timezone.now()
                if asset_timezone:
                    # Convert to asset's local time
                    local_time = current_time.astimezone(asset_timezone)
                    completion_date = local_time.date()
                    print(f"Auto-set completion_end_date to: {completion_date} (asset timezone: {asset_timezone})")
                else:
                    # Fallback to UTC date
                    completion_date = current_time.date()
                    print(f"Auto-set completion_end_date to: {completion_date} (UTC fallback)")
                
                instance.completion_end_date = completion_date
            
            instance.save()
            WorkOrderLog.objects.create(work_order=instance, amount=amount, log_type=WorkOrderLog.LogTypeChoices.COMPLETED, user=params['user'], description="Work Order Closed")
            
            # Handle backlog completion - return uncompleted backlog items to asset backlogs
            try:
                completion_result = WorkOrderService.handle_work_order_completion(instance.id, params['user'])
                if completion_result['success'] and completion_result['returned_count'] > 0:
                    print(f"Returned {completion_result['returned_count']} uncompleted backlog items to asset backlogs")
                elif not completion_result['success']:
                    print(f"Warning: Failed to handle backlog completion: {completion_result['error']}")
            except Exception as e:
                print(f"Error handling backlog completion: {e}")
        else:
            instance.is_closed = False
            instance.status = status_instance
            instance.save()               
            WorkOrderLog.objects.create(work_order=instance, amount=amount, log_type=WorkOrderLog.LogTypeChoices.UPDATED, user=params['user'], description=" ".join(list(data.keys())))
        response['status'] = WorkOrderStatusNamesBaseSerializer(instance.status).data
        return self.format_response(data=response, status_code=200)
    
    def _create_meter_reading_from_completion(self, work_order_instance, completion_meter_reading, user):
        """
        Create a new meter reading when user provides completion_meter_reading
        Validates that the new reading is larger than the previous one
        """
        try:
            from meter_readings.models import MeterReading
            from meter_readings.helpers import get_previous_meter_reading
            from assets.services import get_content_type_and_asset_id
            
            # Validate completion_meter_reading is not empty and is numeric
            if not completion_meter_reading or str(completion_meter_reading).strip() == '':
                raise LocalBaseException(
                    exception="Completion meter reading cannot be empty",
                    status_code=400
                )
            
            try:
                completion_meter_reading_float = float(completion_meter_reading)
            except (ValueError, TypeError):
                raise LocalBaseException(
                    exception=f"Completion meter reading '{completion_meter_reading}' is not a valid number",
                    status_code=400
                )
            
            # Get previous meter reading for validation
            asset_id = str(work_order_instance.object_id)  # Use just the UUID
            previous_meter_reading = get_previous_meter_reading(asset_id)
            old_meter_reading = previous_meter_reading.meter_reading if previous_meter_reading else 0
            
            # Validate that new reading is larger than previous
            if old_meter_reading >= completion_meter_reading_float:
                raise LocalBaseException(
                    exception=f'Completion meter reading ({completion_meter_reading_float}) must be greater than the last meter reading ({old_meter_reading})', 
                    status_code=400
                )
            
            # Check if meter reading already exists to avoid duplicates
            existing_meter_reading = MeterReading.objects.filter(
                content_type=work_order_instance.content_type,
                object_id=work_order_instance.object_id,
                meter_reading=completion_meter_reading_float
            ).first()
            
            if existing_meter_reading:
                print(f"Meter reading {completion_meter_reading_float} already exists for this asset")
                return existing_meter_reading
            
            # Create new meter reading
            new_meter_reading = MeterReading.objects.create(
                content_type=work_order_instance.content_type,
                object_id=work_order_instance.object_id,
                meter_reading=completion_meter_reading_float,
                created_by=user
            )
            
            print(f"Created new meter reading: {new_meter_reading.meter_reading} for asset {asset_id}")
            return new_meter_reading
            
        except LocalBaseException:
            # Re-raise validation errors
            raise
        except Exception as e:
            print(f"Error creating meter reading from completion: {e}")
            raise LocalBaseException(
                exception=f"Failed to create meter reading: {str(e)}", 
                status_code=500
            )
    

class WorkOrderChecklistBaseView(BaseAPIView):
    serializer_class = WorkOrderChecklistBaseSerializer
    model_class = WorkOrderChecklist

    def handle_post_data(self, request):
        data = super().handle_post_data(request)
        return data

    def create(self, data, params, return_instance=True, *args, **kwargs):
        instance, response = super().create(data, params, return_instance, *args, **kwargs)
        WorkOrderLog.objects.create(work_order=instance.work_order, amount=0, log_type=WorkOrderLog.LogTypeChoices.UPDATED, user=params['user'], description="Checklist item added")
        return self.format_response(data=response, status_code=200)


class WorkOrderLogBaseView(BaseAPIView):
    serializer_class = WorkOrderLogBaseSerializer
    model_class = WorkOrderLog
    http_method_names=['get']

    def get_request_params(self, request):
        params = super().get_request_params(request)
        params['ordering'] = "created_at"
        return params



class WorkOrderMiscCostBaseView(BaseAPIView):
    serializer_class = WorkOrderMiscCostBaseSerializer
    model_class = WorkOrderMiscCost

    def create(self, data, params,  return_instance=True, *args, **kwargs):
        instance, response = super().create(data, params,  return_instance, *args, **kwargs)
        WorkOrderLog.objects.create(work_order=instance.work_order, amount=0, log_type=WorkOrderLog.LogTypeChoices.UPDATED, user=params['user'], description="Third party service added")
        return self.format_response(data=response, status_code=200)


class WorkOrderStatusControlsBaseView(BaseAPIView):
    serializer_class = WorkOrderStatusControlsBaseSerializer
    model_class = WorkOrderStatusControls
    http_method_names = ['get']


class HighLevelMaintenanceTypeBaseView(BaseAPIView):
    serializer_class = HighLevelMaintenanceTypeBaseSerializer
    model_class = HighLevelMaintenanceType
    http_method_names = ['get']


class WorkOrderStatusNamesBaseView(SystemLevelView):
    serializer_class = WorkOrderStatusNamesBaseSerializer
    model_class = WorkOrderStatusNames


class MaintenanceTypeBaseView(SystemLevelView):
    serializer_class = MaintenanceTypeBaseSerializer
    model_class = MaintenanceType
    

class PriorityBaseView(SystemLevelView):
    serializer_class = PriorityBaseSerializer
    model_class = Priority

class WorkOrderCompletionNoteBaseView(BaseAPIView):
    serializer_class = WorkOrderCompletionNoteBaseSerializer
    model_class = WorkOrderCompletionNote

    def get(self, request, pk=None, params=None, allow_unauthenticated_user=False, *args, **kwargs):
        if params is None:
            params = self.get_request_params(request)
        params = self.clear_paginations_params(params)
        instance, errors, status_code= self.model_class.objects.get_object_or_404(raise_exception=False, **params)
        pk = instance.pk if instance else None
        return super().get(request, pk, params, allow_unauthenticated_user, *args, **kwargs)

    def handle_post_data(self, request):
        data = super().handle_post_data(request)
        data['user'] = self.get_request_user(request).pk
        return data


    def post(self, request, allow_unauthenticated_user=False, *args, **kwargs):
        try:
            instance, error, _ = self.model_class.objects.get_object_or_404(raise_exception=False, work_order=request.data.get("work_order"))
            return super().patch(request, instance.pk, *args, **kwargs)
        except:
            return super().post(request, allow_unauthenticated_user, *args, **kwargs)
    
    def update(self, data, params, pk, partial, return_instance=True, *args, **kwargs):
        instance, response = super().update(data, params, pk, partial, return_instance, *args, **kwargs)
        WorkOrderLog.objects.create(work_order=instance.work_order, amount=0, log_type=WorkOrderLog.LogTypeChoices.UPDATED, user=params['user'], description=" ".join(list(data.keys())))
        return self.format_response(data=response, status_code=200)


class WorkOrderImportBacklogsView(BaseAPIView):
    """Custom view for importing asset backlogs into work order checklists"""
    serializer_class = None  # No serializer needed for this operation
    model_class = WorkOrder
    http_method_names = ['post']
    
    def post(self, request, pk=None, *args, **kwargs):
        """
        Import asset backlogs into work order checklist
        
        POST /api/work-orders/{work_order_id}/import-backlogs/
        """
        try:
            work_order_id = pk
            user = request.user
            
            # Call the service to import backlogs
            result = WorkOrderService.import_asset_backlogs_to_work_order(work_order_id, user)
            
            return self.format_response(data={
                'success': True,
                'message': result['message'],
                'imported_count': result['imported_count'],
                'work_order_id': result['work_order_id']
            }, status_code=200)
                
        except Exception as e:
            return self.handle_exception(e)


class WorkOrderCompletionView(BaseAPIView):
    """Custom view for handling work order completion with backlog management"""
    serializer_class = None  # No serializer needed for this operation
    model_class = WorkOrder
    http_method_names = ['post']
    
    def post(self, request, pk=None, *args, **kwargs):
        """
        Complete work order and handle backlog management
        
        POST /api/work-orders/{work_order_id}/complete/
        """
        try:
            work_order_id = pk
            user = request.user
            
            # Call the service to handle completion
            result = WorkOrderService.handle_work_order_completion(work_order_id, user)
            
            return self.format_response(data={
                'success': True,
                'message': result['message'],
                'returned_count': result['returned_count'],
                'work_order_id': result['work_order_id']
            }, status_code=200)
                
        except Exception as e:
            return self.handle_exception(e)