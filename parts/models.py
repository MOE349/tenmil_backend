from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from configurations.base_features.db.base_model import BaseModel
from tenant_users.models import TenantUser


class Part(BaseModel):
    """Master parts catalog with part information and pricing"""
    part_number = models.CharField(
        _("Part Number"), 
        max_length=100, 
        unique=True,
        help_text="Unique identifier for the part"
    )
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    last_price = models.DecimalField(
        _("Last Price"), 
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text="Most recent purchase price"
    )
    make = models.CharField(_("Make"), max_length=100, blank=True, null=True)
    category = models.CharField(_("Category"), max_length=100, blank=True, null=True)
    component = models.CharField(_("Component"), max_length=50, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['part_number']),
            models.Index(fields=['category']),
            models.Index(fields=['make']),
        ]
        verbose_name = _("Part")
        verbose_name_plural = _("Parts")

    def __str__(self):
        return f"[{self.part_number}] {self.name}"


class InventoryBatch(BaseModel):
    """Location-based inventory tracking with FIFO support"""
    part = models.ForeignKey(
        Part, 
        on_delete=models.CASCADE, 
        related_name="inventory_batches"
    )
    location = models.ForeignKey(
        "company.Location", 
        on_delete=models.CASCADE,
        related_name="inventory_batches"
    )
    qty_on_hand = models.IntegerField(
        _("Quantity On Hand"), 
        default=0,
        help_text="Available quantity for issue"
    )
    qty_reserved = models.IntegerField(
        _("Quantity Reserved"), 
        default=0,
        help_text="Quantity reserved for future work orders"
    )
    qty_received = models.IntegerField(
        _("Quantity Received"), 
        help_text="Original quantity received in this batch"
    )
    last_unit_cost = models.DecimalField(
        _("Last Unit Cost"), 
        max_digits=10, 
        decimal_places=4,
        help_text="Unit cost for this batch"
    )
    received_date = models.DateTimeField(
        _("Received Date"),
        help_text="Date when this batch was received (used for FIFO)"
    )
    aisle = models.CharField(
        _("Aisle"), 
        max_length=50, 
        default="0",
        help_text="Storage aisle location"
    )
    row = models.CharField(
        _("Row"), 
        max_length=50, 
        default="0",
        help_text="Storage row location"
    )
    bin = models.CharField(
        _("Bin"), 
        max_length=50, 
        default="0",
        help_text="Storage bin location"
    )

    class Meta:
        indexes = [
            models.Index(fields=['part', 'location', 'received_date']),
            models.Index(fields=['part', 'location'], condition=models.Q(qty_on_hand__gt=0), name='parts_inventory_available_idx'),
            models.Index(fields=['received_date']),
        ]
        verbose_name = _("Inventory Batch")
        verbose_name_plural = _("Inventory Batches")

    def clean(self):
        if self.qty_on_hand < 0:
            raise ValidationError(_("Quantity on hand cannot be negative"))
        if self.qty_reserved < 0:
            raise ValidationError(_("Quantity reserved cannot be negative"))
        if self.qty_received < 0:
            raise ValidationError(_("Quantity received cannot be negative"))
        if self.last_unit_cost < 0:
            raise ValidationError(_("Unit cost cannot be negative"))
        # Ensure qty_received is never modified after creation (immutable historical record)
        if self.pk and hasattr(self, '_original_qty_received'):
            if self.qty_received != self._original_qty_received:
                raise ValidationError(_("Quantity received is immutable and cannot be changed after creation"))

    @property
    def coded_location(self):
        """Generate coded location string: SITE_CODE-LOCATION_NAME-AISLE-ROW-BIN"""
        site_code = self.location.site.code if self.location.site else 'UNK'
        location_name = self.location.name or 'UNK'
        return f"{site_code}-{location_name}-{self.aisle}-{self.row}-{self.bin}"
    
    @property
    def available_qty(self):
        """Available quantity for allocation (on_hand - reserved)"""
        return max(0, self.qty_on_hand - self.qty_reserved)
    
    def __str__(self):
        return f"{self.part.part_number} @ {self.location} - {self.qty_on_hand} on hand"


