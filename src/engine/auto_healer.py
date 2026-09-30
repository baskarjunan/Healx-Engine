from src.rules.unlocode_rule import heal_unlocode
from src.rules.datetime_rule import heal_iso_date

class AutoHealerEngine:
    def __init__(self):
        self.fine_per_healing = 150.0

    def process_payload(self, xml_payload: str) -> dict:
        current_xml = xml_payload
        total_heals = 0
        
        # Rule 1: UN/LOCODE Healing
        current_xml, unlocode_healed = heal_unlocode(current_xml)
        if unlocode_healed:
            total_heals += 1
            
        # Rule 2: ISO Date Normalization
        current_xml, date_healed = heal_iso_date(current_xml)
        if date_healed:
            total_heals += 1

        if total_heals > 0:
            status = "HEALED"
            fine_saved = total_heals * self.fine_per_healing
        else:
            status = "PASSTHROUGH"
            fine_saved = 0.0

        return {
            "status": status,
            "healed_payload": current_xml,
            "heals_count": total_heals,
            "fine_saved_usd": fine_saved
        }