from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
import xml.etree.ElementTree as ET
import json
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
    shipment_id: Optional[str] = "CW-DEFAULT-ID"
    xml_payload: str
    edoc_source_text: Optional[str] = ""

def autonomous_healing_worker(shipment_id: str, xml_str: str, edoc_text: str):
    global system_metrics
    
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        print(f"[HealX Error] Shipment {shipment_id}: Corrupted XML Payload. Details: {str(e)}")
        background_audit_logs.append({
            "shipment_id": shipment_id,
            "actions": [f"XML Parse Error: {str(e)}"],
            "status": "CORRUPTED_XML_REJECTED"
        })
        return

    extracted_truth = {}
    is_healed = False
    healed_actions = []

    weight_node = root.find(".//GrossWeight")
    container_node = root.find(".//ContainerNumber")

    # --- MODE 1: eDOC Cross-Verification Mode ---
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

    # --- MODE 2: Smart Schema & Format Validation Mode ---
    else:
        healed_actions.append("No eDOC provided. Executing Smart Schema & Format Validation.")
        
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

    # --- Mock eAdaptor Ingestion ---
    final_xml = ET.tostring(root, encoding="utf-8").decode("utf-8")
    eadaptor_status = "SUCCESS"

    # --- Update Metrics & Logs ---
    system_metrics["total_autonomous_processed"] += 1
    if is_healed:
        system_metrics["auto_healed_count"] += 1
        
    background_audit_logs.append({
        "shipment_id": shipment_id,
        "actions": healed_actions if healed_actions else ["Passed standard schema validation"],
        "status": "AUTONOMOUSLY_HEALED" if is_healed else "PROCESSED_SUCCESS"
    })
    
    print(f"[HealX Engine] Shipment {shipment_id} processed successfully. Status: {eadaptor_status}. Healed: {is_healed}")

# --- Autonomous Webhook Ingestion Endpoint (Supports both JSON & Raw XML from CargoWise) ---
@app.post("/api/v1/webhook/ingest-autonomous")
async def receive_shipment_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handles incoming webhooks from CargoWise eAdaptor. Supports JSON body or Raw XML payload strings.
    """
    body_bytes = await request.body()
    content_type = request.headers.get("content-type", "")
    
    shipment_id = "CW-SHIPMENT-LIVE"
    xml_payload = ""
    edoc_text = ""

    try:
        if "application/json" in content_type:
            data = json.loads(body_bytes.decode("utf-8"))
            shipment_id = data.get("shipment_id", "CW-SHIPMENT-LIVE")
            xml_payload = data.get("xml_payload", "")
            edoc_text = data.get("edoc_source_text", "")
        else:
            # If CargoWise pushes raw XML directly as text/plain or application/xml
            xml_payload = body_bytes.decode("utf-8")
            # Try to extract a shipment ID from XML if present, else fallback
            match_id = re.search(r'<HouseBill[^>]*>([^<]+)</HouseBill>', xml_payload)
            if match_id:
                shipment_id = match_id.group(1)
    except Exception as e:
        print(f"[HealX Error] Failed to parse incoming webhook payload: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid Payload Format")

    if not xml_payload:
        raise HTTPException(status_code=422, detail="Missing xml_payload in request body")

    # Add to background processing queue
    background_tasks.add_task(
        autonomous_healing_worker, 
        shipment_id, 
        xml_payload, 
        edoc_text
    )
    
    return {
        "status": "ACCEPTED",
        "message": "Payload and eDOC/Text received. HealX autonomous background processing initiated.",
        "shipment_id": shipment_id
    }

# --- Metrics Endpoint for Monitoring ---
@app.get("/api/v1/autonomous/metrics")
async def get_autonomous_metrics():
    return {
        "system_status": "ONLINE",
        "metrics": system_metrics,
        "recent_background_audits": background_audit_logs[-5:]
    }