from .api_client import APIClient, get_client


class AuthService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/auth"

    def setup(self, username: str, password: str) -> dict:
        """Set up password for first-time use."""
        return self.client.post(
            f"{self.base_path}/setup",
            json={"username": username, "password": password},
        )

    def login(self, username: str, password: str) -> dict:
        """Login with username and password."""
        return self.client.post(
            f"{self.base_path}/login",
            json={"username": username, "password": password},
        )

    def has_user(self) -> dict:
        """Check if a user has been set up."""
        return self.client.get(f"{self.base_path}/has-user")

    def change_password(self, old_password: str, new_password: str) -> dict:
        """Change the current password."""
        return self.client.post(
            f"{self.base_path}/change-password",
            json={"old_password": old_password, "new_password": new_password},
        )
