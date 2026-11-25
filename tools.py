from datetime import datetime
from zoneinfo import ZoneInfo
from langchain_core.tools import tool


@tool
def get_current_time(timezone: str = "Asia/Kolkata") -> str:
    """Get the current date and time for an IANA timezone, e.g. 'Asia/Kolkata' or 'UTC'."""
    try:
        now = datetime.now(ZoneInfo(timezone))
    except Exception:
        return f"Unknown timezone: {timezone}"
    return now.strftime("%A, %d %B %Y, %I:%M:%S %p %Z")


@tool
def calculate(expression: str) -> str:
    """Evaluate a basic math expression, e.g. '(12 + 8) * 3 / 2'."""
    allowed = set("0123456789+-*/(). %")
    if not set(expression) <= allowed:
        return "Error: only numbers and + - * / % ( ) are allowed."
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"