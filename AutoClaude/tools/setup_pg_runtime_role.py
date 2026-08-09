"""建立 autoclaude_runtime PostgreSQL role（最小權限）。

DB: aisdlc @ 192.168.1.133
需要 superuser（postgres）才能 CREATE ROLE。

🔴 憑證一律由環境變數提供，**檔內不留任何預設值**（R82）。原版把 superuser 密碼與
   `koala` 帳號密碼寫死在登入候選清單裡、又給 `RUNTIME_PASS` 一個弱密碼預設值——
   那是入庫的明文憑證，而「有預設值」讓它在沒人察覺的情況下持續可用（risk_log
   R-P6-02 已於 2026-05-15 輪換掉那個預設值，這支腳本卻仍會把它重新建回去）。
   缺任一必填變數時直接 rc=2 停下：「沒設定」與「設定成佔位符」都不該靜默通過。

必填環境變數：
  RUNTIME_PASS            要指派給 autoclaude_runtime 的強密碼（≥20 字元）
  PG_SUPERUSER_PASSWORD   superuser 密碼（CREATE ROLE 需要）
選配：
  PG_SUPERUSER            superuser 帳號，預設 postgres（帳號非機密，故可留預設）
  PG_FALLBACK_USER / PG_FALLBACK_PASSWORD   第二組候選登入（兩者都設定時才嘗試）
  PG_HOST                 DB 主機，預設 192.168.1.133

用法（PowerShell）：
  $env:RUNTIME_PASS='...'; $env:PG_SUPERUSER_PASSWORD='...'
  python tools/setup_pg_runtime_role.py
"""
import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

PG_HOST = os.environ.get("PG_HOST", "192.168.1.133")
PG_DBNAME = os.environ.get("PG_DBNAME", "aisdlc")


def login_candidates():
    """依序嘗試的 (user, password) 清單。**沒有任何寫死的密碼**。

    密碼未設定的候選一律不進清單——留一個 `password=None` 的候選只會換來一次
    看不懂的 OperationalError，而不是「你少設了一個環境變數」這個真正的訊息。
    """
    candidates = []
    superuser = os.environ.get("PG_SUPERUSER", "postgres")
    superpass = os.environ.get("PG_SUPERUSER_PASSWORD")
    if superpass:
        candidates.append((superuser, superpass))
    fallback_user = os.environ.get("PG_FALLBACK_USER")
    fallback_pass = os.environ.get("PG_FALLBACK_PASSWORD")
    if fallback_user and fallback_pass:
        candidates.append((fallback_user, fallback_pass))
    return candidates


def build_sql_steps(runtime_pass):
    """組出 SQL 步驟。`runtime_pass` 由呼叫端負責驗證非空（見 `main`）。

    🔴 刻意做成函式而非模組層常數：常數版會在 import 當下就把 `RUNTIME_PASS` 內插
    進 SQL，於是「變數沒設」會靜默變成 `CREATE ROLE ... PASSWORD 'None'`——建出一個
    密碼是字串 None 的可登入 role，比直接失敗糟得多。
    """
    return [
        # 1. 建立 runtime role
        ("CREATE runtime role",
         f"""
     DO $$
     BEGIN
         IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'autoclaude_runtime') THEN
             CREATE ROLE autoclaude_runtime WITH LOGIN PASSWORD '{runtime_pass}';
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
    runtime_pass = os.environ.get("RUNTIME_PASS")
    if not runtime_pass:
        print("[ERROR] 未設定 RUNTIME_PASS（要指派給 autoclaude_runtime 的強密碼）。"
              " 本腳本刻意不提供預設值——見檔頭。")
        sys.exit(2)

    candidates = login_candidates()
    if not candidates:
        print("[ERROR] 未設定 PG_SUPERUSER_PASSWORD，沒有任何可嘗試的登入候選。"
              " 本腳本刻意不提供預設值——見檔頭。")
        sys.exit(2)

    conn = None
    # 嘗試 superuser 連線（憑證全部來自環境變數）
    for user, password in candidates:
        try:
            conn = psycopg2.connect(
                host=PG_HOST, dbname=PG_DBNAME,
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
        print("[WARN] Current user lacks CREATEROLE/superuser — CREATE ROLE may fail.")

    print("\n=== Executing SQL steps ===")
    errors = []
    for name, sql in build_sql_steps(runtime_pass):
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
        # 🔴 不回印密碼：這支腳本的輸出會進終端 scrollback／CI log，回印等於再開一個
        # 外洩管道（同 tools/lib/secret_scan.py 的 `mask()` 立案理由）。
        print("\n[SUMMARY] All steps OK. autoclaude_runtime 密碼＝$RUNTIME_PASS 的值（未回印）")


if __name__ == "__main__":
    main()