class WorkOrderPart(BaseModel):
    """Work order parts association - links work orders to parts"""
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", 
        on_delete=models.CASCADE,
        related_name="work_order_parts"
    )
    part = models.ForeignKey(
        Part, 
        on_delete=models.CASCADE,
        related_name="work_order_parts"
    )

    class Meta:
        indexes = [
            models.Index(fields=['work_order']),
            models.Index(fields=['part']),
            models.Index(fields=['work_order', 'part']),
        ]
        unique_together = ['work_order', 'part']
        verbose_name = _("Work Order Part")
        verbose_name_plural = _("Work Order Parts")

    def __str__(self):
        return f"WO {self.work_order.code} - {self.part.part_number}"


class WorkOrderPartRequest(BaseModel):
    """Work order part requests and consumption tracking with cost snapshots"""
    work_order_part = models.ForeignKey(
        WorkOrderPart, 
        on_delete=models.CASCADE,
        related_name="part_requests"
    )
    inventory_batch = models.ForeignKey(
        InventoryBatch, 
        on_delete=models.CASCADE,
        related_name="work_order_part_requests",
        null=True,
        blank=True,
        help_text="Inventory batch used (null for planning purposes)"
    )
    qty_needed = models.IntegerField(
        _("Quantity Needed"), 
        null=True,
        blank=True,
        help_text="Optional: Quantity needed for planning purposes"
    )
    qty_used = models.IntegerField(
        _("Quantity Used"),
        null=True,
        blank=True, 
        help_text="Positive for issues, negative for returns"
    )
    unit_cost_snapshot = models.DecimalField(
        _("Unit Cost Snapshot"), 
        max_digits=10, 
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Unit cost at time of transaction"
    )
    total_parts_cost = models.DecimalField(
        _("Total Parts Cost"), 
        max_digits=12, 
        decimal_places=2,
        help_text="qty_used × unit_cost_snapshot (persisted for audit)"
    )
    is_approved = models.BooleanField(
        _("Is Approved"), 
        default=False,
        help_text="Whether this part request has been approved"
    )
    
    # Multi-flag workflow tracking
    is_requested = models.BooleanField(
        _("Is Requested"), 
        default=False,
        help_text="Mechanic has submitted the request"
    )
    is_available = models.BooleanField(
        _("Is Available"), 
        default=False,
        help_text="Parts are available (partially or completely)"
    )
    is_ordered = models.BooleanField(
        _("Is Ordered"), 
        default=False,
        help_text="Parts have been ordered externally"
    )
    is_delivered = models.BooleanField(
        _("Is Delivered"), 
        default=False,
        help_text="Parts have been delivered (partially or completely)"
    )
    
    # Quantity tracking for partial fulfillment
    qty_available = models.IntegerField(
        _("Quantity Available"),
        default=0,
        help_text="Total quantity currently available for pickup"
    )
    qty_delivered = models.IntegerField(
        _("Quantity Delivered"),
        default=0, 
        help_text="Total quantity delivered to mechanic so far"
    )

    class Meta:
        indexes = [
            models.Index(fields=['work_order_part']),
            models.Index(fields=['inventory_batch']),
            models.Index(fields=['is_approved']),
            models.Index(fields=['work_order_part', 'is_approved']),
            # Workflow indexes
            models.Index(fields=['is_requested']),
            models.Index(fields=['is_available']),
            models.Index(fields=['is_ordered']),
            models.Index(fields=['is_delivered']),
            models.Index(fields=['is_requested', 'is_available']),
            models.Index(fields=['work_order_part', 'is_requested']),
        ]
        verbose_name = _("Work Order Part Request")
        verbose_name_plural = _("Work Order Part Requests")

    def clean(self):
        # When qty_used is provided, inventory_batch is required
        if self.qty_used is not None and self.qty_used != 0 and self.inventory_batch is None:
            raise ValidationError(_("Inventory batch is required when quantity used is specified"))
        
        # Allow qty_used = 0 for planning purposes when inventory_batch is null
        if self.qty_used == 0 and self.inventory_batch is not None:
            raise ValidationError(_("Quantity used cannot be zero when inventory batch is specified"))
        if self.unit_cost_snapshot is not None and self.unit_cost_snapshot < 0:
            raise ValidationError(_("Unit cost snapshot cannot be negative"))
        if self.qty_needed is not None and self.qty_needed <= 0:
            raise ValidationError(_("Quantity needed must be positive if specified"))

    def save(self, *args, **kwargs):
        from django.utils import timezone
        
        # Capture previous state for audit logging
        previous_flags = {}
        if self.pk:
            try:
                old_instance = WorkOrderPartRequest.objects.get(pk=self.pk)
                previous_flags = {
                    'is_requested': old_instance.is_requested,
                    'is_available': old_instance.is_available,
                    'is_ordered': old_instance.is_ordered,
                    'is_delivered': old_instance.is_delivered,
                }
            except WorkOrderPartRequest.DoesNotExist:
                pass
        
        # Auto approve if qty_used is provided
        if self.qty_used is not None and self.qty_used > 0:
            self.is_approved = True
            self.is_requested = False
            self.is_available = False
            self.is_ordered = False
            self.is_delivered = False
            

        # Auto-calculate total_parts_cost (handle null values for planning)
        if self.unit_cost_snapshot is not None and self.qty_used is not None:
            self.total_parts_cost = self.qty_used * self.unit_cost_snapshot
        else:
            self.total_parts_cost = 0
            
        super().save(*args, **kwargs)
        
        # Create audit log entry if flags changed
        current_flags = {
            'is_requested': self.is_requested,
            'is_available': self.is_available,
            'is_ordered': self.is_ordered,
            'is_delivered': self.is_delivered,
        }
        
        if previous_flags != current_flags:
            self._create_audit_log(previous_flags, current_flags)
    
    def _create_audit_log(self, previous_flags, new_flags, action_type=None, performed_by=None, notes=None, **kwargs):
        """Helper method to create audit log entries"""
        # Determine action type from flag changes if not provided
        if not action_type:
            if new_flags['is_requested'] and not previous_flags.get('is_requested', False):
                action_type = WorkOrderPartRequestLog.ActionType.REQUESTED
            elif new_flags['is_available'] and not previous_flags.get('is_available', False):
                # Determine if partial or full availability
                if self.qty_available >= (self.qty_needed or 0):
                    action_type = WorkOrderPartRequestLog.ActionType.FULLY_AVAILABLE
                else:
                    action_type = WorkOrderPartRequestLog.ActionType.PARTIAL_AVAILABLE
            elif new_flags['is_ordered'] and not previous_flags.get('is_ordered', False):
                action_type = WorkOrderPartRequestLog.ActionType.ORDERED
            elif new_flags['is_delivered'] and not previous_flags.get('is_delivered', False):
                # Determine if partial or full delivery
                if self.qty_delivered >= (self.qty_needed or 0):
                    action_type = WorkOrderPartRequestLog.ActionType.FULLY_DELIVERED
                else:
                    action_type = WorkOrderPartRequestLog.ActionType.PARTIAL_DELIVERED
        
        if action_type:
            WorkOrderPartRequestLog.objects.create(
                work_order_part_request=self,
                action_type=action_type,
                performed_by=performed_by,
                qty_needed_snapshot=self.qty_needed,
                qty_available_snapshot=self.qty_available,
                qty_delivered_snapshot=self.qty_delivered,
                qty_used_snapshot=self.qty_used,
                inventory_batch_snapshot=self.inventory_batch,
                notes=notes,
                previous_status_flags=previous_flags,
                new_status_flags=new_flags,
                **kwargs
            )

    def get_first_requested_at(self):
        """Get timestamp of first request"""
        log = self.audit_logs.filter(
            action_type=WorkOrderPartRequestLog.ActionType.REQUESTED
        ).first()
        return log.created_at if log else None
    
    def get_first_available_at(self):
        """Get timestamp when parts first became available"""
        log = self.audit_logs.filter(
            action_type__in=[
                WorkOrderPartRequestLog.ActionType.PARTIAL_AVAILABLE,
                WorkOrderPartRequestLog.ActionType.FULLY_AVAILABLE
            ]
        ).first()
        return log.created_at if log else None
    
    def get_fully_available_at(self):
        """Get timestamp when all parts became available"""
        log = self.audit_logs.filter(
            action_type=WorkOrderPartRequestLog.ActionType.FULLY_AVAILABLE
        ).first()
        return log.created_at if log else None
    
    def get_delivery_history(self):
        """Get all delivery events with quantities"""
        return self.audit_logs.filter(
            action_type__in=[
                WorkOrderPartRequestLog.ActionType.PARTIAL_DELIVERED,
                WorkOrderPartRequestLog.ActionType.FULLY_DELIVERED
            ]
        ).order_by('created_at')
    
    def is_fully_fulfilled(self):
        """Check if request is completely fulfilled"""
        return self.qty_delivered >= (self.qty_needed or 0)

    def __str__(self):
        qty_display = self.qty_used if self.qty_used is not None else "TBD"
        return f"WO {self.work_order_part.work_order.code} - {self.work_order_part.part.part_number} - Qty: {qty_display}"


