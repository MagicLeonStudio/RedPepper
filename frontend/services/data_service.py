from .api_client import APIClient, get_client


class DataService:
    def __init__(self, client: APIClient = None):
        self.client = client or get_client()
        self.base_path = "/api/data"

    def export_data(self, password: str, output_path: str) -> dict:
        return self.client.post(
            f"{self.base_path}/export",
            json={"password": password, "output_path": output_path},
        )

    def import_data(self, file_path: str, password: str) -> dict:
        return self.client.post(
            f"{self.base_path}/import",
            json={"file_path": file_path, "password": password},
        )

    def import_csv(self, file_path: str) -> dict:
        return self.client.post(
            f"{self.base_path}/import-csv",
            json={"file_path": file_path},
        )

    # ---- Aliases for frontend page compatibility ----

    def reset_all_data(self) -> dict:
        """Reset all data – frontend convenience method.

        Currently a no-op; the actual reset would require backend support.
        """
        return {"message": "Please manually delete the database file and restart"}

    def save_ai_config(self, config: dict) -> dict:
        """Save AI configuration – frontend convenience method.

        Currently writes to config.yaml locally.  Full implementation would
        call a backend endpoint.
        """
        import os
        import yaml

        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "backend", "config.yaml"
        )
        config_path = os.path.abspath(config_path)

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raw = {}

        if "ai" not in raw:
            raw["ai"] = {}
        if "providers" not in raw["ai"]:
            raw["ai"]["providers"] = {}

        for provider, keys in config.get("providers", {}).items():
            if provider not in raw["ai"]["providers"]:
                raw["ai"]["providers"][provider] = {}
            for key, value in keys.items():
                raw["ai"]["providers"][provider][key] = value

        if "default_provider" in config:
            raw["ai"]["default_provider"] = config["default_provider"]

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, default_flow_style=False)

        return {"message": "Configuration saved"}
