import json
from datetime import datetime
from pathlib import Path


class AuditService:
    def __init__(self, enabled: bool = True, log_path: str = "logs/audit_log.jsonl"):
        self.enabled = enabled
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, action: str, user: dict | None = None, details: dict | None = None):
        if not self.enabled:
            return

        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "user": user or {},
            "details": details or {},
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")