# Parts & Inventory Module

Production-grade parts & inventory management system for CMMS applications with FIFO inventory control, comprehensive audit trails, and transactional integrity.

## Overview

This module implements a complete parts and inventory management system with the following key features:

- **FIFO Inventory Control**: First-In, First-Out inventory consumption for accurate cost tracking
- **Transactional Integrity**: All operations are atomic with proper database locking
- **Comprehensive Audit Trail**: Complete movement history via immutable `part_movement` ledger
- **Multi-Location Support**: Track inventory across multiple locations with transfers
- **Work Order Integration**: Direct integration with work order parts consumption
- **Idempotency Support**: Prevent duplicate operations with idempotency keys
- **Concurrent Operation Safety**: Proper locking prevents race conditions

## Architecture

### Core Models

#### 1. Part (Master Catalog)
```python
- part_number (unique)    # Primary identifier
- name                   # Descriptive name
- description           # Optional details
- last_price            # Most recent purchase price
- make                  # Manufacturer
- category              # Classification
- component             # Component type
```

#### 2. InventoryBatch (Location-Based Inventory)
```python
- part_id               # FK to Part
- location_id           # FK to Location
- qty_on_hand           # Available quantity
- qty_reserved          # Reserved quantity
- qty_received          # Original batch quantity
- last_unit_cost        # Cost for this batch
- received_date         # Date received (for FIFO)
```

#### 3. WorkOrderPart (Work Order Integration)
```python
- work_order_id         # FK to WorkOrder
- part_id               # FK to Part
- inventory_batch_id    # FK to InventoryBatch
- qty_used              # Quantity used (+issue, -return)
- unit_cost_snapshot    # Cost at time of transaction
- total_parts_cost      # qty_used × unit_cost_snapshot
```

#### 4. PartMovement (Audit Trail)
```python
- part_id               # FK to Part
- inventory_batch_id    # FK to InventoryBatch (nullable)
- from_location_id      # Source location (nullable)
- to_location_id        # Destination location (nullable)
- movement_type         # ENUM: receive, issue, return, transfer_out, transfer_in, adjustment, rtv_out, count_adjust
- qty_delta             # Signed quantity change
- work_order_id         # FK to WorkOrder (nullable)
- receipt_id            # External reference (nullable)
- created_by            # FK to User
- created_at            # Timestamp
```

### Business Rules & Invariants

1. **Single Source of Truth**: All stock changes must be recorded in `part_movement`
2. **FIFO Consumption**: Issues consume from oldest inventory batches first (by `received_date`)
3. **Immutable Audit Trail**: Part movements cannot be modified after creation
4. **Transactional Operations**: All multi-step operations are atomic
5. **No Negative Inventory**: Inventory quantities cannot go below zero
6. **Cost Preservation**: Transfer operations preserve cost layers and dates

## Service Layer

### Core Service: `InventoryService`

The `InventoryService` class provides all business logic operations:

```python
from parts.services import inventory_service
```

### Operations

#### 1. Receive Parts
```python
result = inventory_service.receive_parts(
    part_id="uuid",
    location_id="uuid", 
    qty=Decimal("10.5"),
    unit_cost=Decimal("25.50"),
    received_date=datetime.now(),  # Optional
    receipt_id="REC001",           # Optional
    created_by=user,               # Optional
    idempotency_key="key123"       # Optional
)
```

**Creates:**
- New `InventoryBatch` record
- `PartMovement` with type `receive`
- Updates `Part.last_price`

#### 2. Issue to Work Order (FIFO)
```python
result = inventory_service.issue_to_work_order(
    work_order_id="uuid",
    part_id="uuid",
    location_id="uuid",
    qty_requested=Decimal("5.0"),
    created_by=user,
    idempotency_key="key456"  # Optional
)
```

**FIFO Logic:**
1. Queries batches ordered by `received_date` ASC
2. Uses `SELECT FOR UPDATE SKIP LOCKED` for concurrency safety
3. Consumes quantities from oldest batches first
4. Creates `WorkOrderPart` and `PartMovement` records for each batch consumed

#### 3. Return from Work Order
```python
result = inventory_service.return_from_work_order(
    work_order_id="uuid",
    part_id="uuid", 
    location_id="uuid",
    qty_to_return=Decimal("2.0"),
    created_by=user,
    idempotency_key="key789"  # Optional
)
```

