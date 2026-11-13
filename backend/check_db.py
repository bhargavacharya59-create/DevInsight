import sqlite3
conn = sqlite3.connect('devinsight_dev.db')
cursor = conn.execute('SELECT COUNT(*) FROM incidents')
print('Total incidents in DB:', cursor.fetchone()[0])
cursor2 = conn.execute("SELECT id, title, is_demo, affected_service, severity FROM incidents ORDER BY rowid DESC LIMIT 20")
rows = cursor2.fetchall()
print(f'All incidents ({len(rows)}):')
for r in rows:
    print(f"  id={r[0][:8]} svc={r[3]} demo={r[2]} sev={r[4]} title={str(r[1])[:55]}")
conn.close()
