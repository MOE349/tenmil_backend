"""
Inventory Operations API Views
Handles receive, issue, return, and transfer operations.
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils import timezone
import logging

from configurations.base_features.views.base_api_view import BaseAPIView
from parts.services import InventoryService, InventoryError, InsufficientStockError, IdempotencyConflictError
from .serializers import (
    ReceivePartsInputSerializer, IssuePartsInputSerializer,
    ReturnPartsInputSerializer, TransferPartsInputSerializer, OnHandQuerySerializer,
    BatchQuerySerializer, MovementQuerySerializer
)

logger = logging.getLogger(__name__)


class InventoryOperationsApiView(BaseAPIView):
    """
    API view for inventory operations (receive, issue, return, transfer)
    """
    
    def handle_inventory_error(self, error):
        """Handle inventory-specific errors"""
        if isinstance(error, InsufficientStockError):
            return self.format_response(
                data=None,
                errors=[{
                    'code': 'INSUFFICIENT_STOCK',
                    'message': str(error),
                    'available_qty': getattr(error, 'available_qty', 0)
                }],
                status_code=status.HTTP_400_BAD_REQUEST
            )
        elif isinstance(error, IdempotencyConflictError):
            return self.format_response(
                data=None,
                errors=[{
                    'code': 'IDEMPOTENCY_CONFLICT',
                    'message': str(error)
                }],
                status_code=status.HTTP_409_CONFLICT
            )
        elif isinstance(error, InventoryError):
            return self.format_response(
                data=None,
                errors=[{
                    'code': 'INVENTORY_ERROR',
                    'message': str(error)
                }],
                status_code=status.HTTP_400_BAD_REQUEST
            )
        elif isinstance(error, DjangoValidationError):
            return self.format_response(
                data=None,
                errors=[{
                    'code': 'VALIDATION_ERROR',
                    'message': str(error)
                }],
                status_code=status.HTTP_400_BAD_REQUEST
            )
        else:
            logger.error(f"Unexpected error in inventory operation: {str(error)}")
            return self.format_response(
                data=None,
                errors=[{
                    'code': 'INTERNAL_ERROR',
                    'message': 'An unexpected error occurred'
                }],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='receive')
    def receive_parts(self, request):
        """
        Receive parts into inventory
        POST /inventory/receive/
        """
        try:
            # Validate input
            serializer = ReceivePartsInputSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Call service
            result = InventoryService.receive_parts(
                part_id=str(serializer.validated_data['part_id']),
                location_id=str(serializer.validated_data['location_id']),
                qty=serializer.validated_data['qty'],
                unit_cost=serializer.validated_data['unit_cost'],
                received_date=serializer.validated_data['received_date'],
                created_by=request.user,
                receipt_id=serializer.validated_data.get('receipt_id'),
                idempotency_key=serializer.validated_data.get('idempotency_key')
            )

            return self.format_response(
                data=result,
                errors=None,
                status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return self.handle_inventory_error(e)

    @action(detail=False, methods=['post'], url_path='issue')
    def issue_parts(self, request):
        """
        Issue parts to work order
        POST /inventory/issue/
        """
        try:
            # Validate input
            serializer = IssuePartsInputSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Call service
            result = InventoryService.issue_to_work_order(
                work_order_id=str(serializer.validated_data['work_order_id']),
                part_id=str(serializer.validated_data['part_id']),
                location_id=str(serializer.validated_data['location_id']),
                qty_requested=serializer.validated_data['qty'],
                created_by=request.user,
                idempotency_key=serializer.validated_data.get('idempotency_key')
            )

            return self.format_response(
                data=result,
                errors=None,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.handle_inventory_error(e)

    @action(detail=False, methods=['post'], url_path='return')
    def return_parts(self, request):
        """
        Return parts from work order
        POST /inventory/return/
        """
        try:
            # Validate input
            serializer = ReturnPartsInputSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Call service
            result = InventoryService.return_from_work_order(
                work_order_id=str(serializer.validated_data['work_order_id']),
                part_id=str(serializer.validated_data['part_id']),
                location_id=str(serializer.validated_data['location_id']),
                qty_to_return=serializer.validated_data['qty'],
                created_by=request.user,
                idempotency_key=serializer.validated_data.get('idempotency_key')
            )

            return self.format_response(
                data=result,
                errors=None,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.handle_inventory_error(e)

    @action(detail=False, methods=['post'], url_path='transfer')
    def transfer_parts(self, request):
        """
        Transfer parts between locations
        POST /inventory/transfer/
        """
        try:
            # Validate input
            serializer = TransferPartsInputSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Call service
            result = InventoryService.transfer_between_locations(
                part_id=str(serializer.validated_data['part_id']),
                from_location_id=str(serializer.validated_data['from_location_id']),
                to_location_id=str(serializer.validated_data['to_location_id']),
                qty=serializer.validated_data['qty'],
                created_by=request.user,
                idempotency_key=serializer.validated_data.get('idempotency_key')
            )

            return self.format_response(
                data=result,
                errors=None,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.handle_inventory_error(e)

    @action(detail=False, methods=['get'], url_path='on-hand')
    def get_on_hand(self, request):
        """
        Get on-hand inventory summary
        GET /inventory/on-hand/?part_id=&location_id=
        """
        try:
            # Validate query parameters
            serializer = OnHandQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Call service
            result = InventoryService.get_on_hand_summary(
                part_id=str(serializer.validated_data['part_id']) if serializer.validated_data.get('part_id') else None,
                location_id=str(serializer.validated_data['location_id']) if serializer.validated_data.get('location_id') else None
            )

            return self.format_response(
                data={'summary': result},
                errors=None,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.handle_inventory_error(e)

    @action(detail=False, methods=['get'], url_path='batches')
    def get_batches(self, request):
        """
        Get detailed batch information
        GET /inventory/batches/?part_id=&location_id=
        """
        try:
            # Validate query parameters
            serializer = BatchQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Call service
            result = InventoryService.get_batches(
                part_id=str(serializer.validated_data['part_id']) if serializer.validated_data.get('part_id') else None,
                location_id=str(serializer.validated_data['location_id']) if serializer.validated_data.get('location_id') else None
            )

            return self.format_response(
                data={'batches': result},
                errors=None,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.handle_inventory_error(e)

    @action(detail=False, methods=['get'], url_path='movements')
    def get_movements(self, request):
        """
        Get movement history
        GET /inventory/movements/?part_id=&location_id=&work_order_id=&from_date=&to_date=&limit=
        """
        try:
            # Validate query parameters
            serializer = MovementQuerySerializer(data=request.query_params)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Call service
            result = InventoryService.get_movements(
                part_id=str(serializer.validated_data['part_id']) if serializer.validated_data.get('part_id') else None,
                location_id=str(serializer.validated_data['location_id']) if serializer.validated_data.get('location_id') else None,
                work_order_id=str(serializer.validated_data['work_order_id']) if serializer.validated_data.get('work_order_id') else None,
                from_date=serializer.validated_data.get('from_date'),
                to_date=serializer.validated_data.get('to_date'),
                limit=serializer.validated_data.get('limit', 100)
            )

            return self.format_response(
                data={'movements': result},
                errors=None,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            return self.handle_inventory_error(e)


class WorkOrderPartsApiView(BaseAPIView):
    """
    Specialized view for work order parts operations
    """
    
    @action(detail=True, methods=['get'], url_path='parts')
    def get_work_order_parts(self, request, pk=None):
        """
        Get all parts for a specific work order
        GET /work-orders/{work_order_id}/parts/
        """
        try:
            # Call service
            result = InventoryService.get_work_order_parts(work_order_id=pk)

            return self.format_response(
                data={'parts': result},
                errors=None,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error getting work order parts: {str(e)}")
            return self.format_response(
                data=None,
                errors=[{
                    'code': 'INTERNAL_ERROR',
                    'message': 'An error occurred while retrieving work order parts'
                }],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
