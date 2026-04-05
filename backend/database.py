import os
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from dateutil.relativedelta import relativedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "app.db")


def get_db_path():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return DB_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表结构"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_vip INTEGER DEFAULT 0,
                vip_expire_at TEXT,
                plan_type TEXT DEFAULT 'free',
                daily_summary_count INTEGER DEFAULT 0,
                last_summary_date TEXT,
                ai_credits INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                currency TEXT DEFAULT 'cny',
                status TEXT DEFAULT 'pending',
                plan_type TEXT DEFAULT 'monthly',
                stripe_session_id TEXT UNIQUE,
                stripe_payment_intent_id TEXT,
                paid_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS ai_usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                video_url TEXT,
                cost_units INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
            CREATE INDEX IF NOT EXISTS idx_orders_order_no ON orders(order_no);
            CREATE INDEX IF NOT EXISTS idx_orders_stripe_session_id ON orders(stripe_session_id);
            CREATE INDEX IF NOT EXISTS idx_ai_usage_user_date ON ai_usage_logs(user_id, date(created_at));
            CREATE INDEX IF NOT EXISTS idx_ai_usage_feature ON ai_usage_logs(feature);
        """)


# 常量定义
FREE_DAILY_SUMMARY_LIMIT = 3
FREE_DAILY_AI_LIMIT = 10
VIP_DAILY_AI_LIMIT = 50

# 专业版AI功能列表
PROFESSIONAL_AI_FEATURES = [
    "professional_analysis",
    "academic_analysis", 
    "business_analysis",
    "detailed_mindmap",
    "study_notes",
    "key_quotes",
    "deep_context_qa",
]


def get_user_by_email(email: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def create_user(email: str, password_hash: str) -> dict:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash),
        )
        return {"id": cursor.lastrowid, "email": email}


def check_and_increment_summary(user_id: int) -> tuple[bool, int]:
    """
    检查用户是否可以使用 AI 总结，并自增计数。
    返回 (allowed, remaining_count)
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False, 0

        if user["is_vip"] and user["vip_expire_at"]:
            expire = datetime.fromisoformat(user["vip_expire_at"])
            if expire > datetime.now(timezone.utc):
                return True, -1  # -1 means unlimited

        if user["last_summary_date"] != today:
            conn.execute(
                "UPDATE users SET daily_summary_count = 1, last_summary_date = ? WHERE id = ?",
                (today, user_id),
            )
            return True, FREE_DAILY_SUMMARY_LIMIT - 1

        current = user["daily_summary_count"]
        if current >= FREE_DAILY_SUMMARY_LIMIT:
            return False, 0

        conn.execute(
            "UPDATE users SET daily_summary_count = daily_summary_count + 1 WHERE id = ?",
            (user_id,),
        )
        return True, FREE_DAILY_SUMMARY_LIMIT - current - 1


def create_order(user_id: int, order_no: str, amount: int, currency: str = "cny", plan_type: str = "monthly") -> dict:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO orders (order_no, user_id, amount, currency, plan_type) VALUES (?, ?, ?, ?, ?)",
            (order_no, user_id, amount, currency, plan_type),
        )
        return {"order_no": order_no, "user_id": user_id, "amount": amount}


def update_order_stripe_session(order_no: str, session_id: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE orders SET stripe_session_id = ?, updated_at = datetime('now') WHERE order_no = ?",
            (session_id, order_no),
        )


