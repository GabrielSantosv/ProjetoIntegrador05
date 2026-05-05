import psycopg

try:
    conn = psycopg.connect('dbname=legal_docs_django user=postgres password=admin host=localhost')
    cur = conn.cursor()
    
    print('=' * 80)
    print('DIAGNÓSTICO DO BANCO DE DADOS')
    print('=' * 80)
    
    # Check if database exists
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f'\n✓ PostgreSQL versão: {version.split(",")[0]}')
    
    # List all tables
    cur.execute("""SELECT table_name FROM information_schema.tables 
                 WHERE table_schema = 'public' ORDER BY table_name""")
    tables = cur.fetchall()
    print(f'\n✓ Tabelas encontradas ({len(tables)}):')
    for table in tables:
        print(f'  - {table[0]}')
    
    # Check documents table
    cur.execute('SELECT COUNT(*) FROM documents_document')
    count = cur.fetchone()[0]
    print(f'\n✓ Registros em documents_document: {count}')
    
    # Show sample data
    if count > 0:
        print(f'\n📄 Últimos 3 registros:')
        cur.execute("""SELECT id, title, status, document_type, risk_score 
                     FROM documents_document 
                     ORDER BY id DESC LIMIT 3""")
        for row in cur.fetchall():
            print(f'  [{row[0]}] {row[1][:30]:30} | Status: {row[2]:10} | Type: {row[3]}')
    
    conn.close()
    
except Exception as e:
    print(f'✗ Erro de conexão: {str(e)}')
    print('\nVerifique:')
    print('1. PostgreSQL está rodando?')
    print('2. Banco "legal_docs_django" existe?')
    print('3. Usuário "postgres" com senha "admin"?')
