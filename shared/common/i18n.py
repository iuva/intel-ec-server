"""
Internationalization (i18n) module

Provides multilingual message support, automatically detects language preference from Accept-Language header.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from shared.common.loguru_config import get_logger
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)

# Default language (Default: English)
DEFAULT_LOCALE = "en_US"

# Supported locales list
SUPPORTED_LOCALES = ["zh_CN", "en_US"]


class I18nManager:
    """Internationalization Manager

    Manages multilingual translation resources, supports dynamic loading and caching.
    """

    def __init__(self, locales_dir: Optional[str] = None):
        """Initialize the Internationalization Manager

        Args:
            locales_dir: Path to the language files directory, if None then auto-detect
        """
        if locales_dir is None:
            # Auto-detect language files directory
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            locales_dir = str(project_root / "shared" / "locales")

        self.locales_dir = Path(locales_dir)
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """Load all language files"""
        if not self.locales_dir.exists():
            logger.warning(f"Language files directory does not exist: {self.locales_dir}")
            return

        for locale in SUPPORTED_LOCALES:
            locale_file = self.locales_dir / f"{locale}.json"
            if locale_file.exists():
                try:
                    with open(locale_file, "r", encoding="utf-8") as f:
                        self._translations[locale] = json.load(f)
                    logger.info(f"Loaded language file: {locale} ({len(self._translations[locale])} translations)")
                except Exception as e:
                    logger.error(f"Failed to load language file: {locale_file}, Error: {str(e)}")
            else:
                logger.warning(f"Language file does not exist: {locale_file}")

    def translate(self, key: str, locale: Optional[str] = None, default: Optional[str] = None, **kwargs: Any) -> str:
        """Translate message key

        Args:
            key: Translation key (supports dot-separated nested keys, e.g., "error.host.not_found")
            locale: Locale code (e.g., "zh_CN", "en_US"), if None then uses default language
            default: Default message (used when key doesn't exist), if None then returns key itself
            **kwargs: Variables for message formatting (e.g., name="test" replaces {name})

        Returns:
            Translated message

        Examples:
            >>> i18n = I18nManager()
            >>> i18n.translate("success.operation", locale="zh_CN")
            "Operation successful"
            >>> i18n.translate("error.host.not_found", locale="en_US", host_id="123")
            "Host not found: 123"
        """
        if locale is None:
            locale = DEFAULT_LOCALE

        # If locale doesn't exist, use default language
        if locale not in self._translations:
            logger.debug(f"Locale doesn't exist: {locale}, using default language: {DEFAULT_LOCALE}")
            locale = DEFAULT_LOCALE

        # Get translation
        translations = self._translations.get(locale, {})
        message = self._get_nested_value(translations, key)

        # If translation not found, use default value or key itself
        if message is None:
            if default is not None:
                message = default
            else:
                logger.warning(f"Translation key doesn't exist: {key} (locale: {locale})")
                message = key

        # Format message (supports {variable} placeholders)
        # Only use basic types (str, int, float, bool, None) for formatting
        # avoid ***REMOVED***ing complex types like dictionaries
        if kwargs:
            # Filter out complex types, only keep basic types
            format_kwargs = {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool, type(None)))}
            try:
                message = message.format(**format_kwargs)
            except KeyError as e:
                logger.warning(f"Missing variables when formatting message: {key}, Missing: {e}")
                # If formatting fails, return original message
            except Exception as e:
                logger.error(f"Failed to format message: {key}, Error: {str(e)}")

        return message

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """Get value from nested dictionary

        Args:
            data: Dictionary data
            key: Key (supports dot-separated, e.g., "error.host.not_found")

        Returns:
            Value, or None if not exists
        """
        keys = key.split(".")
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return str(current) if current is not None else None

    def reload(self) -> None:
        """Reload language files (for hot reloading in development environment)"""
        self._translations.clear()
        self._load_translations()
        logger.info("Language files reloaded")


# Global instance
_i18n_manager_instance: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """Get global internationalization manager instance (singleton pattern)

    Returns:
        I18nManager instance
    """
    global _i18n_manager_instance

    if _i18n_manager_instance is None:
        _i18n_manager_instance = I18nManager()

    return _i18n_manager_instance


def t(key: str, locale: Optional[str] = None, default: Optional[str] = None, **kwargs: Any) -> str:
    """Translation shortcut function

    Args:
        key: Translation key
        locale: Locale code
        default: Default message
        **kwargs: Formatting variables

    Returns:
        Translated message

    Example:
        >>> t("success.operation", locale="en_US")
        "Operation successful"
    """
    return get_i18n_manager().translate(key, locale=locale, default=default, **kwargs)


def parse_accept_language(accept_language: Optional[str]) -> str:
    """Parse Accept-Language header, return the best matching locale code

    Args:
        accept_language: Accept-Language header value (e.g., "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7")

    Returns:
        Locale code (e.g., "zh_CN", "en_US"), return default language if unable to parse

    Examples:
        >>> parse_accept_language("zh-CN,zh;q=0.9")
        "zh_CN"
        >>> parse_accept_language("en-US,en;q=0.9")
        "en_US"
        >>> parse_accept_language(None)
        "zh_CN"
    """
    if not accept_language:
        return DEFAULT_LOCALE

    # Parse Accept-Language (format: "lang;q=priority,lang;q=priority")
    languages = []
    for part in accept_language.split(","):
        part = part.strip()
        if ";" in part:
            lang, q = part.split(";", 1)
            lang = lang.strip()
            q_value = 1.0
            if "q=" in q:
                try:
                    q_value = float(q.split("q=")[1].strip())
                except ValueError:
                    q_value = 1.0
            languages.append((lang, q_value))
        else:
            languages.append((part.strip(), 1.0))

    # Sort by priority
    languages.sort(key=lambda x: x[1], reverse=True)

    # Find matching language
    for lang, _ in languages:
        # Normalize locale code (zh-CN -> zh_CN)
        normalized = lang.replace("-", "_")

        # Full match
        if normalized in SUPPORTED_LOCALES:
            return normalized

        # Partial match (zh -> zh_CN, en -> en_US)
        lang_code = normalized.split("_")[0].lower()
        if lang_code == "zh":
            return "zh_CN"
        elif lang_code == "en":
            return "en_US"

    # Default language
    return DEFAULT_LOCALE
