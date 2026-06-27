from enum import Enum


class DataTier(str, Enum):
    TIER1_PLANET = "tier1_planet"
    TIER2_SEN2SR = "tier2_sen2sr"
    TIER3_SAR = "tier3_sar"


class RiskTier(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    ELEVATED = "elevated"
    HIGH = "high"
    INSUFFICIENT_DATA = "insufficient_data"


class FieldStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class UserRole(str, Enum):
    ADMIN = "admin"
    LOAN_OFFICER = "loan_officer"
