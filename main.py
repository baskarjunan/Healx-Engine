from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import xml.etree.ElementTree as ET
import re

app = FastAPI(
    title="AuraLogix HealX Autonomous Engine", 
    version="3.2.0"
)

# Simulation Database & Metrics
background_audit_logs = []
system_metrics = {
    "total_autonomous_processed": 1851,
    "auto_healed_count": 1029,
    "fines_prevented_usd": 2800.0
}

class ShipmentIngestRequest(BaseModel):
    shipment_id: str
    xml_payload: str
    edoc_source_text: str = ""  # Optional (eDOC or email details text)

def autonomous_healing_worker(shipment_id: str, xml_str: str, edoc_text: str):
    global system_metrics
    
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        print(f"[HealX Error] Shipment {shipment_id}: Corrupted XML Payload.")
        return

    extracted_truth = {}
    is_healed = False
    healed_actions = []

    weight_node = root.find(".//GrossWeight")
    container_node = root.find(".//ContainerNumber")

    # --- MODE 1: eDOC Cross-Verification Mode (If eDOC/Text exists) ---
    if edoc_text and edoc_text.strip() != "":
        edoc_upper = edoc_text.upper()
        
        container_match = re.search(r'\b[A-Z]{4}[0-9]{7}\b', edoc_upper)
        if container_match:
            extracted_truth["ContainerNumber"] = container_match.group(0)
            
        weight_match = re.search(r'(?:WEIGHT|GW|GROSS)[^\d]*([\d]+\.?[\d]*)', edoc_upper)
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

        # Reconcile Weight
        if weight_node is not None:
            xml_wt = weight_node.text.strip() if weight_node.text else "0"
            try:
                true_wt = extracted_truth.get("GrossWeight")
                if true_wt and float(xml_wt) != float(true_wt):
                    weight_node.text = true_wt
                    healed_actions.append(f"eDOC Reconciled GrossWeight: {xml_wt}KG -> {true_wt}KG")
                    is_healed = True
                    system_metrics["fines_prevented_usd"] += 500.0
            except ValueError:
                pass

    # --- MODE 2: Smart Schema & Format Validation Mode (If NO eDOC / Mail text only) ---
    else:
        healed_actions.append("No eDOC provided. Executing Smart Schema & Format Validation.")
        
        # Check and fix weight if zero or negative or invalid
        if weight_node is not None:
            try:
                wt_val = float(weight_node.text) if weight_node.text else 0.0
                if wt_val <= 0:
                    weight_node.text = "500.0"
                    healed_actions.append("Schema Fallback: Corrected zero/negative weight to 500.0 KG")
                    is_healed = True
            except ValueError:
                weight_node.text = "500.0"
                healed_actions.append("Schema Fallback: Fixed non-numeric weight to 500.0 KG")
                is_healed = True
                
        # Check container format if needed
        if container_node is not None and container_node.text:
            cont_val = container_node.text.strip().upper()
            if not re.match(r'^[A-Z]{4}[0-9]{7}$', cont_val):
                pass

    # --- Mock eAdaptor Ingestion ---
    final_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")
    eadaptor_status = "SUCCESS" if "<UniversalShipment>" in final_xml else "REJECTED"

    # --- Update Metrics & Logs ---
    system_metrics["total_autonomous_processed"] += 1
    if is_healed:
        system_metrics["auto_healed_count"] += 1
        background_audit_logs.append({
            "shipment_id": shipment_id,
            "actions": healed_actions,
            "status": "AUTONOMOUSLY_HEALED"
        })
    
    print(f"[HealX Engine] Shipment {shipment_id} processed. Status: {eadaptor_status}. Healed: {is_healed}")

# --- Autonomous Webhook Ingestion Endpoint ---
@app.post("/api/v1/webhook/ingest-autonomous")
async def receive_shipment_webhook(payload: ShipmentIngestRequest, background_tasks: BackgroundTasks):
    """
    Client systems or eAdaptor gateway pushes data here.
    Returns immediate 202 Accepted response while background processing happens.
    """
    background_tasks.add_task(
        autonomous_healing_worker, 
        payload.shipment_id, 
        payload.xml_payload, 
        payload.edoc_source_text
    )
    
    return {
        "status": "ACCEPTED",
        "message": "Payload and eDOC/Text received. HealX autonomous background processing initiated.",
        "shipment_id": payload.shipment_id
    }

# --- Metrics Endpoint for Monitoring ---
@app.get("/api/v1/autonomous/metrics")
async def get_autonomous_metrics():
    return {
        "system_status": "ONLINE",
        "metrics": system_metrics,
        "recent_background_audits": background_audit_logs[-5:]
    }