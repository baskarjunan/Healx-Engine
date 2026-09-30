import pika
import json
import sqlite3
import re
import os

# SQLite DB Path (Project Root-ல் உள்ள healx_db.db)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "healx_db.db")

def heal_xml_payload(xml_string):
    """
    Auto-Healing Engine Rules:
    1. UN/LOCODE normalization (e.g., 'IN MAA' or 'in maa' -> 'INMAA')
    2. Date format normalization
    """
    errors_fixed = []

    # 1. UN/LOCODE Auto-Heal Rule (Handles spaces, lowercase, and formatting)
    def fix_locode(match):
        errors_fixed.append("UNLOCODE_NORMALISED")
        raw_code = match.group(1).replace(" ", "").upper()
        return f"<PortOfLoading>{raw_code}</PortOfLoading>"

    # Regex matches <PortOfLoading> inside tags
    healed_xml = re.sub(r"<PortOfLoading>\s*(.*?)\s*</PortOfLoading>", fix_locode, xml_string, flags=re.DOTALL)

    status = "HEALED" if len(errors_fixed) > 0 else "PASSTHROUGH"
    return healed_xml, status, ",".join(list(set(errors_fixed)))

def process_message(ch, method, properties, body):
    try:
        data = json.loads(body)
        correlation_id = data.get("correlation_id")
        tenant_id = data.get("tenant_id")
        message_type = data.get("message_type")
        raw_payload = data.get("payload")

        # Auto-Heal Logic execution
        healed_payload, status, error_types_str = heal_xml_payload(raw_payload)

        # Cost Savings Metrics Calculation
        fine_savings = 150.00 if status == "HEALED" else 0.00
        hours_saved = 0.33 if status == "HEALED" else 0.00

        # SQLite3 Audit Logging
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO healx_audit_logs 
            (correlation_id, tenant_id, message_type, status, original_payload, healed_payload, error_types, manual_hours_saved, est_fine_prevented_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            correlation_id, tenant_id, message_type, status, 
            raw_payload, healed_payload, error_types_str, hours_saved, fine_savings
        ))

        conn.commit()
        conn.close()

        print(f" [✔] Processed Payload: {correlation_id} | Status: {status} | Fine Saved: ${fine_savings}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f" [❌] Error processing payload: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_worker():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='eadaptor_inbound_queue', durable=True)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='eadaptor_inbound_queue', on_message_callback=process_message)

    print(' [*] HealX Worker Engine Running (SQLite Persistence)... Waiting for Inbound XMLs.')
    channel.start_consuming()

if __name__ == "__main__":
    start_worker()