def complete_order(session_id: str, payment_intent_id: str) -> dict | None:
    """
    支付完成时更新订单状态、激活 VIP。
    使用事务保证幂等：只有 pending 状态的订单才会被更新。
    """
    with get_db() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE stripe_session_id = ? AND status = 'pending'",
            (session_id,),
        ).fetchone()

        if not order:
            return None

        now = datetime.now(timezone.utc).isoformat()

        from dateutil.relativedelta import relativedelta
        user = conn.execute("SELECT * FROM users WHERE id = ?", (order["user_id"],)).fetchone()

        current_expire = None
        if user["vip_expire_at"]:
            try:
                current_expire = datetime.fromisoformat(user["vip_expire_at"])
            except ValueError:
                pass

        base_time = datetime.now(timezone.utc)
        if current_expire and current_expire > base_time:
            base_time = current_expire

        # 根据套餐类型计算过期时间
        if order["plan_type"] == "monthly":
            new_expire = base_time + relativedelta(months=1)
        elif order["plan_type"] == "professional_monthly":
            new_expire = base_time + relativedelta(months=1)
        elif order["plan_type"] == "professional_yearly":
            new_expire = base_time + relativedelta(years=1)
        else:
            new_expire = base_time + relativedelta(months=1)

        conn.execute(
            "UPDATE orders SET status = 'paid', stripe_payment_intent_id = ?, paid_at = ?, updated_at = ? WHERE id = ?",
            (payment_intent_id, now, now, order["id"]),
        )

        # 更新用户计划和VIP状态
        conn.execute(
            """
            UPDATE users 
            SET is_vip = 1, vip_expire_at = ?, plan_type = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_expire.isoformat(), order["plan_type"], now, order["user_id"]),
        )

        return dict(order)


def get_order_by_no(order_no: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM orders WHERE order_no = ?", (order_no,)).fetchone()
        return dict(row) if row else None


def get_user_orders(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_user_plan(user_id: int, plan_type: str, expire_at: str = None):
    """更新用户套餐计划"""
    with get_db() as conn:
        now = datetime.now(timezone.utc).isoformat()
        
        # 设置VIP状态
        is_vip = plan_type != "free"
        
        # 计算过期时间
        if expire_at:
            vip_expire_at = expire_at
        elif plan_type == "monthly":
            vip_expire_at = (datetime.now(timezone.utc) + relativedelta(months=1)).isoformat()
        elif plan_type == "professional_monthly":
            vip_expire_at = (datetime.now(timezone.utc) + relativedelta(months=1)).isoformat()
        elif plan_type == "professional_yearly":
            vip_expire_at = (datetime.now(timezone.utc) + relativedelta(years=1)).isoformat()
        else:
            vip_expire_at = None
        
        conn.execute(
            """
            UPDATE users 
            SET is_vip = ?, vip_expire_at = ?, plan_type = ?, updated_at = ?
            WHERE id = ?
            """,
            (1 if is_vip else 0, vip_expire_at, plan_type, now, user_id)
        )
        return True


def record_ai_usage(user_id: int, feature: str, video_url: str = "", cost_units: int = 1) -> bool:
    """记录AI使用情况"""
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO ai_usage_logs (user_id, feature, video_url, cost_units)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, feature, video_url, cost_units)
        )
        return True


def get_user_ai_usage_today(user_id: int) -> int:
    """获取用户今日AI使用次数"""
    with get_db() as conn:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = conn.execute(
            """
            SELECT COUNT(*) as count 
            FROM ai_usage_logs 
            WHERE user_id = ? AND date(created_at) = ?
            """,
            (user_id, today)
        ).fetchone()
        return row["count"] if row else 0


def get_user_ai_usage_by_feature(user_id: int, days: int = 7) -> dict:
    """获取用户按功能分类的AI使用统计"""
    with get_db() as conn:
        cutoff = datetime.now(timezone.utc) - relativedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
        
        rows = conn.execute(
            """
            SELECT feature, COUNT(*) as count, SUM(cost_units) as total_cost
            FROM ai_usage_logs 
            WHERE user_id = ? AND created_at >= ?
            GROUP BY feature
            ORDER BY count DESC
            """,
            (user_id, cutoff_str)
        ).fetchall()
        
        return {row["feature"]: {"count": row["count"], "total_cost": row["total_cost"]} for row in rows}


def get_user_plan_info(user_id: int) -> dict:
    """获取用户套餐信息"""
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    # 检查VIP是否过期
    is_vip = user.get("is_vip", False)
    vip_expire_at = user.get("vip_expire_at")
    
    if is_vip and vip_expire_at:
        try:
            expire_date = datetime.fromisoformat(vip_expire_at.replace('Z', '+00:00'))
            if expire_date < datetime.now(timezone.utc):
                # VIP已过期
                is_vip = False
        except ValueError:
            is_vip = False
    
    return {
        "user_id": user_id,
        "is_vip": is_vip,
        "plan_type": user.get("plan_type", "free"),
        "vip_expire_at": vip_expire_at,
        "ai_credits": user.get("ai_credits", 0),
        "daily_summary_count": user.get("daily_summary_count", 0),
    }
