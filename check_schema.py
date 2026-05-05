import psycopg

conn = psycopg.connect('dbname=legal_docs_django user=postgres password=admin host=localhost')
cur = conn.cursor()

# Get table structure
cur.execute("""
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'documents_document'
ORDER BY ordinal_position
""")

print('Documents table schema:')
for col in cur.fetchall():
    nullable = 'NULL' if col[2] == 'YES' else 'NOT NULL'
    print(f'{col[0]:20} {col[1]:15} {nullable}')
