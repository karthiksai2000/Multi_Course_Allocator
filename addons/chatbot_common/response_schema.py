from typing import Any


def text_response(title: str, message: str, guidelines: list[str] | None = None, source_module: str = "unknown") -> dict[str, Any]:
    return {
        "type": "text",
        "title": title,
        "message": message,
        "guidelines": guidelines or [],
        "sourceModule": source_module,
    }


def table_response(title: str, rows: list[dict[str, Any]], message: str = "", source_module: str = "unknown") -> dict[str, Any]:
    return {
        "type": "table",
        "title": title,
        "message": message,
        "rows": rows,
        "sourceModule": source_module,
    }


def error_response(message: str, source_module: str = "unknown") -> dict[str, Any]:
    return {
        "type": "error",
        "title": "Unable to process question",
        "message": message,
        "sourceModule": source_module,
    }
