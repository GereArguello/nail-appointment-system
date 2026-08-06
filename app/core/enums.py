from enum import Enum


class RoleEnum(Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"


class StatusEnum(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
