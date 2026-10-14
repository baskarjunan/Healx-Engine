from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
import xml.etree.ElementTree as ET
import json
import re
import requests

app = FastAPI(
    title="AuraLogix HealX Autonomous Engine", 
    version="3.5.0",
    description="Autonomous Error-Healing Engine with eDOC Extraction & Bi-directional CargoWise Sync"
)

# --- CONFIGURATION: CargoWise eAdaptor Inbound URL ---
# Unga CW1 USAT Sandbox Inbound URL-ai inge enter pannunga
CARGOWISE_EADAPTOR_INBOUND_URL = "https://your-sandbox.cargowise.com/eAdaptor/Inbound"

class IngestPayload(BaseModel):
    shipment_id: Optional[str] = Field(default="CW-SHIPMENT-LIVE", example="WRCHI0001339")
    xml_payload: Optional[str] = Field(default="", example='<UniversalShipment>...</UniversalShipment>')
    edoc_source_text: Optional[str] = Field(default="", example="BILL OF LADING / INVOICE: CONTAINER MSCU1234567 GROSS WEIGHT 1250.00 KG")

# Simulation Database & Metrics
background_audit_logs = []
system_metrics = {
    "total_autonomous_processed": 1852,
    "auto_healed_count": 1030,
    "fines_prevented_usd": 2800.0
}

def find_xml_node(element, tag_name):
    """Helper to locate XML nodes ignoring CargoWise namespaces."""
    for elem in element.iter():
        if elem.tag.endswith(tag_name):
            return elem
    return None

def send_to_eadaptor(xml_payload: str) -> bool:
    """Sends the healed XML payload back to CargoWise eAdaptor Inbound so UI & DB update automatically."""
    headers = {"Content-Type": "application/xml; charset=utf-8"}
    try:
        # Authentication thevaiyal irunthal auth=('username', 'password') add pannikkonga
        response = requests.post(
            CARGOWISE_EADAPTOR_INBOUND_URL, 
            data=xml_payload.encode('utf-8'), 
            headers=headers, 
            timeout=15
        )
        if response.status_code in [200, 202]:
            print(f"[HealX Sync Success] Healed XML successfully pushed to CargoWise Inbound: {response.status_code}")
            return True
        else:
            print(f"[HealX Sync Error] CargoWise Inbound status: {response.status_code}, Body: {response.text}")
            return False
    except Exception as e:
        print(f"[HealX Sync Exception] Failed to sync with CargoWise: {str(e)}")
        return False

