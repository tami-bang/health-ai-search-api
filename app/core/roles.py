# app/core/roles.py

from enum import Enum  # 용도: 역할 정의


class UserRole(str, Enum):
    SUPERUSER = "SUPERUSER"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    USER = "USER"