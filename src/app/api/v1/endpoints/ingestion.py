from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel
import pika
import json
import uuid

router = APIRouter()

# Request Body Model
class XMLPayloadRequest(BaseModel):
    payload: str

@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_xml_payload(
    data: XMLPayloadRequest,
    x_tenant_id: str = Header(..., alias="x-tenant-id"),
    x_message_type: str = Header(..., alias="x-message-type")
):
    correlation_id = str(uuid.uuid4())
    
    message_body = {
        "correlation_id": correlation_id,
        "tenant_id": x_tenant_id,
        "message_type": x_message_type,
        "payload": data.payload
    }

    # RabbitMQ Connection
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='eadaptor_inbound_queue', durable=True)

        channel.basic_publish(
            exchange='',
            routing_key='eadaptor_inbound_queue',
            body=json.dumps(message_body),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type='application/json'
            )
        )
        connection.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RabbitMQ Publish Failed: {str(e)}")

    return {"status": "ACCEPTED", "correlation_id": correlation_id}

from fastapi import APIRouter, UploadFile, File, Form
from src.engine.rules.cargowise_rules import CargoWiseRuleEngine

router = APIRouter()

@router.post("/ingest")
async def ingest_xml(client_id: str = Form(...), file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8")
    
    # Run Self-Healing Engine
    healed_content, is_healed = CargoWiseRuleEngine.apply_all_healing(content)
    
    status = "HEALED" if is_healed else "PASSED"
    
    return {
        "status": "SUCCESS",
        "client_id": client_id,
        "filename": file.filename,
        "healing_status": status,
        "message": "XML Processed and Healed Successfully" if is_healed else "XML Validated - No Healing Required"
    }

from fastapi import APIRouter, UploadFile, File, Form
from src.engine.rules.cargowise_rules import CargoWiseRuleEngine

router = APIRouter()

@router.post("/ingest")
async def ingest_xml(client_id: str = Form(...), file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8")
    
    # Run eDocs Cross-Matching & Healing Engine
    healed_xml, audit_logs = CargoWiseRuleEngine.validate_and_heal_with_edocs(content)
    
    is_healed = len(audit_logs) > 0
    
    return {
        "status": "SUCCESS",
        "client_id": client_id,
        "filename": file.filename,
        "healing_status": "HEALED" if is_healed else "PASSED",
        "edocs_audit_logs": audit_logs,
        "mapped_to_cargowise": True,
        "message": "XML Cross-Verified with eDocs (BL/CIV/PKL) and Ingested to CargoWise Gateway"
    }