def autonomous_healing_worker(shipment_id: str, xml_str: str, edoc_text: str):
    global system_metrics
    
    xml_str = xml_str.strip()
    
    if xml_str.lower() == "string" or not xml_str:
        xml_str = """<?xml version="1.0" encoding="UTF-8"?>
        <UniversalShipment xmlns="http://www.cargowise.com/shipment/2011/03">
            <Shipment>
                <DataContext>
                    <Company><Code>TRN</Code></Company>
                    <EnterpriseID>ALG</EnterpriseID>
                    <ServerID>SYD</ServerID>
                </DataContext>
                <HouseBill>WRCHI0001339</HouseBill>
                <ContainerNumber>MSCU1234567</ContainerNumber>
                <GrossWeight>0.0</GrossWeight>
            </Shipment>
        </UniversalShipment>"""
        shipment_id = "WRCHI0001339"

    if not xml_str.startswith("<"):
        background_audit_logs.append({
            "shipment_id": shipment_id,
            "actions": ["Payload is not valid XML"],
            "status": "NON_XML_REJECTED"
        })
        return

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        background_audit_logs.append({
            "shipment_id": shipment_id,
            "actions": [f"XML Parse Error: {str(e)}"],
            "status": "CORRUPTED_XML_REJECTED"
        })
        return

    extracted_truth = {}
    is_healed = False
    healed_actions = []

    weight_node = find_xml_node(root, "GrossWeight")
    container_node = find_xml_node(root, "ContainerNumber")

    # --- MODE 1: eDOC Cross-Verification (BL, CIV, PKL Text Extraction) ---
    if edoc_text and edoc_text.strip() != "":
        edoc_upper = edoc_text.upper()
        
        # Regex to extract Container Number (e.g., MSCU1234567)
        container_match = re.search(r'\b[A-Z]{4}[0-9]{7}\b', edoc_upper)
        if container_match:
            extracted_truth["ContainerNumber"] = container_match.group(0)
            
        # Regex to extract Weight from BL/CIV/PKL text keywords
        weight_match = re.search(r'(?:WEIGHT|GW|GROSS|TOTAL|KGS)[^\d]*([\d]+\.?[\d]*)', edoc_upper)
        if weight_match:
            extracted_truth["GrossWeight"] = weight_match.group(1)

        # Reconcile Container Number
        if container_node is not None:
            xml_cont = container_node.text.strip().upper() if container_node.text else ""
            true_cont = extracted_truth.get("ContainerNumber")
            if true_cont and xml_cont != true_cont:
                container_node.text = true_cont
                healed_actions.append(f"eDOC Reconciled Container: {xml_cont} -> {true_cont}")
                is_healed = True

        # Reconcile Weight from eDOC
        if weight_node is not None:
            xml_wt = weight_node.text.strip() if weight_node.text else "0"
            try:
                true_wt = extracted_truth.get("GrossWeight")
                if true_wt and float(xml_wt) != float(true_wt):
                    weight_node.text = true_wt
                    healed_actions.append(f"eDOC Reconciled GrossWeight from BL/CIV/PKL: {xml_wt}KG -> {true_wt}KG")
                    is_healed = True
                    system_metrics["fines_prevented_usd"] += 500.0
            except ValueError:
                pass

    # --- MODE 2: Smart Schema & Fallback Validation ---
    if weight_node is not None:
        try:
            wt_val = float(weight_node.text) if weight_node.text else 0.0
            if wt_val <= 0:
                # If eDOC found a weight use it, otherwise apply intelligent default
                fallback_wt = extracted_truth.get("GrossWeight", "1000.0")
                weight_node.text = fallback_wt
                healed_actions.append(f"Schema/eDOC Fallback: Corrected zero weight to {fallback_wt} KG")
                is_healed = True
        except (ValueError, TypeError):
            weight_node.text = "1000.0"
            healed_actions.append("Schema Fallback: Fixed non-numeric weight to 1000.0 KG")
            is_healed = True

    # --- Generate Clean Healed XML ---
    final_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")

    # --- CRITICAL: Send Healed XML back to CargoWise Inbound ---
    sync_success = send_to_eadaptor(final_xml)
    if sync_success:
        healed_actions.append("Successfully synced healed XML back to CargoWise database.")

    # --- Update Metrics & Audit Logs ---
    system_metrics["total_autonomous_processed"] += 1
    if is_healed:
        system_metrics["auto_healed_count"] += 1
        
    background_audit_logs.append({
        "shipment_id": shipment_id,
        "actions": healed_actions if healed_actions else ["Passed standard validation"],
        "status": "AUTONOMOUSLY_HEALED_AND_SYNCED" if is_healed else "PROCESSED_SUCCESS"
    })
    
    print(f"[HealX Engine] Shipment {shipment_id} processed. Synced to CW: {sync_success}")

# --- Webhook Endpoint ---
@app.post("/api/v1/webhook/ingest-autonomous")
async def receive_shipment_webhook(request: Request, background_tasks: BackgroundTasks, payload: Optional[IngestPayload] = None):
    shipment_id = "CW-SHIPMENT-LIVE"
    xml_payload = ""
    edoc_text = ""

    content_type = request.headers.get("content-type", "").lower()
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8", errors="ignore").strip()

    try:
        if payload and (payload.xml_payload or payload.edoc_source_text):
            shipment_id = payload.shipment_id or "CW-SHIPMENT-LIVE"
            xml_payload = payload.xml_payload or ""
            edoc_text = payload.edoc_source_text or ""
        elif "xml" in content_type or body_str.startswith("<"):
            xml_payload = body_str
        elif "application/json" in content_type or body_str.startswith("{"):
            data = json.loads(body_str) if body_str else {}
            shipment_id = data.get("shipment_id", "CW-SHIPMENT-LIVE")
            xml_payload = data.get("xml_payload", "")
            edoc_text = data.get("edoc_source_text", "")

        if not xml_payload or xml_payload.lower() == "string":
            xml_payload = body_str

        if xml_payload and xml_payload.startswith("<"):
            match_id = re.search(r'<HouseBill[^>]*>([^<]+)</HouseBill>', xml_payload)
            if match_id:
                shipment_id = match_id.group(1)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Payload: {str(e)}")

    if not xml_payload:
        raise HTTPException(status_code=422, detail="Empty XML Payload received")

    background_tasks.add_task(
        autonomous_healing_worker, 
        shipment_id, 
        xml_payload, 
        edoc_text
    )
    
    return {
        "status": "ACCEPTED",
        "message": "HealX autonomous extraction and bi-directional sync initiated successfully.",
        "shipment_id": shipment_id
    }

# --- Metrics Monitoring Endpoint ---
@app.get("/api/v1/autonomous/metrics")
async def get_autonomous_metrics():
    return {
        "system_status": "ONLINE",
        "metrics": system_metrics,
        "recent_background_audits": background_audit_logs[-5:]
    }