**Return Policy:**
- Returns to oldest available batches (FIFO return)
- Creates negative `WorkOrderPart` records for audit trail
- Creates `PartMovement` with type `return`

#### 4. Transfer Between Locations
```python
result = inventory_service.transfer_between_locations(
    part_id="uuid",
    from_location_id="uuid",
    to_location_id="uuid", 
    qty=Decimal("8.0"),
    created_by=user,
    idempotency_key="key012"  # Optional
)
```

**Transfer Logic:**
1. Consumes from source location using FIFO
2. Creates `transfer_out` movements
3. Creates destination batches preserving cost/date layers
4. Creates `transfer_in` movements

### Query Operations

#### On-Hand Quantities
```python
# All parts and locations
on_hand = inventory_service.get_on_hand_by_part_location()

# Specific part
on_hand = inventory_service.get_on_hand_by_part_location(part_id="uuid")

# Specific location  
on_hand = inventory_service.get_on_hand_by_part_location(location_id="uuid")
```

#### Inventory Batches
```python
batches = inventory_service.get_batches(
    part_id="uuid",     # Optional
    location_id="uuid"  # Optional
)
```

#### Movement History
```python
movements = inventory_service.get_movements(
    part_id="uuid",        # Optional
    location_id="uuid",    # Optional  
    work_order_id="uuid",  # Optional
    from_date=datetime,    # Optional
    to_date=datetime,      # Optional
    limit=100              # Optional (default 100)
)
```

#### Work Order Parts Summary
```python
summary = inventory_service.get_work_order_parts("work_order_uuid")
# Returns: {'work_order_id': str, 'parts': list, 'total_parts_cost': Decimal}
```

## API Endpoints

### Base URL: `/v1/api/parts/`

#### Standard CRUD Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/parts/` | List/Create parts |
| GET/PUT/DELETE | `/parts/{id}/` | Retrieve/Update/Delete part |
| GET/POST | `/inventory-batches/` | List/Create inventory batches |
| GET/PUT/DELETE | `/inventory-batches/{id}/` | Retrieve/Update/Delete batch |
| GET/POST | `/work-order-parts/` | List/Create work order parts |
| GET/PUT/DELETE | `/work-order-parts/{id}/` | Retrieve/Update/Delete WO part |
| GET | `/movements/` | List part movements (read-only) |
| GET | `/movements/{id}/` | Retrieve movement (read-only) |

#### Inventory Operations

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/receive/` | Receive parts | `{"part_id": "uuid", "location_id": "uuid", "qty": "10.5", "unit_cost": "25.50", "received_date": "ISO", "receipt_id": "string", "idempotency_key": "string"}` |
| POST | `/issue/` | Issue to work order | `{"work_order_id": "uuid", "part_id": "uuid", "location_id": "uuid", "qty": "5.0", "idempotency_key": "string"}` |
| POST | `/return/` | Return from work order | `{"work_order_id": "uuid", "part_id": "uuid", "location_id": "uuid", "qty": "2.0", "idempotency_key": "string"}` |
| POST | `/transfer/` | Transfer between locations | `{"part_id": "uuid", "from_location_id": "uuid", "to_location_id": "uuid", "qty": "8.0", "idempotency_key": "string"}` |

#### Query Operations

| Method | Endpoint | Description | Query Parameters |
|--------|----------|-------------|------------------|
| GET | `/on-hand/` | Get on-hand quantities | `part_id` or `part`, `location_id` or `location` |
| GET | `/batches/` | Get inventory batches | `part_id` or `part`, `location_id` or `location` |
| GET | `/movements-query/` | Get movement history | `part_id` or `part`, `location_id` or `location`, `work_order_id` or `work_order`, `from_date`, `to_date`, `limit` |
| GET | `/locations-on-hand/` | Get all locations with on-hand for part | `part_id` or `part` (required) |
| GET | `/work-orders/{id}/parts/` | Get work order parts summary | - |

### Example API Usage

#### Receive Parts
```bash
curl -X POST /v1/api/parts/receive/ \
  -H "Content-Type: application/json" \
  -d '{
    "part_id": "123e4567-e89b-12d3-a456-426614174000",
    "location_id": "123e4567-e89b-12d3-a456-426614174001", 
    "qty": "100.0",
    "unit_cost": "15.75",
    "receipt_id": "PO-2024-001",
    "idempotency_key": "receive_2024_001"
  }'
