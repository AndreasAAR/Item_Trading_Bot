from typing import Dict, Any, List

def format_blocket_description(item_data: Dict[str, Any]) -> str:
    """Formats a clean and informative description for Blocket.se."""
    original_desc = item_data.get("description", "").strip()
    attributes: Dict[str, str] = item_data.get("attributes", {})

    lines: List[str] = []

    if original_desc:
        lines.append(original_desc)
        lines.append("")

    # Append specifications / attributes if present
    spec_lines = []
    for k, v in attributes.items():
        spec_lines.append(f"• {k}: {v}")

    if spec_lines:
        lines.append("Detaljer:")
        lines.extend(spec_lines)
        lines.append("")

    # Pickup & delivery notes
    pickup_note = "Finns för avhämtning i Stockholm (Odenplan) eller kan skickas med Blocketpaket/frakt."
    lines.append(pickup_note)

    return "\n".join(lines).strip()

def format_blocket_title(title: str, max_length: int = 50) -> str:
    """Formats and shortens title if necessary for Blocket limits."""
    clean_title = " ".join(title.split())
    if len(clean_title) <= max_length:
        return clean_title
    return clean_title[:max_length - 3] + "..."
