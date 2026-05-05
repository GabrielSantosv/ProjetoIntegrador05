import psycopg
import sys

old_db = 'legal_docs_django'
new_db = 'Projeto_integrador'

try:
    # Connect to postgres maintenance DB
    conn = psycopg.connect(dbname='postgres', user='postgres', password='admin', host='localhost')
    conn.autocommit = True
    cur = conn.cursor()

    # Check source exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (old_db,))
    if not cur.fetchone():
        print(f'Source database "{old_db}" does not exist. Nothing to rename.')
        sys.exit(0)

    # Check target does not exist
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (new_db,))
    if cur.fetchone():
        print(f'Target database "{new_db}" already exists. Aborting to avoid overwrite.')
        sys.exit(1)

    # Terminate other connections to the source database
    cur.execute("""
        SELECT pid FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid();
    """, (old_db,))
    pids = [r[0] for r in cur.fetchall()]
    if pids:
        print(f'Terminating {len(pids)} connection(s) to "{old_db}"')
        for pid in pids:
            try:
                cur.execute("SELECT pg_terminate_backend(%s)", (pid,))
            except Exception as e:
                print('Failed to terminate pid', pid, e)

    # Perform rename
    try:
        cur.execute(f'ALTER DATABASE "{old_db}" RENAME TO "{new_db}";')
        print(f'Database renamed: {old_db} -> {new_db}')
    except Exception as e:
        print('Rename failed:', e)
        sys.exit(2)

    # Verify
    cur.execute("SELECT datname FROM pg_database WHERE datname = %s", (new_db,))
    if cur.fetchone():
        print('Verified new database exists:', new_db)
    else:
        print('Verification failed: new database not found')

    cur.close()
    conn.close()

except Exception as e:
    print('Error:', e)
    sys.exit(3)
