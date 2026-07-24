from database.connection import DatabaseManager
import pprint

db = DatabaseManager()
conn = db.__enter__()
cur = conn.cursor(dictionary=True)
cur.execute('SELECT entity_id, increment_id, relation_parent_id, relation_parent_real_id, relation_child_id, relation_child_real_id, original_increment_id FROM sales_order WHERE increment_id LIKE "%-%" LIMIT 5')
results_child = cur.fetchall()

print("Child orders (with suffix):")
pprint.pprint(results_child)

cur.execute('SELECT entity_id, increment_id, relation_parent_id, relation_parent_real_id, relation_child_id, relation_child_real_id, original_increment_id FROM sales_order WHERE relation_child_id IS NOT NULL LIMIT 5')
results_parent = cur.fetchall()

print("Parent orders (with children):")
pprint.pprint(results_parent)

cur.close()
db.__exit__(None, None, None)
