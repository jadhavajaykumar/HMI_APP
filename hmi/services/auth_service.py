import json
from pathlib import Path


class AuthService:
    def __init__(self, users_path: str):
        self.users_path = Path(users_path)
        self.users = self._load_users()

    def _load_users(self):
        if not self.users_path.exists():
            return []
        data = json.loads(self.users_path.read_text(encoding="utf-8"))
        return data.get("users", [])

    def authenticate(self, username: str, password: str):
        for user in self.users:
            if user["username"] == username and user["password"] == password:
                return user
        return None