class WorkOrderPartRequestLog(BaseModel):
    """Specialized audit trail for WorkOrderPartRequest workflow operations"""
    
    class ActionType(models.TextChoices):
        REQUESTED = 'requested', _('Requested')           
        PARTIAL_AVAILABLE = 'partial_available', _('Partial Available')
        FULLY_AVAILABLE = 'fully_available', _('Fully Available')
        ORDERED = 'ordered', _('Ordered')                 
        PARTIAL_DELIVERED = 'partial_delivered', _('Partial Delivered')
        FULLY_DELIVERED = 'fully_delivered', _('Fully Delivered')
        PICKED_UP = 'picked_up', _('Picked Up')          
        CONSUMED = 'consumed', _('Consumed')              
        CANCELLED = 'cancelled', _('Cancelled')           
        RETURNED = 'returned', _('Returned')
        AVAILABILITY_CANCELLED = 'availability_cancelled', _('Availability Cancelled')
        BATCH_REASSIGNED = 'batch_reassigned', _('Batch Reassigned')
        
    work_order_part_request = models.ForeignKey(
        WorkOrderPartRequest,
        on_delete=models.CASCADE,
        related_name="audit_logs"
    )
    action_type = models.CharField(
        _("Action Type"),
        max_length=25,
        choices=ActionType.choices
    )
    performed_by = models.ForeignKey(
        TenantUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wopr_audit_logs",
        help_text="User who performed this action"
    )
    
    # Quantity-specific tracking for partial operations
    qty_in_action = models.IntegerField(
        _("Quantity in Action"),
        null=True,
        blank=True,
        help_text="Specific quantity involved in this action"
    )
    qty_total_after_action = models.IntegerField(
        _("Total Quantity After Action"),
        null=True,
        blank=True,
        help_text="Total quantity after this action completed"
    )
    
    # Snapshot data at time of action
    qty_needed_snapshot = models.IntegerField(
        _("Qty Needed Snapshot"),
        null=True,
        blank=True,
        help_text="qty_needed value at time of action"
    )
    qty_available_snapshot = models.IntegerField(
        _("Qty Available Snapshot"),
        null=True,
        blank=True,
        help_text="qty_available value at time of action"
    )
    qty_delivered_snapshot = models.IntegerField(
        _("Qty Delivered Snapshot"),
        null=True,
        blank=True,
        help_text="qty_delivered value at time of action"
    )
    qty_used_snapshot = models.IntegerField(
        _("Qty Used Snapshot"), 
        null=True,
        blank=True,
        help_text="qty_used value at time of action"
    )
    
    inventory_batch_snapshot = models.ForeignKey(
        InventoryBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Inventory batch at time of action"
    )
    
    # Action-specific metadata
    notes = models.TextField(
        _("Notes"),
        blank=True,
        null=True,
        help_text="Optional notes about this action"
    )
    previous_status_flags = models.JSONField(
        _("Previous Status Flags"),
        default=dict,
        help_text="Snapshot of all status flags before this action"
    )
    new_status_flags = models.JSONField(
        _("New Status Flags"),
        default=dict,
        help_text="Snapshot of all status flags after this action"
    )
    
    # System metadata
    ip_address = models.GenericIPAddressField(
        _("IP Address"),
        null=True,
        blank=True,
        help_text="IP address of user performing action"
    )
    user_agent = models.TextField(
        _("User Agent"),
        blank=True,
        null=True,
        help_text="Browser/app user agent"
    )

    class Meta:
        indexes = [
            models.Index(fields=['work_order_part_request', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['performed_by', 'created_at']),
            models.Index(fields=['work_order_part_request', 'action_type']),
        ]
        verbose_name = _("Work Order Part Request Log")
        verbose_name_plural = _("Work Order Part Request Logs")
        ordering = ['-created_at']

    def __str__(self):
        user_display = self.performed_by.email if self.performed_by else "System"
        return f"WOPR {self.work_order_part_request.id} - {self.action_type} by {user_display} @ {self.created_at}"


class PartMovement(BaseModel):
    """Immutable audit trail for all stock changes - single source of truth"""
    
    class MovementType(models.TextChoices):
        RECEIVE = 'receive', _('Receive')
        ISSUE = 'issue', _('Issue')
        RETURN = 'return', _('Return')
        TRANSFER_OUT = 'transfer_out', _('Transfer Out')
        TRANSFER_IN = 'transfer_in', _('Transfer In')
        ADJUSTMENT = 'adjustment', _('Adjustment')
        RTV_OUT = 'rtv_out', _('Return to Vendor Out')
        COUNT_ADJUST = 'count_adjust', _('Count Adjustment')

    part = models.ForeignKey(
        Part, 
        on_delete=models.CASCADE,
        related_name="movements"
    )
    inventory_batch = models.ForeignKey(
        InventoryBatch, 
        on_delete=models.CASCADE,
        related_name="movements",
        null=True, 
        blank=True,
        help_text="Null for pre-batch actions"
    )
    from_location = models.ForeignKey(
        "company.Location", 
        on_delete=models.SET_NULL,
        related_name="part_movements_from",
        null=True, 
        blank=True
    )
    to_location = models.ForeignKey(
        "company.Location", 
        on_delete=models.SET_NULL,
        related_name="part_movements_to",
        null=True, 
        blank=True
    )
    movement_type = models.CharField(
        _("Movement Type"), 
        max_length=20, 
        choices=MovementType.choices
    )
    qty_delta = models.IntegerField(
        _("Quantity Delta"), 
        help_text="Signed quantity: positive increases stock, negative decreases"
    )
    work_order = models.ForeignKey(
        "work_orders.WorkOrder", 
        on_delete=models.SET_NULL,
        related_name="part_movements",
        null=True, 
        blank=True
    )
    receipt_id = models.CharField(
        _("Receipt ID"), 
        max_length=100, 
        null=True, 
        blank=True,
        help_text="External receipt/document reference"
    )
    created_by = models.ForeignKey(
        TenantUser, 
        on_delete=models.SET_NULL,
        related_name="part_movements",
        null=True, 
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['part', 'created_at']),
            models.Index(fields=['work_order', 'created_at']),
            models.Index(fields=['movement_type', 'created_at']),
            models.Index(fields=['from_location', 'created_at']),
            models.Index(fields=['to_location', 'created_at']),
            models.Index(fields=['inventory_batch', 'created_at']),
        ]
        verbose_name = _("Part Movement")
        verbose_name_plural = _("Part Movements")
        ordering = ['-created_at']

    def clean(self):
        if self.qty_delta == 0:
            raise ValidationError(_("Quantity delta cannot be zero"))
        
        # Validate movement type consistency
        if self.movement_type in [self.MovementType.RECEIVE, self.MovementType.TRANSFER_IN, 
                                  self.MovementType.RETURN] and self.qty_delta <= 0:
            raise ValidationError(_("Receive, transfer in, and return movements must have positive quantity delta"))
        
        if self.movement_type in [self.MovementType.ISSUE, self.MovementType.TRANSFER_OUT, 
                                  self.MovementType.RTV_OUT] and self.qty_delta >= 0:
            raise ValidationError(_("Issue, transfer out, and RTV movements must have negative quantity delta"))

    def __str__(self):
        return f"{self.part.part_number} - {self.movement_type} - {self.qty_delta} @ {self.created_at}"


