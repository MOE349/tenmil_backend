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
    qty_on_hand = models.DecimalField(
        _("Quantity On Hand"), 
        max_digits=10, 
        decimal_places=3,
        default=0,
        help_text="Available quantity for issue"
    )
    qty_reserved = models.DecimalField(
        _("Quantity Reserved"), 
        max_digits=10, 
        decimal_places=3,
        default=0,
        help_text="Quantity reserved for future work orders"
    )
    qty_received = models.DecimalField(
        _("Quantity Received"), 
        max_digits=10, 
        decimal_places=3,
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
        if self.qty_received <= 0:
            raise ValidationError(_("Quantity received must be positive"))
        if self.last_unit_cost < 0:
            raise ValidationError(_("Unit cost cannot be negative"))
        # Ensure qty_received is never modified after creation (immutable historical record)
        if self.pk and hasattr(self, '_original_qty_received'):
            if self.qty_received != self._original_qty_received:
                raise ValidationError(_("Quantity received is immutable and cannot be changed after creation"))

    def __str__(self):
        return f"{self.part.part_number} @ {self.location} - {self.qty_on_hand} on hand"


class WorkOrderPart(BaseModel):
    """Work order parts consumption tracking with cost snapshots"""
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
    inventory_batch = models.ForeignKey(
        InventoryBatch, 
        on_delete=models.CASCADE,
        related_name="work_order_parts"
    )
    qty_used = models.DecimalField(
        _("Quantity Used"), 
        max_digits=10, 
        decimal_places=3,
        help_text="Positive for issues, negative for returns"
    )
    unit_cost_snapshot = models.DecimalField(
        _("Unit Cost Snapshot"), 
        max_digits=10, 
        decimal_places=4,
        help_text="Unit cost at time of transaction"
    )
    total_parts_cost = models.DecimalField(
        _("Total Parts Cost"), 
        max_digits=12, 
        decimal_places=2,
        help_text="qty_used × unit_cost_snapshot (persisted for audit)"
    )

    class Meta:
        indexes = [
            models.Index(fields=['work_order']),
            models.Index(fields=['part']),
            models.Index(fields=['inventory_batch']),
            models.Index(fields=['work_order', 'part']),
        ]
        verbose_name = _("Work Order Part")
        verbose_name_plural = _("Work Order Parts")

    def clean(self):
        if self.qty_used == 0:
            raise ValidationError(_("Quantity used cannot be zero"))
        if self.unit_cost_snapshot < 0:
            raise ValidationError(_("Unit cost snapshot cannot be negative"))

    def save(self, *args, **kwargs):
        # Auto-calculate total_parts_cost
        self.total_parts_cost = self.qty_used * self.unit_cost_snapshot
        super().save(*args, **kwargs)

    def __str__(self):
        return f"WO {self.work_order.code} - {self.part.part_number} - Qty: {self.qty_used}"


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
    qty_delta = models.DecimalField(
        _("Quantity Delta"), 
        max_digits=10, 
        decimal_places=3,
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


