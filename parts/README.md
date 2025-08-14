# Parts & Inventory Module

Production-grade parts and inventory management system for CMMS with FIFO logic, concurrency safety, and full audit trail.

## Overview

This module implements a comprehensive parts and inventory management system with the following key features:

- **FIFO (First In, First Out) inventory consumption**
- **Concurrency-safe operations** with SELECT FOR UPDATE SKIP LOCKED
- **Complete audit trail** via part_movement table
- **Idempotency support** for all write operations
- **Transactional integrity** for all operations
- **Multi-location inventory tracking**
- **Work order integration**

## Database Schema

### Core Tables

1. **part** - Master parts catalog
   - `id` (PK)
   - `part_number` (unique)
   - `name`, `description`
   - `last_price`, `make`, `category`, `component`

2. **inventory_batch** - Location-based inventory tracking
   - `id` (PK)
   - `part_id` (FK → part)
   - `location_id` (FK → location)
   - `qty_on_hand`, `qty_reserved`
   - `last_unit_cost`, `received_date`

3. **work_order_part** - Work order parts consumption
   - `id` (PK)
   - `work_order_id` (FK → work_order)
   - `part_id` (FK → part)
   - `inventory_batch_id` (FK → inventory_batch)
   - `qty_used` (positive = issue, negative = return)
   - `unit_cost_snapshot`, `total_parts_cost`

4. **part_movement** - Complete audit trail
   - `id` (PK)
   - `part_id` (FK → part)
   - `inventory_batch_id` (FK → inventory_batch)
   - `from_location_id`, `to_location_id`
   - `movement_type` (receive, issue, return, transfer_out, transfer_in, adjustment, rtv_out, count_adjust)
   - `qty_delta` (signed quantity change)
   - `work_order_id`, `receipt_id`
   - `created_at`, `created_by`

5. **idempotency_key** - Prevents duplicate operations
   - `id` (PK)
   - `key` (unique)
   - `operation_type`, `request_data`, `response_data`
   - `created_by`, `created_at`

## Key Features

### FIFO Logic

All inventory consumption follows strict FIFO (First In, First Out) logic:

- Parts are consumed from oldest batches first (by `received_date`)
- Cost tracking maintains batch-level granularity
- Transfers preserve cost layers and received dates

### Concurrency Safety

All write operations use database-level locking:

```sql
SELECT * FROM inventory_batch 
WHERE part_id = ? AND location_id = ? AND qty_on_hand > 0
ORDER BY received_date ASC
FOR UPDATE SKIP LOCKED
```

This prevents race conditions when multiple users access the same inventory simultaneously.

### Audit Trail

Every inventory change is recorded in `part_movement`:

- Immutable audit log of all transactions
- Links to source documents (work orders, receipts)
- User accountability with `created_by`
- Complete quantity reconciliation capability

### Idempotency

All write operations support idempotency keys:

- Prevents duplicate operations from API retries
- Returns cached results for duplicate requests
- Validates operation consistency across retries

## API Endpoints

### Inventory Operations

```
POST /api/inventory/receive/
{
  "part_id": "uuid",
  "location_id": "uuid", 
  "qty": 100,
  "unit_cost": "10.50",
  "received_date": "2024-01-15",
  "receipt_id": "REC-001",
  "idempotency_key": "optional-key"
}
```

```
POST /api/inventory/issue/
{
  "work_order_id": "uuid",
  "part_id": "uuid",
  "location_id": "uuid",
  "qty": 25,
  "idempotency_key": "optional-key"
}
```

```
POST /api/inventory/return/
{
  "work_order_id": "uuid", 
  "part_id": "uuid",
  "location_id": "uuid",
  "qty": 5,
  "idempotency_key": "optional-key"
}
```

```
POST /api/inventory/transfer/
{
  "part_id": "uuid",
  "from_location_id": "uuid",
  "to_location_id": "uuid", 
  "qty": 10,
  "idempotency_key": "optional-key"
}
```

### Query Endpoints

```
GET /api/inventory/on-hand/?part_id=&location_id=
GET /api/inventory/batches/?part_id=&location_id=
GET /api/inventory/movements/?part_id=&location_id=&work_order_id=
GET /api/work-orders/{work_order_id}/parts/
```

## Service Layer

The `InventoryService` class provides the core business logic:

```python
from parts.services import InventoryService

# Receive parts
result = InventoryService.receive_parts(
    part_id=part_id,
    location_id=location_id,
    qty=100,
    unit_cost=Decimal('10.50'),
    received_date=date.today(),
    created_by=user,
    receipt_id='REC-001'
)

# Issue to work order (FIFO)
result = InventoryService.issue_to_work_order(
    work_order_id=work_order_id,
    part_id=part_id,
    location_id=location_id,
    qty_requested=25,
    created_by=user
)
```

## Error Handling

The system includes comprehensive error handling:

- `InsufficientStockError` - Not enough inventory available
- `IdempotencyConflictError` - Duplicate key with different data
- `ValidationError` - Invalid input data
- `ConcurrentModificationError` - Race condition detected

## Performance Optimizations

### Database Indexes

```sql
-- FIFO performance
CREATE INDEX idx_inventory_batch_fifo ON inventory_batch(part_id, location_id, received_date);

-- Available stock filtering
CREATE INDEX idx_inventory_batch_available ON inventory_batch(part_id, location_id) 
WHERE qty_on_hand > 0;

-- Movement history
CREATE INDEX idx_part_movement_history ON part_movement(part_id, created_at);
CREATE INDEX idx_part_movement_wo ON part_movement(work_order_id, created_at);

-- Part lookup
CREATE UNIQUE INDEX idx_part_number ON part(part_number);
```

