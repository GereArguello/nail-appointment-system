from enum import StrEnum


class RoleEnum(StrEnum):
    ADMIN = "admin"
    CUSTOMER = "customer"


class StatusEnum(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class AppointmentStatusEnum(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED_BY_CLIENT = "cancelled_by_client"
    CANCELLED_BY_ADMIN = "cancelled_by_admin"
    NO_SHOW = "no_show"


class TimezoneEnum(StrEnum):
    BUENOS_AIRES = "America/Argentina/Buenos_Aires"
    ACAPULCO = "America/Mexico_City"
