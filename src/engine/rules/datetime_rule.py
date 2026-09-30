import re
from typing import Tuple

def heal_iso_date(xml_payload: str) -> Tuple[str, bool]:
    """
    Finds non-standard date formats (e.g., DD/MM/YYYY or DD-MM-YYYY) inside XML tags
    and normalizes them to CargoWise standard ISO 8601 format (YYYY-MM-DD).
    """
    healed = False

    # Regex pattern to identify dates in format DD/MM/YYYY or DD-MM-YYYY within XML tags
    # Example matches: <EstimatedArrival>17/09/2026</EstimatedArrival>
    date_pattern = r'(<([a-zA-Z0-9_]+)>)(\d{2})[/.-](\d{2})[/.-](\d{4})(</\2>)'

    def replace_date(match):
        nonlocal healed
        open_tag = match.group(1)
        day = match.group(3)
        month = match.group(4)
        year = match.group(5)
        close_tag = match.group(6)

        # Basic calendar validation for day and month ranges
        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
            healed = True
            return f"{open_tag}{year}-{month}-{day}{close_tag}"
        
        return match.group(0)

    # Perform regex replacement on the XML string
    healed_xml = re.sub(date_pattern, replace_date, xml_payload)
    
    return healed_xml, healed