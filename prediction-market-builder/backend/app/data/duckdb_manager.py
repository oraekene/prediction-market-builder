import duckdb
from datetime import datetime
from app.config import settings


class DuckDBManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = duckdb.connect(settings.duckdb_path)
            cls._instance._ensure_tables()
        return cls._instance

    def _ensure_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS market_analytics (
                id VARCHAR PRIMARY KEY,
                platform VARCHAR,
                title VARCHAR,
                category VARCHAR,
                current_odds DOUBLE,
                volume DOUBLE,
                liquidity DOUBLE,
                participants INTEGER,
                close_time TIMESTAMP,
                status VARCHAR,
                last_updated TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id VARCHAR,
                strategy_id VARCHAR,
                total_trades INTEGER,
                win_rate DOUBLE,
                profit_loss DOUBLE,
                sharpe_ratio DOUBLE,
                max_drawdown DOUBLE,
                period_start DATE,
                period_end DATE
            )
        """)
        self._create_indexes()

    def _create_indexes(self):
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_market_platform ON market_analytics(platform)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_market_category ON market_analytics(category)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_market_status ON market_analytics(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_market_volume ON market_analytics(volume DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_market_close_time ON market_analytics(close_time)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_strat_perf_id ON strategy_performance(strategy_id)")

    def query_markets(self, sql_filter: str = "1=1", limit: int = 1000) -> list[dict]:
        safe_filter = sql_filter.replace(";", "").strip()
        result = self.conn.execute(
            "SELECT * FROM market_analytics WHERE {} ORDER BY volume DESC LIMIT ?".format(safe_filter), [limit]
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]

    def insert_market(self, data: dict):
        keys = ["id", "platform", "title", "category", "current_odds", "volume", "liquidity", "participants", "close_time", "status", "last_updated"]
        values = [data.get(k) for k in keys]
        placeholders = ",".join("?" for _ in keys)
        self.conn.execute(f"INSERT OR REPLACE INTO market_analytics VALUES ({placeholders})", values)

    def insert_markets_batch(self, markets: list[dict]):
        for market in markets:
            self.insert_market(market)

    def get_top_categories(self) -> list[dict]:
        result = self.conn.execute(
            "SELECT category, COUNT(*) as count, AVG(volume) as avg_volume FROM market_analytics WHERE category IS NOT NULL GROUP BY category ORDER BY count DESC"
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, r)) for r in result.fetchall()]

    def get_volume_leaders(self, top_n: int = 10) -> list[dict]:
        result = self.conn.execute(
            "SELECT title, platform, volume FROM market_analytics ORDER BY volume DESC LIMIT ?", [top_n]
        )
        columns = [desc[0] for desc in result.description]
        return [dict(zip(columns, r)) for r in result.fetchall()]

    def record_strategy_performance(self, data: dict):
        keys = ["id", "strategy_id", "total_trades", "win_rate", "profit_loss", "sharpe_ratio", "max_drawdown", "period_start", "period_end"]
        values = [data.get(k) for k in keys]
        placeholders = ",".join("?" for _ in keys)
        self.conn.execute(f"INSERT OR REPLACE INTO strategy_performance VALUES ({placeholders})", values)
