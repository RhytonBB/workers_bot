# вспомогательные SQL-запросы
def get_worker_by_telegram_id(conn, telegram_id):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM worker WHERE telegram_id = %s", (telegram_id,))
        return cur.fetchone()

def get_executor_by_key(conn, key, nick):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM executor WHERE access_key = %s AND telegram_nick = %s",
            (key, nick)
        )
        return cur.fetchone()

def insert_worker_from_executor(conn, executor_row, telegram_id):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO worker (telegram_id, telegram_nick, full_name, phone)
            VALUES ( %s, %s, %s, %s)
            RETURNING id
        """, (
            telegram_id,
            executor_row[8],  # telegram_nick
            f"{executor_row[1]} {executor_row[2]} {executor_row[3] or ''}".strip(),
            executor_row[6]
        ))
        conn.commit()

def increment_fail_attempts(conn, nick):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE executor
            SET fail_attempts = fail_attempts + 1
            WHERE telegram_nick = %s
        """, (nick,))
        conn.commit()

def block_executor(conn, nick):
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE executor
            SET is_blocked = true
            WHERE telegram_nick = %s
        """, (nick,))
        conn.commit()
