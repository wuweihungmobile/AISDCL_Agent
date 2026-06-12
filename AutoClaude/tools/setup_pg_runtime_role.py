"""建立 autoclaude_runtime PostgreSQL role（最小權限）。

DB: aisdlc @ 192.168.1.133
需要 superuser（postgres）才能 CREATE ROLE。
用法：
  python tools/setup_pg_runtime_role.py
或指定密碼：
  RUNTIME_PASS=xxx python tools/setup_pg_runtime_role.py
"""
import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

RUNTIME_PASS = os.environ.get("RUNTIME_PASS", "runtime_autoclaude_2026")

SQL_STEPS = [
    # 1. 建立 runtime role
    ("CREATE runtime role",
     f"""
     DO $$
     BEGIN
         IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'autoclaude_runtime') THEN
             CREATE ROLE autoclaude_runtime WITH LOGIN PASSWORD '{RUNTIME_PASS}';
         ELSE
             RAISE NOTICE 'autoclaude_runtime already exists, skip create';
         END IF;
     END $$;
     """),

    # 2. 基本連線與 schema 使用權
    ("GRANT CONNECT + USAGE",
     "GRANT CONNECT ON DATABASE aisdlc TO autoclaude_runtime;"),
    ("GRANT USAGE schema",
     "GRANT USAGE ON SCHEMA public TO autoclaude_runtime;"),

    # 3. 資料表讀寫（CRUD，無 DDL）
    ("GRANT playbook_runs",
     "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE playbook_runs TO autoclaude_runtime;"),
    ("GRANT checkpoints",
     "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE checkpoints TO autoclaude_runtime;"),
    ("GRANT knowledge_entries",
     "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE knowledge_entries TO autoclaude_runtime;"),

    # 4. 序列（UUID 主鍵自動產生）
    ("GRANT sequences",
     "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO autoclaude_runtime;"),

    # 5. 明確拒絕 DDL
    ("REVOKE CREATE",
     "REVOKE CREATE ON SCHEMA public FROM autoclaude_runtime;"),
]

SQL_VERIFY = [
    ("role exists",
     "SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname = 'autoclaude_runtime'"),
    ("table grants",
     """SELECT table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privs
        FROM information_schema.role_table_grants
        WHERE grantee = 'autoclaude_runtime'
        GROUP BY table_name ORDER BY table_name"""),
    ("no DDL: CREATE in schema",
     """SELECT has_schema_privilege('autoclaude_runtime', 'public', 'CREATE')
        AS has_create_on_schema"""),
]


def main():
    # 嘗試 superuser (postgres) 連線
    for user, password in [("postgres", "postgres"), ("postgres", "koala5"), ("koala", "koala5")]:
        try:
            conn = psycopg2.connect(
                host="192.168.1.133", dbname="aisdlc",
                user=user, password=password, connect_timeout=10,
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            print(f"Connected as: {user}")
            break
        except psycopg2.OperationalError as e:
            print(f"  login {user}: {e.__class__.__name__}")
            conn = None

    if conn is None:
        print("\n[ERROR] Cannot connect. Please run the SQL manually on DB host as postgres.")
        sys.exit(1)

    cur = conn.cursor()

    # Check if current user has CREATEROLE
    cur.execute("SELECT rolcreaterole OR rolsuper FROM pg_roles WHERE rolname = current_user")
    can_create = cur.fetchone()[0]
    if not can_create:
        print(f"[WARN] Current user lacks CREATEROLE/superuser — CREATE ROLE may fail.")

    print("\n=== Executing SQL steps ===")
    errors = []
    for name, sql in SQL_STEPS:
        try:
            cur.execute(sql)
            print(f"  [OK] {name}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            errors.append((name, str(e)))

    print("\n=== Verification ===")
    for name, sql in SQL_VERIFY:
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            print(f"  [{name}]: {rows}")
        except Exception as e:
            print(f"  [{name}] ERROR: {e}")

    conn.close()

    if errors:
        print(f"\n[SUMMARY] {len(errors)} step(s) failed:")
        for n, e in errors:
            print(f"  - {n}: {e}")
        sys.exit(1)
    else:
        print(f"\n[SUMMARY] All steps OK. RUNTIME_PASS = {RUNTIME_PASS}")


if __name__ == "__main__":
    main()
