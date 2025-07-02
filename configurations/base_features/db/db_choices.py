from django.db.models import TextChoices


class StatusChoices(TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"
    IN_PROGRESS = "in progress", "In Progress"

class TriggerTypeChoices(TextChoices):
    TIME = "time", "Time"
    METER_READING = "meter_reading", "Meter Reading"
    EVENT = "event", "Event"