from configurations.base_features.views.base_api_view import BaseAPIView
from pm_automation.models import *
from pm_automation.platforms.base.serializers import *
from pm_automation.services import PMAutomationService
from rest_framework.response import Response
from rest_framework import status
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
import logging

logger = logging.getLogger(__name__)


class PMSettingsBaseView(BaseAPIView):
    serializer_class = PMSettingsBaseSerializer
    model_class = PMSettings


class PMTriggerBaseView(BaseAPIView):
    serializer_class = PMTriggerBaseSerializer
    model_class = PMTrigger


class PMIterationBaseView(BaseAPIView):
    serializer_class = PMIterationSerializer
    model_class = PMIteration


class PMIterationChecklistBaseView(BaseAPIView):
    serializer_class = PMIterationChecklistSerializer
    model_class = PMIterationChecklist


class ManualPMGenerationBaseView(BaseAPIView):
    serializer_class = PMSettingsBaseSerializer
    model_class = PMSettings
    http_method_names = ['get', 'post']

    """View for manual PM work order generation"""
    
    def get(self, request, pm_settings_id, *args, **kwargs):
        """
        Get next available iterations for manual PM generation
        Returns: {"1": 500, "2": 1000, "3": 500, "4": 2000}
        """
        try:
            # Get PM settings
            pm_settings = self.get_instance(pm_settings_id)
            
            # Validate that manual generation is possible
            self._validate_manual_generation(pm_settings)
            
            # Calculate next available iterations
            next_iterations = self._calculate_next_iterations(pm_settings)
            
            return self.format_response(
                data=next_iterations,
                status_code=200
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def post(self, request, pm_settings_id, *args, **kwargs):
        """
        Generate manual PM work order for selected iteration
        Expected payload: {"iteration_number": 1}
        """
        try:
            # Get PM settings using BaseAPIView method
            pm_settings = self.get_instance(pm_settings_id)
            
            # Validate that manual generation is possible
            self._validate_manual_generation(pm_settings)
            
            # Get iteration number from request
            iteration_number = request.data.get('iteration_number')
            if not iteration_number:
                raise LocalBaseException(
                    exception_type="validation_error",
                    status_code=400,
                    kwargs={"message": "iteration_number is required"}
                )
            
            # Convert to int and validate
            try:
                iteration_number = int(iteration_number)
            except (ValueError, TypeError):
                raise LocalBaseException(
                    exception_type="validation_error",
                    status_code=400,
                    kwargs={"message": "iteration_number must be a valid integer"}
                )
            
            # Validate iteration number against available options
            next_iterations = self._calculate_next_iterations(pm_settings)
            if str(iteration_number) not in next_iterations:
                raise LocalBaseException(
                    exception_type="validation_error",
                    status_code=400,
                    kwargs={
                        "message": f"Invalid iteration_number. Available options: {list(next_iterations.keys())}",
                        "available_iterations": next_iterations
                    }
                )
            
            # Generate manual work order
            work_order = self._generate_manual_work_order(
                pm_settings, 
                iteration_number, 
                next_iterations[str(iteration_number)],
                request.user
            )
            
            return self.format_response(
                data={
                    "work_order_id": str(work_order.id),
                    "work_order_code": work_order.code,
                    "description": work_order.description,
                    "iteration_number": iteration_number,
                    "iteration_interval": next_iterations[str(iteration_number)],
                    "new_pm_counter": pm_settings.trigger_counter,
                    "created_by": work_order.created_by.email if hasattr(work_order, 'created_by') and work_order.created_by else "System"
                },
                status_code=201
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _validate_manual_generation(self, pm_settings):
        """Validate that manual PM generation is possible"""
        
        # Check if there are any iterations configured
        iterations = list(pm_settings.get_iterations())
        if not iterations:
            raise LocalBaseException(
                exception_type="validation_error",
                status_code=400,
                kwargs={"message": "No PM iterations configured for this PM Settings"}
            )
        
        # Check if there are any open PM work orders that might conflict
        # This is a business rule - you might want to allow or disallow based on your needs
        from work_orders.models import WorkOrder
        open_pm_work_orders = WorkOrder.objects.filter(
            content_type=pm_settings.content_type,
            object_id=pm_settings.object_id,
            maint_type='PM',
            is_closed=False,
            is_pm_generated=True
        ).count()
        
        # if open_pm_work_orders > 0:
        #     logger.warning(f"Manual PM generation requested but {open_pm_work_orders} open PM work orders exist")
            # You might want to raise an exception here or just log a warning
            # Uncomment the next lines if you want to prevent manual generation when there are open PM work orders
            # raise LocalBaseException(
            #     exception_type="validation_error",
            #     status_code=400,
            #     kwargs={"message": f"Cannot generate manual PM work order. {open_pm_work_orders} open PM work orders exist for this asset."}
            # )
    
    def _calculate_next_iterations(self, pm_settings):
        """
        Calculate next available iterations for manual generation
        Returns: {"1": 500, "2": 1000, "3": 500, "4": 2000}
        """
        # Get all iterations ordered by order
        iterations = list(pm_settings.get_iterations())
        if not iterations:
            return {}
        
        # Find largest iteration order
        largest_order = max(iteration.order for iteration in iterations)
        
        # Calculate next counter (current + 1)
        next_counter = pm_settings.trigger_counter + 1
        
        logger.info(f"Calculating manual PM iterations: current_counter={pm_settings.trigger_counter}, next_counter={next_counter}, largest_order={largest_order}")
        
        # Calculate next X triggers where X = largest_order
        next_iterations = {}
        
        for i in range(1, largest_order + 1):
            counter = next_counter + i - 1  # 20, 21, 22, 23 for example
            
            # Find which iterations trigger at this counter
            triggered_iterations = []
            for iteration in iterations:
                if counter % iteration.order == 0:
                    triggered_iterations.append(iteration)
            
            # Get the largest (highest interval) triggered iteration
            if triggered_iterations:
                largest_iteration = max(triggered_iterations, key=lambda x: x.interval_value)
                next_iterations[str(i)] = int(largest_iteration.interval_value)
                logger.debug(f"Counter {counter}: triggered iterations {[f'{it.interval_value}(order:{it.order})' for it in triggered_iterations]}, largest: {largest_iteration.interval_value}")
            else:
                # This shouldn't happen with proper iteration setup, but fallback to base interval
                next_iterations[str(i)] = int(pm_settings.interval_value)
                logger.warning(f"Counter {counter}: no iterations triggered, using base interval {pm_settings.interval_value}")
        
        logger.info(f"Calculated next iterations: {next_iterations}")
        return next_iterations
    
    def _generate_manual_work_order(self, pm_settings, iteration_number, iteration_interval, user):
        """Generate manual PM work order for the selected iteration"""
        
        # Update PM settings counter using the user's logic:
        # pm_counter += chosen_iteration_key + 1
        new_counter = pm_settings.trigger_counter + iteration_number + 1
        
        logger.info(f"Manual PM generation: old_counter={pm_settings.trigger_counter}, iteration_number={iteration_number}, new_counter={new_counter}")
        
        # Calculate the target counter for determining triggered iterations
        target_counter = pm_settings.trigger_counter + iteration_number
        
        # Get iterations that would trigger at this target counter
        triggered_iterations = []
        for iteration in pm_settings.get_iterations():
            if target_counter % iteration.order == 0:
                triggered_iterations.append(iteration)
        
        logger.info(f"Target counter {target_counter} triggers iterations: {[f'{it.interval_value}h(order:{it.order})' for it in triggered_iterations]}")
        
        # Update PM settings counter
        PMSettings.objects.filter(id=pm_settings.id).update(trigger_counter=new_counter)
        pm_settings.refresh_from_db()
        
        # Create work order using existing service but with modifications
        from work_orders.models import WorkOrder, WorkOrderStatusNames, WorkOrderLog
        from assets.services import get_content_type_and_asset_id
        
        # Get the asset
        try:
            asset = pm_settings.asset
        except Exception as e:
            logger.error(f"Error accessing asset from pm_settings: {e}")
            raise LocalBaseException(
                exception_type="internal_error",
                status_code=500,
                kwargs={"message": "Could not access asset for PM settings"}
            )
        
        # Get active status
        active_status = WorkOrderStatusNames.objects.filter(
            control__name='Active'
        ).first()
        
        if not active_status:
            from core.models import WorkOrderStatusControls
            active_control = WorkOrderStatusControls.objects.filter(key='active').first()
            if not active_control:
                active_control = WorkOrderStatusControls.objects.create(
                    key='active',
                    name='Active',
                    color='#4caf50',
                    order=1
                )
            active_status = WorkOrderStatusNames.objects.create(
                name='Active',
                control=active_control
            )
        
        # Create work order description
        iteration_names = [it.name for it in triggered_iterations] if triggered_iterations else [f"{iteration_interval}h"]
        asset_code = asset.code if hasattr(asset, 'code') else f"{pm_settings.content_type.app_label}.{pm_settings.content_type.model}"
        description = f"[MANUAL] PM for {asset_code} - Target: {iteration_interval}h (Iterations: {', '.join(iteration_names)})"
        
        # Get trigger meter reading (current meter reading)
        from meter_readings.models import MeterReading
        trigger_meter_reading = None
        try:
            latest_reading = MeterReading.objects.filter(
                content_type=pm_settings.content_type,
                object_id=pm_settings.object_id
            ).order_by('-created_at').first()
            if latest_reading:
                trigger_meter_reading = latest_reading.meter_reading
        except Exception as e:
            logger.warning(f"Could not get latest meter reading: {e}")
        
        # Create work order
        work_order = WorkOrder.objects.create(
            content_type=pm_settings.content_type,
            object_id=pm_settings.object_id,
            status=active_status,
            maint_type='PM',
            priority='medium',
            description=description,
            is_pm_generated=True,
            trigger_meter_reading=trigger_meter_reading
        )
        
        logger.info(f"Created manual PM work order {work_order.id}: {work_order.description}")
        
        # Copy the cumulative checklist for triggered iterations
        try:
            if triggered_iterations:
                # Get the highest-order iteration (which will have the most comprehensive checklist)
                highest_order_iteration = max(triggered_iterations, key=lambda x: x.order)
                pm_settings.copy_iteration_checklist_to_work_order(work_order, highest_order_iteration)
                logger.info(f"Copied cumulative checklist for iteration '{highest_order_iteration.name}' to work order {work_order.id}")
        except Exception as e:
            logger.error(f"Error copying iteration checklists to work order {work_order.id}: {e}")
        
        # Log creation with request user (not system admin)
        WorkOrderLog.objects.create(
            work_order=work_order,
            amount=0,
            log_type=WorkOrderLog.LogTypeChoices.CREATED,
            user=user,
            description="Work Order Created (Manual PM Generation)"
        )
        
        logger.info(f"Created work order log for manual PM work order {work_order.id} by user {user.email}")
        
        return work_order


