from django.contrib.contenttypes.models import ContentType
from work_orders.models import WorkOrder, WorkOrderChecklist
from asset_backlogs.models import AssetBacklog
import logging

logger = logging.getLogger(__name__)


class WorkOrderService:
    """Service for work order operations"""
    
    @staticmethod
    def import_asset_backlogs_to_work_order(work_order_id, user):
        """
        Import asset backlogs into work order checklist and remove them from backlogs
        
        Args:
            work_order_id: The work order ID to import backlogs into
            user: The user performing the import
            
        Returns:
            dict: Result with count of imported items and any errors
        """
        try:
            # Get the work order
            work_order = WorkOrder.objects.get(id=work_order_id)
            logger.info(f"Importing asset backlogs for work order {work_order.id}")
            
            # Get the asset from the work order
            asset = work_order.asset
            if not asset:
                logger.error(f"No asset found for work order {work_order.id}")
                return {
                    'success': False,
                    'error': 'No asset found for this work order',
                    'imported_count': 0
                }
            
            # Get all backlogs for this asset
            content_type = ContentType.objects.get_for_model(asset)
            asset_backlogs = AssetBacklog.objects.filter(
                content_type=content_type,
                object_id=asset.id
            )
            
            if not asset_backlogs.exists():
                logger.info(f"No backlogs found for asset {asset.id}")
                return {
                    'success': True,
                    'message': 'No backlogs found for this asset',
                    'imported_count': 0
                }
            
            # Import each backlog as a checklist item and remove from backlogs
            imported_count = 0
            for backlog in asset_backlogs:
                # Check if this backlog is already imported (to avoid duplicates)
                existing_checklist = WorkOrderChecklist.objects.filter(
                    work_order=work_order,
                    description=backlog.name,
                    is_backlog=True
                ).first()
                
                if existing_checklist:
                    logger.debug(f"Backlog '{backlog.name}' already exists in work order {work_order.id}")
                    continue
                
                # Create new checklist item
                checklist_item = WorkOrderChecklist.objects.create(
                    work_order=work_order,
                    description=backlog.name,
                    is_backlog=True,
                    is_custom=False
                )
                
                # Remove the backlog from asset backlogs
                backlog.delete()
                logger.info(f"Removed backlog '{backlog.name}' from asset {asset.id}")
                
                imported_count += 1
                logger.info(f"Imported backlog '{backlog.name}' to work order {work_order.id}")
            
            logger.info(f"Successfully imported {imported_count} backlogs to work order {work_order.id}")
            
            return {
                'success': True,
                'message': f'Successfully imported {imported_count} backlogs',
                'imported_count': imported_count,
                'work_order_id': work_order.id
            }
            
        except WorkOrder.DoesNotExist:
            logger.error(f"Work order {work_order_id} not found")
            return {
                'success': False,
                'error': 'Work order not found',
                'imported_count': 0
            }
        except Exception as e:
            logger.error(f"Error importing backlogs to work order {work_order_id}: {e}")
            return {
                'success': False,
                'error': f'Error importing backlogs: {str(e)}',
                'imported_count': 0
            }
    
    @staticmethod
    def handle_work_order_completion(work_order_id, user):
        """
        Handle work order completion - return uncompleted backlog items to asset backlogs
        
        Args:
            work_order_id: The work order ID being completed
            user: The user completing the work order
            
        Returns:
            dict: Result with count of returned items and any errors
        """
        try:
            # Get the work order
            work_order = WorkOrder.objects.get(id=work_order_id)
            logger.info(f"Handling completion for work order {work_order.id}")
            
            # Get the asset from the work order
            asset = work_order.asset
            if not asset:
                logger.error(f"No asset found for work order {work_order.id}")
                return {
                    'success': False,
                    'error': 'No asset found for this work order',
                    'returned_count': 0
                }
            
            # Get all uncompleted backlog checklist items
            uncompleted_backlog_items = WorkOrderChecklist.objects.filter(
                work_order=work_order,
                is_backlog=True,
                completed_by__isnull=True  # Not completed
            )
            
            if not uncompleted_backlog_items.exists():
                logger.info(f"No uncompleted backlog items found for work order {work_order.id}")
                return {
                    'success': True,
                    'message': 'No uncompleted backlog items to return',
                    'returned_count': 0
                }
            
            # Return uncompleted backlog items to asset backlogs
            returned_count = 0
            content_type = ContentType.objects.get_for_model(asset)
            
            for checklist_item in uncompleted_backlog_items:
                # Check if this backlog already exists (to avoid duplicates)
                existing_backlog = AssetBacklog.objects.filter(
                    content_type=content_type,
                    object_id=asset.id,
                    name=checklist_item.description
                ).first()
                
                if existing_backlog:
                    logger.debug(f"Backlog '{checklist_item.description}' already exists for asset {asset.id}")
                    continue
                
                # Create new backlog item
                backlog_item = AssetBacklog.objects.create(
                    content_type=content_type,
                    object_id=asset.id,
                    name=checklist_item.description
                )
                
                returned_count += 1
                logger.info(f"Returned backlog '{checklist_item.description}' to asset {asset.id}")
            
            logger.info(f"Successfully returned {returned_count} backlog items to asset {asset.id}")
            
            return {
                'success': True,
                'message': f'Successfully returned {returned_count} backlog items',
                'returned_count': returned_count,
                'work_order_id': work_order.id
            }
            
        except WorkOrder.DoesNotExist:
            logger.error(f"Work order {work_order_id} not found")
            return {
                'success': False,
                'error': 'Work order not found',
                'returned_count': 0
            }
        except Exception as e:
            logger.error(f"Error handling work order completion {work_order_id}: {e}")
            return {
                'success': False,
                'error': f'Error handling completion: {str(e)}',
                'returned_count': 0
            } 