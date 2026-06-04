from .api_client import APIClient, get_client

from pathlib import Path

import yaml


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

    def load_ai_config(self) -> dict:
        config_path = self._config_path()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raw = {}

        ai = raw.get("ai", {}) or {}
        providers = ai.get("providers", {}) or {}
        scene_models = ai.get("scene_models", {}) or {}

        return {
            "default_provider": ai.get("default_provider", "kimi"),
            "screenshot_ocr": scene_models.get("screenshot_ocr", ""),
            "providers": {
                "kimi": providers.get("kimi", {}) or {},
                "deepseek": providers.get("deepseek", {}) or {},
            },
        }

    def save_ai_config(self, config: dict) -> dict:
        """Save AI configuration – frontend convenience method.

        Currently writes to config.yaml locally.  Full implementation would
        call a backend endpoint.
        """
        config_path = self._config_path()

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
                if value:
                    raw["ai"]["providers"][provider][key] = value

        if "default_provider" in config:
            raw["ai"]["default_provider"] = config["default_provider"]

        if "scene_models" not in raw["ai"]:
            raw["ai"]["scene_models"] = {}

        default_provider = raw["ai"].get("default_provider", "kimi")
        default_model = (
            raw["ai"]["providers"].get(default_provider, {}) or {}
        ).get("default_model")
        if default_model:
            raw["ai"]["scene_models"]["screenshot_ocr"] = default_model

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return {"message": "Configuration saved"}

    @staticmethod
    def _config_path() -> str:
        return str((Path(__file__).resolve().parents[1] / ".." / "backend" / "config.yaml").resolve())