```

#### Issue Parts to Work Order
```bash
curl -X POST /v1/api/parts/issue/ \
  -H "Content-Type: application/json" \
  -d '{
    "work_order_id": "123e4567-e89b-12d3-a456-426614174002",
    "part_id": "123e4567-e89b-12d3-a456-426614174000",
    "location_id": "123e4567-e89b-12d3-a456-426614174001",
    "qty": "5.0"
  }'
```

#### Get Locations On-Hand
```bash
# Using part_id parameter
curl -X GET "/v1/api/parts/locations-on-hand/?part_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer your-jwt-token"

# Using part parameter (alternative format)
curl -X GET "/v1/api/parts/locations-on-hand/?part=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer your-jwt-token"
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "site": "MAIN",
      "location": "Warehouse A",
      "QTY_on_hand": "150.000"
    },
    {
      "site": "MAIN", 
      "location": "Warehouse B",
      "QTY_on_hand": "0.000"
    },
    {
      "site": "BRANCH",
      "location": "Storage Room",
      "QTY_on_hand": "25.500"
    }
  ],
  "errors": null,
  "status_code": 200
}
```

## Error Handling

### Custom Exceptions

#### `InsufficientStockError`
- **When**: Requested quantity exceeds available stock
- **Properties**: `part_number`, `requested`, `available`
- **HTTP Status**: 400 Bad Request

#### `InvalidOperationError`  
- **When**: Operation violates business rules
- **Examples**: Invalid part/location IDs, same source/destination in transfer
- **HTTP Status**: 400 Bad Request

### Error Response Format
```json
{
  "success": false,
  "errors": ["Insufficient stock for P001: requested 10, available 5"],
  "data": null,
  "status_code": 400
}
```

### Success Response Format
```json
{
  "success": true,
  "data": {
    "operation": "issue",
    "message": "Issued 5.0 of P001 to WO WO_123",
    "allocations": [
      {
        "batch_id": "uuid",
        "qty_allocated": "5.0", 
        "unit_cost": "15.75",
        "total_cost": "78.75"
      }
    ],
    "movements": ["movement_uuid"],
    "work_order_parts": ["wo_part_uuid"]
  },
  "errors": null,
  "status_code": 200
}
```

## Concurrency & Performance

### Locking Strategy
- Uses `SELECT FOR UPDATE SKIP LOCKED` for FIFO batch allocation
- Prevents deadlocks with consistent lock ordering
- Fails fast if batches are locked by other transactions

### Database Indexes
```sql
-- FIFO performance
CREATE INDEX ON inventory_batch(part_id, location_id, received_date);

-- Available stock queries  
CREATE INDEX ON inventory_batch(part_id, location_id) WHERE qty_on_hand > 0;

-- Movement history
CREATE INDEX ON part_movement(part_id, created_at);
CREATE INDEX ON part_movement(work_order_id, created_at);
CREATE INDEX ON part_movement(movement_type, created_at);
```

### Performance Considerations
1. **Batch Consolidation**: Consider consolidating small batches periodically
2. **Archive Strategy**: Archive old movements to separate tables
3. **Batch Size Limits**: Monitor transaction sizes for large operations
4. **Connection Pooling**: Use appropriate database connection pooling

## Testing

### Test Coverage
The module includes comprehensive tests covering:

- **FIFO Correctness**: Proper oldest-first consumption
- **Concurrent Operations**: Race condition prevention  
- **Return Scenarios**: Return then re-issue reconciliation
- **Transfer Operations**: Multi-location transfers with cost preservation
- **Error Conditions**: Insufficient stock, validation failures
- **Idempotency**: Duplicate request handling
- **Data Integrity**: Model validation and constraints

### Running Tests
```bash
# All tests
python manage.py test parts

# Specific test classes
python manage.py test parts.tests.FIFOTests
python manage.py test parts.tests.ConcurrencyTests
```

### Test Database Setup
Tests use Django's test database with proper transaction isolation:
- `TestCase` for simple tests with transaction rollback
- `TransactionTestCase` for concurrency tests requiring real commits

## Migration Guide

### Initial Setup
1. **Add to TENANT_APPS**: Already configured in `installed_apps.py`
2. **Run Migrations**: `python manage.py migrate parts`
3. **Create Admin User**: Access via `/admin/` for manual data entry

### Data Migration
If migrating from existing inventory system:

```python
# Example migration script
from parts.services import inventory_service
from decimal import Decimal

