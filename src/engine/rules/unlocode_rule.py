import re
from typing import Tuple, Dict, Any, List
from lxml import etree
from src.engine.rules.base_rule import BaseHealingRule

class UNLocodeHealingRule(BaseHealingRule):
    rule_code = "UNLOCODE_CORRECTED"
    description = "Normalizes fuzzy or space-padded UN/LOCODE identifiers to 5-character ISO standard."

    TARGET_XPATHS = [
        "//PortOfLoading/Code",
        "//PortOfDischarge/Code",
        "//PlaceOfDelivery/Code",
        "//UNLOCODE"
    ]

    def apply(self, tree: etree._ElementTree) -> Tuple[etree._ElementTree, List[Dict[str, Any]]]:
        audit_logs = []
        for xpath in self.TARGET_XPATHS:
            nodes = tree.xpath(xpath)
            for node in nodes:
                if node.text:
                    original = node.text
                    cleaned = re.sub(r'[^A-Z0-9]', '', original.upper())
                    
                    if len(cleaned) == 5 and cleaned != original:
                        node.text = cleaned
                        audit_logs.append({
                            "rule_code": self.rule_code,
                            "field_xpath": tree.getpath(node),
                            "original_value": original,
                            "healed_value": cleaned,
                            "healing_strategy": "Regex whitespace and special character cleanup"
                        })
                        
        return tree, audit_logs