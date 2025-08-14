"""
API Views for Parts & Inventory Module
Production-grade endpoints with proper error handling and validation.
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils import timezone
import logging

from configurations.base_features.views.base_api_view import BaseAPIView
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
from parts.services import InventoryService, InventoryError, InsufficientStockError, IdempotencyConflictError
from .serializers import (
    PartApiSerializer, InventoryBatchApiSerializer, WorkOrderPartApiSerializer, 
    PartMovementApiSerializer, ReceivePartsInputSerializer, IssuePartsInputSerializer,
    ReturnPartsInputSerializer, TransferPartsInputSerializer, OnHandQuerySerializer,
    BatchQuerySerializer, MovementQuerySerializer
)

logger = logging.getLogger(__name__)


class PartApiView(BaseAPIView):
    """API view for Part management"""
    serializer_class = PartApiSerializer
    model_class = Part

    def get_queryset(self):
        """Get parts with optional filtering"""
        queryset = Part.objects.all().order_by('part_number')
        
        # Filter by part number (partial match)
        part_number = self.request.query_params.get('part_number')
        if part_number:
            queryset = queryset.filter(part_number__icontains=part_number)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        # Filter by make
        make = self.request.query_params.get('make')
        if make:
            queryset = queryset.filter(make__icontains=make)
            
        return queryset


class InventoryBatchApiView(BaseAPIView):
    """API view for InventoryBatch management"""
    serializer_class = InventoryBatchApiSerializer
    model_class = InventoryBatch

    def get_queryset(self):
        """Get batches with optional filtering"""
        queryset = InventoryBatch.objects.select_related('part', 'location').order_by(
            'part__part_number', 'location__name', 'received_date'
        )
        
        # Filter by part
        part_id = self.request.query_params.get('part_id')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        
        # Filter by location
        location_id = self.request.query_params.get('location_id')
        if location_id:
            queryset = queryset.filter(location_id=location_id)
        
        # Show only batches with stock
        show_empty = self.request.query_params.get('show_empty', 'false').lower()
        if show_empty != 'true':
            queryset = queryset.filter(qty_on_hand__gt=0)
            
        return queryset


class WorkOrderPartApiView(BaseAPIView):
    """API view for WorkOrderPart management"""
    serializer_class = WorkOrderPartApiSerializer
    model_class = WorkOrderPart

    def get_queryset(self):
        """Get work order parts with optional filtering"""
        queryset = WorkOrderPart.objects.select_related(
            'work_order', 'part', 'inventory_batch'
        ).order_by('-created_at')
        
        # Filter by work order
        work_order_id = self.request.query_params.get('work_order_id')
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)
        
        # Filter by part
        part_id = self.request.query_params.get('part_id')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
            
        return queryset


class PartMovementApiView(BaseAPIView):
    """API view for PartMovement management"""
    serializer_class = PartMovementApiSerializer
    model_class = PartMovement

    def get_queryset(self):
        """Get movements with optional filtering"""
        queryset = PartMovement.objects.select_related(
            'part', 'inventory_batch', 'from_location', 'to_location', 'work_order', 'created_by'
        ).order_by('-created_at')
        
        # Filter by part
        part_id = self.request.query_params.get('part_id')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        
        # Filter by work order
        work_order_id = self.request.query_params.get('work_order_id')
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)
        
        # Filter by movement type
        movement_type = self.request.query_params.get('movement_type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        # Date range filtering
        from_date = self.request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        
        to_date = self.request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)
        
        # Limit results for performance
        limit = min(int(self.request.query_params.get('limit', 100)), 1000)
        return queryset[:limit]