def migrate_existing_inventory():
    for old_item in OldInventoryModel.objects.all():
        # Create part if not exists
        part, created = Part.objects.get_or_create(
            part_number=old_item.part_code,
            defaults={
                'name': old_item.description,
                'last_price': old_item.cost
            }
        )
        
        # Receive into new system
        if old_item.quantity > 0:
            inventory_service.receive_parts(
                part_id=str(part.id),
                location_id=str(default_location.id),
                qty=Decimal(str(old_item.quantity)),
                unit_cost=Decimal(str(old_item.cost)),
                received_date=old_item.created_date,
                receipt_id=f"MIGRATION_{old_item.id}"
            )
```

## Monitoring & Maintenance

### Key Metrics to Monitor
1. **Inventory Accuracy**: Compare physical counts to system quantities
2. **Movement Volume**: Track transaction rates for capacity planning
3. **FIFO Compliance**: Verify oldest batches are consumed first
4. **Lock Contention**: Monitor database lock waits and deadlocks
5. **Error Rates**: Track insufficient stock and validation failures

### Maintenance Tasks
1. **Periodic Reconciliation**: Compare system vs physical inventory
2. **Batch Cleanup**: Archive fully consumed batches
3. **Movement Archival**: Move old movements to archive tables
4. **Index Maintenance**: Monitor and rebuild indexes as needed

### Health Checks
```python
# Example health check
def inventory_health_check():
    # Check for negative inventory
    negative_batches = InventoryBatch.objects.filter(qty_on_hand__lt=0)
    
    # Check for orphaned movements
    orphaned_movements = PartMovement.objects.filter(
        inventory_batch__isnull=True,
        movement_type__in=['issue', 'return']
    )
    
    # Check FIFO compliance (simplified)
    violations = check_fifo_violations()
    
    return {
        'negative_inventory': negative_batches.count(),
        'orphaned_movements': orphaned_movements.count(), 
        'fifo_violations': len(violations)
    }
```

## Troubleshooting

### Common Issues

#### 1. Insufficient Stock Errors
**Symptoms**: API returns 400 with insufficient stock message
**Causes**: 
- Concurrent operations consuming same inventory
- Inventory not properly received
- Reserved quantities not accounted for

**Resolution**:
```python
# Check actual availability
batches = InventoryBatch.objects.filter(
    part_id=part_id, 
    location_id=location_id,
    qty_on_hand__gt=0
)
total_available = sum(b.qty_on_hand for b in batches)
```

#### 2. FIFO Order Issues
**Symptoms**: Newer batches consumed before older ones
**Causes**: 
- Incorrect `received_date` values
- Database clock skew
- Timezone issues

**Resolution**:
```python
# Verify batch order
batches = InventoryBatch.objects.filter(
    part_id=part_id,
    location_id=location_id
).order_by('received_date')

for batch in batches:
    print(f"Batch {batch.id}: {batch.received_date} - Qty: {batch.qty_on_hand}")
```

#### 3. Movement Audit Discrepancies  
**Symptoms**: Batch quantities don't match movement history
**Causes**:
- Direct database modifications
- Failed transaction rollbacks
- Data corruption

**Resolution**:
```python
# Reconcile movements vs batch quantities
def reconcile_movements(part_id, location_id):
    movements = PartMovement.objects.filter(
        part_id=part_id,
        to_location_id=location_id  # or from_location_id
    ).aggregate(total=Sum('qty_delta'))
    
    batches = InventoryBatch.objects.filter(
        part_id=part_id,
        location_id=location_id
    ).aggregate(total=Sum('qty_on_hand'))
    
    print(f"Movement total: {movements['total']}")
    print(f"Batch total: {batches['total']}")
```

### Debug Mode
Enable additional logging in development:
```python
# settings.py
LOGGING = {
    'loggers': {
        'parts.services': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    }
}
```

## Security Considerations

### Access Control
- All API endpoints require authentication
- Use tenant-based access control for multi-tenant deployments
- Implement role-based permissions for inventory operations

### Audit Trail
- All movements are logged with user attribution
- Movements are immutable after creation
- Full audit trail available for compliance requirements

### Data Validation
- Input validation at serializer level
- Business rule validation at service level
- Database constraints for data integrity

---

## Support

For issues or questions:
1. Check the test suite for usage examples
2. Review the service layer code for implementation details
3. Consult the API documentation for endpoint specifications
4. Monitor application logs for error details

**Version**: 1.0.0
**Last Updated**: 2025-01-08
**Compatibility**: Django 4.x+, PostgreSQL 12+
