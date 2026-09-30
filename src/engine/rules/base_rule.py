from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, List
from lxml import etree

class BaseHealingRule(ABC):
    rule_code: str = "BASE_RULE"
    description: str = "Base Healing Rule"

    @abstractmethod
    def apply(self, tree: etree._ElementTree) -> Tuple[etree._ElementTree, List[Dict[str, Any]]]:
        """
        Applies transformation logic to the XML Tree.
        Returns: (Modified XML Tree, List of Audit Entries)
        """
        pass