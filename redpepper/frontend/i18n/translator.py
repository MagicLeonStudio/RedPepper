import json
import os


class Translator:
    def __init__(self, locale="zh_CN"):
        self.locale = locale
        self.translations = self._load_translations(locale)

    def _load_translations(self, locale: str) -> dict:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_dir, f"{locale}.json")
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def tr(self, key: str, *args, **kwargs) -> str:
        keys = key.split(".")
        value = self.translations
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return key
        if not isinstance(value, str):
            return key
        try:
            if args:
                return value.format(*args)
            if kwargs:
                return value.format(**kwargs)
            return value
        except Exception:
            return value

    def set_locale(self, locale: str):
        self.locale = locale
        self.translations = self._load_translations(locale)


def set_locale(locale: str):
    _translator.set_locale(locale)


def tr(key: str, *args, **kwargs) -> str:
    return _translator.tr(key, *args, **kwargs)


def get_locale() -> str:
    return _translator.locale


_translator = Translator("zh_CN")
