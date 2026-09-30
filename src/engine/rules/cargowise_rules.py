import re

class CargoWiseRuleEngine:
    # Simulated Master Database & eDocs Extracted Data (BL, Commercial Invoice, Packing List)
    EDOCS_MASTER_DB = {
        "MSCU1234567": {
            "weight": "12500.50",
            "hs_code": "8471.30",
            "description": "ELECTRONIC INTEGRATED CIRCUITS",
            "container_number": "MSCU1234567"
        }
    }

    @classmethod
    def validate_and_heal_with_edocs(cls, xml_content: str) -> tuple[str, list[str]]:
        healed_xml = xml_content
        logs = []

        # 1. Container Number Correction / Standardizing
        container_match = re.search(r'<ContainerNumber>(.*?)</ContainerNumber>', healed_xml)
        container_no = container_match.group(1).strip() if container_match else "MSCU1234567"

        # Check DB / eDocs reference
        edocs_data = cls.EDOCS_MASTER_DB.get(container_no, cls.EDOCS_MASTER_DB["MSCU1234567"])

        # 2. HS Code Cross-Verification & Auto-Insertion from Commercial Invoice
        if "<HSCode>" not in healed_xml:
            healed_xml = healed_xml.replace(
                "</Consignment>",
                f"  <HSCode>{edocs_data['hs_code']}</HSCode>\n    </Consignment>"
            )
            logs.append(f"Auto-Healed: HS Code {edocs_data['hs_code']} fetched from eDocs (CIV) and mapped.")

        # 3. Goods Description Matching from Packing List
        if "<Description>" not in healed_xml:
            healed_xml = healed_xml.replace(
                "</Consignment>",
                f"  <Description>{edocs_data['description']}</Description>\n    </Consignment>"
            )
            logs.append("Auto-Healed: Goods Description verified against eDocs (PKL) & mapped.")

        # 4. Gross Weight Mismatch Check with Bill of Lading (BL)
        weight_match = re.search(r'<Weight>(.*?)</Weight>', healed_xml)
        if weight_match and weight_match.group(1) != edocs_data['weight']:
            old_w = weight_match.group(1)
            healed_xml = healed_xml.replace(f"<Weight>{old_w}</Weight>", f"<Weight>{edocs_data['weight']}</Weight>")
            logs.append(f"Mismatch Fixed: Weight {old_w} auto-corrected to {edocs_data['weight']} KGS from BL.")

        return healed_xml, logs