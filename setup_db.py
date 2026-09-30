import sqlite3

# 1. Local Database File உருவாக்குதல்
conn = sqlite3.connect('healx_db.db')
cursor = conn.cursor()

# 2. Audit Table உருவாக்குதல் (Cost Savings & Fine Prevention Metrics-உடன்)
cursor.execute('''
CREATE TABLE IF NOT EXISTS healx_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    correlation_id TEXT UNIQUE NOT NULL,
    tenant_id TEXT NOT NULL,
    message_type TEXT NOT NULL,
    status TEXT NOT NULL,
    original_payload TEXT NOT NULL,
    healed_payload TEXT,
    error_types TEXT,
    manual_hours_saved REAL DEFAULT 0.33,
    est_fine_prevented_usd REAL DEFAULT 150.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()

print(" [✔] SQLite Database 'healx_db.db' மற்றும் 'healx_audit_logs' Table வெற்றிகரமாக உருவாக்கப்பட்டது!")