from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from configurations.base_features.db.base_model import BaseModel
from tenant_users.models import TenantUser as User


class Part(BaseModel):
    """
    Master parts catalog.
    Stores general information about parts/components.
    """
    part_number = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Unique part identifier"
    )
    name = models.CharField(
        max_length=255,
        help_text="Descriptive name of the part"
    )
    description = models.TextField(
        blank=True, 
        null=True,
        help_text="Detailed description of the part"
    )
    last_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Most recent purchase price"
    )
    make = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Manufacturer or brand"
    )
    category = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Part category for organization"
    )
    component = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Component type or classification"
    )

    class Meta:
        verbose_name = "Part"
        verbose_name_plural = "Parts"
        indexes = [
            models.Index(fields=['part_number']),
            models.Index(fields=['category']),
            models.Index(fields=['make']),
        ]

    def __str__(self):
        return f"{self.part_number} - {self.name}"

    @property
    def total_qty_on_hand(self):
        """Calculate total quantity on hand across all batches"""
        return self.inventory_batches.aggregate(
            total=models.Sum('qty_on_hand')
        )['total'] or 0

    @property
    def total_qty_available(self):
        """Calculate total available quantity (on hand - reserved)"""
        return self.inventory_batches.aggregate(
            available=models.Sum(
                models.F('qty_on_hand') - models.F('qty_reserved')
            )
        )['available'] or 0


class InventoryBatch(BaseModel):
    """
    Inventory batches by location.
    Tracks quantities and costs for parts at specific locations.
    """
    part = models.ForeignKey(
        Part, 
        on_delete=models.CASCADE,
        related_name='inventory_batches',
        help_text="Part this batch belongs to"
    )
    location = models.ForeignKey(
        'company.Location',
        on_delete=models.CASCADE,
        related_name='inventory_batches',
        help_text="Location where this batch is stored"
    )
    qty_on_hand = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Physical quantity available"
    )
    qty_reserved = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Quantity reserved for work orders"
    )
    last_unit_cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost per unit for this batch"
    )
    received_date = models.DateField(
        help_text="Date this batch was received"
    )

    class Meta:
        verbose_name = "Inventory Batch"
        verbose_name_plural = "Inventory Batches"
        indexes = [
            models.Index(fields=['part', 'location', 'received_date']),
            models.Index(fields=['part', 'location'], condition=models.Q(qty_on_hand__gt=0), name='idx_inventory_batch_available'),
        ]

    def __str__(self):
        return f"{self.part.part_number} @ {self.location.name} - {self.qty_on_hand} units"

    @property
    def qty_available(self):
        """Available quantity (on hand - reserved)"""
        return max(0, self.qty_on_hand - self.qty_reserved)

    @property
    def total_value(self):
        """Total value of this batch"""
        return self.qty_on_hand * self.last_unit_cost

    def clean(self):
        """Validate that reserved quantity doesn't exceed on hand"""
        from django.core.exceptions import ValidationError
        if self.qty_reserved > self.qty_on_hand:
            raise ValidationError(
                "Reserved quantity cannot exceed quantity on hand."
            )


class WorkOrderPart(BaseModel):
    """
    Parts used in work orders.
    Tracks part consumption and returns for work orders.
    """
    work_order = models.ForeignKey(
        'work_orders.WorkOrder',
        on_delete=models.CASCADE,
        related_name='work_order_parts',
        help_text="Work order this part usage belongs to"
    )
    part = models.ForeignKey(
        Part,
        on_delete=models.CASCADE,
        related_name='work_order_usages',
        help_text="Part that was used"
    )
    inventory_batch = models.ForeignKey(
        InventoryBatch,
        on_delete=models.CASCADE,
        related_name='work_order_usages',
        help_text="Specific inventory batch the part came from"
    )
    qty_used = models.IntegerField(
        help_text="Quantity used (positive = issue, negative = return)"
    )
    unit_cost_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Unit cost at the time of transaction"
    )
    total_parts_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Calculated: qty_used × unit_cost_snapshot"
    )

    class Meta:
        verbose_name = "Work Order Part"
        verbose_name_plural = "Work Order Parts"
        indexes = [
            models.Index(fields=['work_order']),
            models.Index(fields=['part']),
            models.Index(fields=['inventory_batch']),
        ]

    def __str__(self):
        action = "issued" if self.qty_used > 0 else "returned"
        return f"{abs(self.qty_used)} {self.part.part_number} {action} to {self.work_order.code}"

    def save(self, *args, **kwargs):
        """Auto-calculate total_parts_cost"""
        self.total_parts_cost = self.qty_used * self.unit_cost_snapshot
        super().save(*args, **kwargs)

    def clean(self):
        """Validate that part matches inventory batch"""
        from django.core.exceptions import ValidationError
        if self.inventory_batch and self.part != self.inventory_batch.part:
            raise ValidationError(
                "Selected inventory batch must belong to the selected part."
            )


