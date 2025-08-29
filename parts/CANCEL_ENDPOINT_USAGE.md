# Unified Cancel Availability Endpoint

The `/work-order-part-requests/{id}/cancel-availability` endpoint now handles all cancel scenarios through a single API endpoint.

## Endpoint
```
POST /api/parts/work-order-part-requests/{wopr_id}/cancel-availability
```

## Request Body
```json
{
  "cancel_type": "availability",  // Optional, defaults to "availability"
  "notes": "Optional cancellation notes"
}
```

## Cancel Types

### 1. Cancel Mechanic Request (`cancel_type: "request"`)
**Scenario**: Delete on request - Mechanic cancels their request
- Sets `qty_needed = 0`
- Sets `is_requested = False`
- Used when mechanic no longer needs the parts

```json
{
  "cancel_type": "request",
  "notes": "Mechanic no longer needs these parts"
}
```

### 2. Cancel Warehouse Availability (`cancel_type: "availability"`) - **DEFAULT**
**Scenario**: Delete on parts available - Warehouse cancels availability
- Sets `qty_available = 0`
- Sets `is_available = False`
- Releases inventory reservation
- Used when warehouse can no longer provide the parts

```json
{
  "cancel_type": "availability",
  "notes": "Parts no longer available in warehouse"
}
```

### 3. Cancel Parts Order (`cancel_type: "order"`)
**Scenario**: Order parts cancellation - Cancel when parts are ordered
- Sets `is_ordered = False`
- Used when external order is cancelled

```json
{
  "cancel_type": "order",
  "notes": "External order was cancelled"
}
```

### 4. Full Cancellation (`cancel_type: "full"`)
**Scenario**: Full cancellation - Reset everything to initial state
- Resets all quantities to 0
- Sets all flags to False
- Releases any reservations
- Complete reset of the request

```json
{
  "cancel_type": "full",
  "notes": "Complete cancellation of this request"
}
```

## Response
```json
{
  "success": true,
  "message": "Parts availability cancelled successfully",
  "wopr_id": "uuid-here",
  "cancel_type": "availability",
  "is_requested": false,
  "is_available": false,
  "is_ordered": false,
  "qty_needed": 0,
  "qty_available": 0
}
```

## Usage Examples

### Frontend Implementation
```javascript
// Cancel availability (default behavior)
const cancelAvailability = async (woprId, notes = '') => {
  return await fetch(`/api/parts/work-order-part-requests/${woprId}/cancel-availability`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes })
  });
};

// Cancel mechanic request
const cancelRequest = async (woprId, notes = '') => {
  return await fetch(`/api/parts/work-order-part-requests/${woprId}/cancel-availability`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      cancel_type: 'request',
      notes 
    })
  });
};

// Full cancellation
const fullCancel = async (woprId, notes = '') => {
  return await fetch(`/api/parts/work-order-part-requests/${woprId}/cancel-availability`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      cancel_type: 'full',
      notes 
    })
  });
};
```

## Migration Notes
- Existing calls without `cancel_type` will continue to work (defaults to "availability")
- All cancel scenarios now use the same endpoint
- Proper audit logging is maintained for all cancel types with correct action types
- Inventory reservations are properly released when applicable
- Fixed issue with duplicate audit logs and incorrect quantity tracking

## Recent Fixes
- **Fixed quantity tracking**: Corrected `qty_in_action` calculation to use actual quantities instead of boolean flags
- **Fixed audit logging**: Prevented duplicate audit logs by properly coordinating between service and model layers
- **Improved reliability**: Enhanced error handling and state management for all cancel scenarios
