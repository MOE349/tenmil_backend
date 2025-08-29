# Smart Cancel Availability Endpoint

The `/work-order-part-requests/{id}/cancel-availability` endpoint automatically detects what type of cancellation to perform based on the current state of the request.

## Endpoint
```
POST /api/parts/work-order-part-requests/{wopr_id}/cancel-availability
```

## Request Body
```json
{
  "notes": "Optional cancellation notes"
}
```

## Auto-Detection Logic

The endpoint automatically determines the appropriate cancellation action:

### 1. **Warehouse Availability Cancellation** (when `is_available = True`)
**Automatically triggered when**: Parts are currently marked as available
- Sets `is_requested = False` (mechanic no longer needs the parts)
- **Keeps `is_available = True`** (so warehouse keeper knows they had gathered parts)
- **Keeps `qty_available` and `inventory_batch`** (for warehouse visibility)
- Releases inventory reservation (parts returned to available stock)

### 2. **Mechanic Request Cancellation** (when `is_available = False` and `is_requested = True`)
**Automatically triggered when**: Request exists but no availability confirmed yet
- Sets `qty_needed = 0`
- Sets `is_requested = False`

### 3. **Validation Errors**
**Cannot cancel when**:
- `is_ordered = True` → Returns error: "Cannot cancel request: parts have already been ordered"
- `is_delivered = True` → Returns error: "Cannot cancel request: parts have already been delivered"
- Neither `is_available` nor `is_requested` is true → Returns error: "Cannot cancel: request is not in a cancellable state"

## Response
```json
{
  "success": true,
  "message": "Parts availability cancelled successfully",
  "wopr_id": "uuid-here",
  "cancel_type": "availability",  // Auto-detected type
  "is_requested": false,          // Mechanic no longer needs parts
  "is_available": true,           // Kept true for warehouse visibility
  "is_ordered": false,
  "qty_needed": 5,                // Original quantity preserved
  "qty_available": 5              // Quantity info preserved for warehouse
}
```

## Usage Examples

### Frontend Implementation
```javascript
// Smart cancellation - automatically detects what to cancel
const cancelRequest = async (woprId, notes = '') => {
  return await fetch(`/api/parts/work-order-part-requests/${woprId}/cancel-availability`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes })
  });
};

// Usage examples:
// If WOPR has is_available=true → Cancels availability (keeps availability info for warehouse)
// If WOPR has is_requested=true but is_available=false → Cancels mechanic request
// If WOPR has is_ordered=true → Returns validation error
```

## Complete Cancellation Workflow

### **Step 1: Mechanic Cancels Request**
```
POST /api/parts/work-order-part-requests/{wopr_id}/cancel-availability
Body: { "notes": "No longer needed" }

Result:
├── is_requested: False  (mechanic doesn't need parts)
├── is_available: True   (warehouse keeper can see they gathered parts)
├── qty_available: 5     (quantity info preserved)
└── inventory_batch: "BATCH-123"  (batch info preserved)
```

### **Step 2: Warehouse Keeper Acknowledges Cancellation**
```
POST /api/parts/work-order-part-requests/{wopr_id}/deliver
Body: { "notes": "Acknowledged cancellation" }

Result:
├── is_requested: False
├── is_available: False  (cleaned up after acknowledgment)
├── qty_needed: 0        (cleaned up)
├── qty_available: 0     (cleaned up)
├── qty_delivered: 0     (preserved - not affected)
└── qty_used: 0          (preserved - not affected)
```

### **Benefits of Two-Step Process**
- **Visibility**: Warehouse keeper knows what parts were prepared but cancelled
- **Acknowledgment**: Explicit confirmation that warehouse understands the cancellation
- **Clean State**: Final state is clean with no leftover availability data
- **Audit Trail**: Complete record of cancellation and acknowledgment

## Migration Notes
- Existing calls without `cancel_type` will continue to work (defaults to "availability")
- All cancel scenarios now use the same endpoint
- Proper audit logging is maintained for all cancel types with correct action types
- Inventory reservations are properly released when applicable
- Fixed issue with duplicate audit logs and incorrect quantity tracking

## Recent Improvements
- **Smart Auto-Detection**: Automatically detects cancel type based on current WOPR state
- **Simplified API**: Removed manual `cancel_type` parameter - no longer needed
- **Enhanced Validation**: Prevents cancellation of ordered/delivered requests
- **Code Refactoring**: Extracted reusable helper functions for WOPR lookup and state validation
- **Enhanced Delivery Logic**: Added cancellation acknowledgment support in deliver_parts endpoint
- **Updated Pending Requests**: Modified pending requests filter to include cancelled requests awaiting acknowledgment
- **Fixed quantity tracking**: Corrected `qty_in_action` calculation to use actual quantities
- **Fixed audit logging**: Prevented duplicate audit logs by coordinating service and model layers
