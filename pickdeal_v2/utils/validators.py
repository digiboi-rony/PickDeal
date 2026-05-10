"""utils/validators.py — input validation helpers"""
import re


def is_valid_phone(phone: str) -> bool:
    """Bangladesh mobile number: 01XXXXXXXXX"""
    p = phone.strip().replace(" ", "").replace("-", "")
    return bool(re.fullmatch(r"01[3-9]\d{8}", p))


def is_valid_name(name: str) -> bool:
    return 3 <= len(name.strip()) <= 60


def is_valid_address(addr: str) -> bool:
    return len(addr.strip()) >= 10


def clean_phone(phone: str) -> str:
    return phone.strip().replace(" ", "").replace("-", "")