class PartMovement(BaseModel):
    """
    Comprehensive log of all part movements.
    Tracks all inventory transactions and movements.
    """
    class MovementTypeChoices(models.TextChoices):
        RECEIVE = 'receive', 'Receive'
        ISSUE = 'issue', 'Issue'
        RETURN = 'return', 'Return'
        TRANSFER_OUT = 'transfer_out', 'Transfer Out'
        TRANSFER_IN = 'transfer_in', 'Transfer In'
        ADJUSTMENT = 'adjustment', 'Adjustment'
        RTV_OUT = 'rtv_out', 'Return to Vendor (Out)'
        COUNT_ADJUST = 'count_adjust', 'Count Adjustment'

    part = models.ForeignKey(
        Part,
        on_delete=models.CASCADE,
        related_name='movements',
        help_text="Part that was moved"
    )
    inventory_batch = models.ForeignKey(
        InventoryBatch,
        on_delete=models.CASCADE,
        related_name='movements',
        null=True,
        blank=True,
        help_text="Inventory batch (nullable for pre-batch actions)"
    )
    from_location = models.ForeignKey(
        'company.Location',
        on_delete=models.CASCADE,
        related_name='movements_from',
        null=True,
        blank=True,
        help_text="Source location for the movement"
    )
    to_location = models.ForeignKey(
        'company.Location',
        on_delete=models.CASCADE,
        related_name='movements_to',
        null=True,
        blank=True,
        help_text="Destination location for the movement"
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementTypeChoices.choices,
        help_text="Type of movement"
    )
    qty_delta = models.IntegerField(
        help_text="Quantity change (positive or negative)"
    )
    work_order = models.ForeignKey(
        'work_orders.WorkOrder',
        on_delete=models.CASCADE,
        related_name='movements',
        null=True,
        blank=True,
        help_text="Associated work order (if applicable)"
    )
    receipt_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Receipt/transaction reference ID"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Additional notes about the movement"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='movements',
        help_text="User who performed the movement"
    )

    class Meta:
        verbose_name = "Part Movement"
        verbose_name_plural = "Part Movements"
        indexes = [
            models.Index(fields=['part', 'created_at']),
            models.Index(fields=['movement_type', 'created_at']),
            models.Index(fields=['work_order', 'created_at']),
            models.Index(fields=['from_location']),
            models.Index(fields=['to_location']),
            models.Index(fields=['receipt_id']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        movement_desc = f"{self.movement_type.title()}: {self.qty_delta} {self.part.part_number}"
        if self.from_location and self.to_location:
            movement_desc += f" from {self.from_location.name} to {self.to_location.name}"
        elif self.from_location:
            movement_desc += f" from {self.from_location.name}"
        elif self.to_location:
            movement_desc += f" to {self.to_location.name}"
        return movement_desc

    def clean(self):
        """Validate movement logic"""
        from django.core.exceptions import ValidationError
        
        # Validate that inventory batch belongs to the part
        if self.inventory_batch and self.part != self.inventory_batch.part:
            raise ValidationError(
                "Inventory batch must belong to the selected part."
            )

        # Validate location requirements for transfers
        if self.movement_type in ['transfer_out', 'transfer_in']:
            if not self.from_location or not self.to_location:
                raise ValidationError(
                    "Transfer movements require both from and to locations."
                )
            if self.from_location == self.to_location:
                raise ValidationError(
                    "From and to locations cannot be the same for transfers."
                )


class IdempotencyKey(BaseModel):
    """
    Idempotency tracking to prevent duplicate operations.
    """
    key = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique idempotency key"
    )
    operation_type = models.CharField(
        max_length=50,
        help_text="Type of operation (receive, issue, return, transfer)"
    )
    request_data = models.JSONField(
        help_text="Original request data for the operation"
    )
    response_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Response data from the successful operation"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='idempotency_keys',
        help_text="User who performed the operation"
    )

    class Meta:
        verbose_name = "Idempotency Key"
        verbose_name_plural = "Idempotency Keys"
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['operation_type', 'created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.operation_type}: {self.key}"

