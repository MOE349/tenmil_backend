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
    
    def update(self, data, params, pk, partial, return_instance=False, *args, **kwargs):
        """Override update to handle next_iteration counter adjustments"""
        
        # Check if next_iteration is in the data
        next_iteration = data.pop('next_iteration', None)
        counter_update_info = None
        
        if next_iteration is not None:
            # Validate next_iteration
            try:
                next_iteration = int(next_iteration)
                if next_iteration < 0:
                    raise ValueError("next_iteration must be non-negative (0 represents natural next iteration)")
            except (ValueError, TypeError) as e:
                raise LocalBaseException(
                    exception=f"Invalid next_iteration value: {str(e)}",
                    status_code=400
                )
            
            # Get the instance
            instance = self.get_instance(pk)
            
            # Validate that PM settings is active (optional business rule)
            if not instance.is_active:
                logger.warning(f"Counter update attempted on inactive PM Settings {pk}")
                # Uncomment if you want to prevent updates on inactive PM settings
                # raise LocalBaseException(
                #     exception_type="validation_error", 
                #     status_code=400,
                #     kwargs={"message": "Cannot update counter for inactive PM Settings"}
                # )
            
            # Update PM counter using the same logic as manual generation
            # pm_counter += next_iteration
            old_counter = instance.trigger_counter
            new_counter = old_counter + next_iteration
            
            logger.info(f"PM Settings counter update: PM={pk}, old_counter={old_counter}, next_iteration={next_iteration}, new_counter={new_counter}")
            
            # Update the counter
            data['trigger_counter'] = new_counter
            
            # Store counter update info for response
            counter_update_info = {
                "counter_updated": True,
                "old_counter": old_counter,
                "new_counter": new_counter,
                "next_iteration": next_iteration
            }
            
            logger.info(f"Successfully updated PM Settings {pk} counter from {old_counter} to {new_counter} (next_iteration={next_iteration})")
        
        # Proceed with normal update
        instance, response = super().update(data, params, pk, partial, return_instance=True, *args, **kwargs)
        
        # Add counter update info to response if it occurred
        if counter_update_info:
            if isinstance(response, dict):
                response['counter_update'] = counter_update_info
            else:
                # If response is not a dict, we'll add it to the final formatted response
                pass
        
        if return_instance:
            return instance, response
        
        # Format the final response with counter update info
        formatted_response = self.format_response(data=response)
        if counter_update_info and hasattr(formatted_response, 'data') and isinstance(formatted_response.data, dict):
            formatted_response.data['counter_update'] = counter_update_info
        
        return formatted_response


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
        Returns: {"0": "2000 hours", "1": "500 hours", "2": "1000 hours", "3": "500 hours", "4": "2000 hours"}
        Where "0" is the natural next iteration, and 1-4 are manual advance options
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
        Generate manual PM work order for the next appropriate iteration
        No payload required - iteration is calculated automatically
        """
        try:
            # Get PM settings using BaseAPIView method
            pm_settings = self.get_instance(pm_settings_id)
            
            # Validate that manual generation is possible
            self._validate_manual_generation(pm_settings)
            
            # Calculate iteration_number locally - find what would naturally trigger next
            next_counter = pm_settings.trigger_counter + 1
            
            # Find which iterations would trigger at the next counter
            triggered_iterations = []
            for iteration in pm_settings.get_iterations():
                if next_counter % iteration.order == 0:
                    triggered_iterations.append(iteration)
            
            if not triggered_iterations:
                raise LocalBaseException(
                    exception="No iterations would trigger at the next counter position",
                    status_code=400
                )
            
            # Get the largest (most comprehensive) iteration that would trigger
            largest_iteration = max(triggered_iterations, key=lambda x: x.interval_value)
            iteration_number = 0  # Use natural next iteration (option "0")
            
            logger.info(f"Calculated iteration_number={iteration_number} for counter {next_counter}, largest iteration: {largest_iteration.name}")
            
            # Get the formatted string and extract the numeric value
            next_iterations = self._calculate_next_iterations(pm_settings)
            iteration_string = next_iterations[str(iteration_number)]
            iteration_value = int(iteration_string.split()[0])  # Extract "500" from "500 hours"
            
            # Generate manual work order
            work_order = self._generate_manual_work_order(
                pm_settings, 
                iteration_number, 
                iteration_value,  # Pass numeric value for calculations
                request.user
            )
            
            return self.format_response(
                data={
                    "work_order_id": str(work_order.id),
                    "work_order_code": work_order.code,
                    "description": work_order.description,
                    "iteration_number": iteration_number,
                    "iteration_interval": iteration_string,  # Return formatted string for user
                    "new_pm_counter": pm_settings.trigger_counter,
                    "triggered_iterations": [it.name for it in triggered_iterations],
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
                exception="No PM iterations configured for this PM Settings",
                status_code=400
            )
        
        # Check if there are any open PM work orders that might conflict
        from work_orders.models import WorkOrder
        open_pm_work_orders = WorkOrder.objects.filter(
            content_type=pm_settings.content_type,
            object_id=pm_settings.object_id,
            maint_type='PM',
            is_closed=False,
            is_pm_generated=True
        ).count()
        
        if open_pm_work_orders > 0:
            logger.warning(f"Manual PM generation requested but {open_pm_work_orders} open PM work orders exist")
            raise LocalBaseException(
                exception=f"Cannot generate PM work order. {open_pm_work_orders} open PM work order(s) exist for this asset. Please complete the existing work order(s) before generating a new one.",
                status_code=400
            )
    
    def _calculate_next_iterations(self, pm_settings):
        """
        Calculate next available iterations for manual generation
        Returns: {"0": "2000 hours", "1": "500 hours", "2": "1000 hours", "3": "500 hours", "4": "500 hours"}
        Where "0" is the natural next iteration, and 1-4 are manual advance options
        """
        # Get all iterations ordered by order
        iterations = list(pm_settings.get_iterations())
        if not iterations:
            logger.warning(f"No iterations found for PM Settings {pm_settings.id}")
            return {}
        
        # Validate iterations have proper values
        for iteration in iterations:
            if not iteration.interval_value or iteration.interval_value <= 0:
                logger.error(f"Invalid iteration found: {iteration.id} with interval_value {iteration.interval_value}")
        
        # Find largest iteration order
        largest_order = max(iteration.order for iteration in iterations)
        
        # Calculate next counter (current + 1)
        next_counter = pm_settings.trigger_counter + 1
        
        logger.info(f"Calculating manual PM iterations: current_counter={pm_settings.trigger_counter}, next_counter={next_counter}, largest_order={largest_order}")
        logger.info(f"Available iterations: {[(it.interval_value, it.order, it.name) for it in iterations]}")
        
        # Calculate next X+1 triggers where X = largest_order (0 + X manual options)
        next_iterations = {}
        
        # First, add option "0" - the natural next iteration in the cycle
        natural_counter = next_counter  # This is what would happen naturally
        triggered_iterations_natural = []
        for iteration in iterations:
            if natural_counter % iteration.order == 0:
                triggered_iterations_natural.append(iteration)
        
        if triggered_iterations_natural:
            largest_natural = max(triggered_iterations_natural, key=lambda x: x.interval_value)
            if largest_natural.interval_value and largest_natural.interval_value > 0:
                next_iterations["0"] = f"{int(largest_natural.interval_value)} {pm_settings.interval_unit}"
                logger.debug(f"Natural counter {natural_counter}: triggered iterations {[f'{it.interval_value}(order:{it.order})' for it in triggered_iterations_natural]}, largest: {largest_natural.interval_value} {pm_settings.interval_unit}")
            else:
                logger.error(f"Invalid largest natural iteration: {largest_natural.interval_value}")
                next_iterations["0"] = f"{int(pm_settings.interval_value)} {pm_settings.interval_unit}"
        else:
            next_iterations["0"] = f"{int(pm_settings.interval_value)} {pm_settings.interval_unit}"
            logger.warning(f"Natural counter {natural_counter}: no iterations triggered, using base interval {pm_settings.interval_value} {pm_settings.interval_unit}")
        
        # Then add manual options 1 through largest_order
        for i in range(1, largest_order + 1):
            counter = next_counter + i  # 38, 39, 40, 41 for manual options
            
            logger.debug(f"Calculating manual option {i} for counter {counter}")
            
            # Find which iterations trigger at this counter
            triggered_iterations = []
            for iteration in iterations:
                if counter % iteration.order == 0:
                    triggered_iterations.append(iteration)
                    logger.debug(f"  Counter {counter} % {iteration.order} = {counter % iteration.order} → Triggers {iteration.interval_value}")
            
            # Get the largest (highest interval) triggered iteration
            if triggered_iterations:
                largest_iteration = max(triggered_iterations, key=lambda x: x.interval_value)
                if largest_iteration.interval_value and largest_iteration.interval_value > 0:
                    # Format as string with unit
                    next_iterations[str(i)] = f"{int(largest_iteration.interval_value)} {pm_settings.interval_unit}"
                    logger.debug(f"Manual counter {counter}: triggered iterations {[f'{it.interval_value}(order:{it.order})' for it in triggered_iterations]}, largest: {largest_iteration.interval_value} {pm_settings.interval_unit}")
                else:
                    logger.error(f"Invalid largest iteration at counter {counter}: {largest_iteration.interval_value}")
                    next_iterations[str(i)] = f"{int(pm_settings.interval_value)} {pm_settings.interval_unit}"
            else:
                # This shouldn't happen with proper iteration setup, but fallback to base interval
                next_iterations[str(i)] = f"{int(pm_settings.interval_value)} {pm_settings.interval_unit}"
                logger.warning(f"Manual counter {counter}: no iterations triggered, using base interval {pm_settings.interval_value} {pm_settings.interval_unit}")
        
        logger.info(f"Calculated next iterations: {next_iterations}")
        return next_iterations
    
    def _generate_manual_work_order(self, pm_settings, iteration_number, iteration_value, user):
        """Generate manual PM work order for the selected iteration"""
        
        # Update PM settings counter based on iteration type:
        if iteration_number == 0:
            # Option "0" is the natural next iteration - just increment by 1
            new_counter = pm_settings.trigger_counter + 1
            target_counter = pm_settings.trigger_counter + 1
            work_order_type = "NATURAL"
        else:
            # Manual options - use: pm_counter += iteration_number + 1
            new_counter = pm_settings.trigger_counter + iteration_number + 1
            target_counter = pm_settings.trigger_counter + iteration_number
            work_order_type = "MANUAL"
        
        logger.info(f"{work_order_type} PM generation: old_counter={pm_settings.trigger_counter}, iteration_number={iteration_number}, target_counter={target_counter}, new_counter={new_counter}")
        
        # Get iterations that would trigger at the target counter
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
                exception="Could not access asset for PM settings",
                status_code=500
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
        iteration_names = [it.name for it in triggered_iterations] if triggered_iterations else [f"{iteration_value}h"]
        asset_code = asset.code if hasattr(asset, 'code') else f"{pm_settings.content_type.app_label}.{pm_settings.content_type.model}"
        
        # Create description: pm name + iteration interval + unit
        unit_formatted = pm_settings.interval_unit.title()  # Proper capitalization
        
        if pm_settings.name:
            # Use PM settings name if available
            if iteration_number == 0:
                description = f"{pm_settings.name} {iteration_value} {unit_formatted}"
            else:
                description = f"[Manual] {pm_settings.name} {iteration_value} {unit_formatted}"
        else:
            # Fallback to generic PM naming
            if iteration_number == 0:
                description = f"{iteration_value} {unit_formatted} PM"
            else:
                description = f"[Manual] {iteration_value} {unit_formatted} PM"
        
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
        
        logger.info(f"Created {work_order_type.lower()} PM work order {work_order.id}: {work_order.description}")
        
        # Create PMTrigger record so completion handling works properly
        try:
            from pm_automation.models import PMTrigger
            trigger_value = pm_settings.next_trigger_value if pm_settings.next_trigger_value else float(pm_settings.start_threshold_value) + float(pm_settings.interval_value)
            
            # Use get_or_create to handle unique constraint violations
            pm_trigger, created = PMTrigger.objects.get_or_create(
                pm_settings=pm_settings,
                trigger_value=trigger_value,
                defaults={
                    'trigger_unit': pm_settings.interval_unit,
                    'work_order': work_order,
                    'is_handled': False
                }
            )
            
            if created:
                logger.info(f"Created PMTrigger {pm_trigger.id} for manual work order {work_order.id} at trigger value {trigger_value}")
            else:
                # Update existing trigger with the new work order
                pm_trigger.work_order = work_order
                pm_trigger.is_handled = False  # Reset to unhandled
                pm_trigger.save()
                logger.info(f"Updated existing PMTrigger {pm_trigger.id} for manual work order {work_order.id} at trigger value {trigger_value}")
        except Exception as e:
            logger.error(f"Error creating/updating PMTrigger for manual work order {work_order.id}: {e}")
        
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
        log_description = f"Work Order Created ({work_order_type.title()} PM Generation)"
        WorkOrderLog.objects.create(
            work_order=work_order,
            amount=0,
            log_type=WorkOrderLog.LogTypeChoices.CREATED,
            user=user,
            description=log_description
        )
        
        logger.info(f"Created work order log for {work_order_type.lower()} PM work order {work_order.id} by user {user.email}")
        
        return work_order