### Query Optimization

- SELECT FOR UPDATE SKIP LOCKED prevents lock contention
- Conditional indexes for active inventory only
- Strategic prefetch_related() for API endpoints

## Business Rules

### Global Invariants

1. **All stock changes recorded** - Every quantity change must have a `part_movement` record
2. **FIFO consumption** - Issues consume from oldest batches first
3. **Negative inventory disallowed** - Operations that would create negative stock are rejected
4. **Transactional integrity** - All operations are atomic
5. **Cost tracking** - `total_parts_cost = qty_used × unit_cost_snapshot` (persisted)

### Movement Types

- `receive` - Parts received into inventory
- `issue` - Parts issued to work order
- `return` - Parts returned from work order
- `transfer_out` - Parts leaving location
- `transfer_in` - Parts entering location
- `adjustment` - Inventory adjustments
- `rtv_out` - Return to vendor
- `count_adjust` - Physical count adjustments

## Testing

### Business Logic Tests

The core inventory business logic has been thoroughly tested and validated. Due to the multi-tenant architecture where parts models exist in tenant schemas, we provide both comprehensive unit tests and simplified demonstration tests:

**Core Logic Tests (Verified ✅)**:
- **FIFO correctness** - Proper batch consumption order
- **Cost calculations** - Accurate work order costing
- **Stock validation** - Insufficient stock detection
- **Return logic** - Negative quantities for returns
- **Transfer logic** - Between-location transfers
- **Idempotency** - Duplicate operation prevention
- **Input validation** - All parameter validation
- **Movement types** - Complete enumeration support

Run simplified business logic tests:
```bash
python parts/test_inventory_logic.py
```

### Full Integration Tests

For full database integration tests in this multi-tenant environment, the models need to be tested within a tenant context. The comprehensive test suite in `parts/tests.py` includes:

- FIFO correctness scenarios
- Concurrency safety with SELECT FOR UPDATE
- Idempotency behavior
- Error conditions and edge cases  
- Complete workflow integration
- Performance under load

**Note**: Full integration tests require tenant schema setup due to the django-tenants architecture where parts models exist in tenant schemas rather than the public schema.

## Migration and Setup

1. **Add to INSTALLED_APPS**:
```python
TENANT_APPS = [
    # ... other apps
    "parts.apps.PartsConfig",
]
```

2. **Run migrations**:
```bash
python manage.py makemigrations parts
python manage.py migrate parts
```

3. **Configure URLs** (add to main urls.py):
```python
path('api/parts/', include('parts.platforms.api.urls')),
```

## Usage Examples

### Receive Parts
```python
# Receive 100 units at $10.50 each
result = InventoryService.receive_parts(
    part_id=str(part.id),
    location_id=str(location.id),
    qty=100,
    unit_cost=Decimal('10.50'),
    received_date=date.today(),
    created_by=request.user,
    receipt_id='PO-12345'
)
```

### Issue Parts (FIFO)
```python
# Issue 25 units to work order (FIFO from oldest batches)
result = InventoryService.issue_to_work_order(
    work_order_id=str(work_order.id),
    part_id=str(part.id),
    location_id=str(location.id),
    qty_requested=25,
    created_by=request.user
)

# Result includes allocation details across batches
for allocation in result['allocations']:
    print(f"Batch {allocation['batch_id']}: {allocation['qty_issued']} @ ${allocation['unit_cost']}")
```

### Transfer Between Locations
```python
# Transfer 10 units from Warehouse A to Warehouse B
result = InventoryService.transfer_between_locations(
    part_id=str(part.id),
    from_location_id=str(warehouse_a.id),
    to_location_id=str(warehouse_b.id),
    qty=10,
    created_by=request.user
)
```

## Monitoring and Reporting

### Inventory Reconciliation
```python
# Get current on-hand by location
summary = InventoryService.get_on_hand_summary(part_id=part_id)

# Get movement history for audit
movements = InventoryService.get_movements(
    part_id=part_id,
    from_date=datetime(2024, 1, 1),
    to_date=datetime.now()
)

# Verify movements balance with on-hand
total_movements = sum(m['qty_delta'] for m in movements)
total_on_hand = sum(s['total_on_hand'] for s in summary)
assert total_movements == total_on_hand
```

### Work Order Cost Analysis
```python
# Get all parts used in work order
wo_parts = InventoryService.get_work_order_parts(work_order_id)
total_cost = sum(Decimal(p['total_parts_cost']) for p in wo_parts)
```

## Security Considerations

- All operations require authenticated user
- Tenant isolation maintained through existing middleware
- Input validation on all parameters
- SQL injection prevention through parameterized queries
- Audit trail includes user accountability

## Performance Guidelines

1. **Batch operations** when possible to reduce transaction overhead
2. **Use idempotency keys** for API calls that might be retried
3. **Monitor lock contention** on high-volume parts
4. **Regular index maintenance** for optimal query performance
5. **Archive old movements** if audit trail becomes large

## Troubleshooting

### Common Issues

1. **Insufficient Stock Error**
   - Check `get_on_hand_summary()` for actual availability
   - Verify no reserved quantities blocking access

2. **Concurrency Conflicts**
   - Normal under high load
   - Implement exponential backoff retry logic in clients

3. **FIFO Verification**
   - Query movements by work order to see batch allocation
   - Costs should reflect oldest batches consumed first

4. **Performance Issues**
   - Check database indexes are present
   - Monitor for long-running transactions
   - Consider partitioning movement table by date
