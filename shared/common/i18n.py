"""
国际化 (i18n) 模块

提供多语言消息支持，支持从请求头 Accept-Language 自动检测语言偏好。
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

# 默认语言
DEFAULT_LOCALE = "zh_CN"

# 支持的语言列表
SUPPORTED_LOCALES = ["zh_CN", "en_US"]


class I18nManager:
    """国际化管理器

    管理多语言翻译资源，支持动态加载和缓存。
    """

    def __init__(self, locales_dir: Optional[str] = None):
        """初始化国际化管理器

        Args:
            locales_dir: 语言文件目录路径，如果为 None 则自动检测
        """
        if locales_dir is None:
            # 自动检测语言文件目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            locales_dir = str(project_root / "shared" / "locales")

        self.locales_dir = Path(locales_dir)
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self) -> None:
        """加载所有语言文件"""
        if not self.locales_dir.exists():
            logger.warning(f"语言文件目录不存在: {self.locales_dir}")
            return

        for locale in SUPPORTED_LOCALES:
            locale_file = self.locales_dir / f"{locale}.json"
            if locale_file.exists():
                try:
                    with open(locale_file, "r", encoding="utf-8") as f:
                        self._translations[locale] = json.load(f)
                    logger.info(f"已加载语言文件: {locale} ({len(self._translations[locale])} 条翻译)")
                except Exception as e:
                    logger.error(f"加载语言文件失败: {locale_file}, 错误: {str(e)}")
            else:
                logger.warning(f"语言文件不存在: {locale_file}")

    def translate(
        self, key: str, locale: Optional[str] = None, default: Optional[str] = None, **kwargs: Any
    ) -> str:
        """翻译消息键

        Args:
            key: 翻译键（支持点号分隔的嵌套键，如 "error.host.not_found"）
            locale: 语言代码（如 "zh_CN", "en_US"），如果为 None 则使用默认语言
            default: 默认消息（如果键不存在时使用），如果为 None 则返回键本身
            **kwargs: 用于格式化消息的变量（如 name="test" 会替换 {name}）

        Returns:
            翻译后的消息

        Examples:
            >>> i18n = I18nManager()
            >>> i18n.translate("success.operation", locale="zh_CN")
            "操作成功"
            >>> i18n.translate("error.host.not_found", locale="en_US", host_id="123")
            "Host not found: 123"
        """
        if locale is None:
            locale = DEFAULT_LOCALE

        # 如果语言不存在，使用默认语言
        if locale not in self._translations:
            logger.debug(f"语言不存在: {locale}，使用默认语言: {DEFAULT_LOCALE}")
            locale = DEFAULT_LOCALE

        # 获取翻译
        translations = self._translations.get(locale, {})
        message = self._get_nested_value(translations, key)

        # 如果找不到翻译，使用默认值或键本身
        if message is None:
            if default is not None:
                message = default
            else:
                logger.warning(f"翻译键不存在: {key} (locale: {locale})")
                message = key

        # 格式化消息（支持 {variable} 占位符）
        if kwargs:
            try:
                message = message.format(**kwargs)
            except KeyError as e:
                logger.warning(f"格式化消息时缺少变量: {key}, 缺少: {e}")
                # 如果格式化失败，返回原始消息
            except Exception as e:
                logger.error(f"格式化消息失败: {key}, 错误: {str(e)}")

        return message

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[str]:
        """获取嵌套字典的值

        Args:
            data: 字典数据
            key: 键（支持点号分隔，如 "error.host.not_found"）

        Returns:
            值，如果不存在则返回 None
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
        """重新加载语言文件（用于开发环境热重载）"""
        self._translations.clear()
        self._load_translations()
        logger.info("语言文件已重新加载")


# 全局实例
_i18n_manager_instance: Optional[I18nManager] = None


def get_i18n_manager() -> I18nManager:
    """获取全局国际化管理器实例（单例模式）

    Returns:
        I18nManager 实例
    """
    global _i18n_manager_instance

    if _i18n_manager_instance is None:
        _i18n_manager_instance = I18nManager()

    return _i18n_manager_instance


def t(key: str, locale: Optional[str] = None, default: Optional[str] = None, **kwargs: Any) -> str:
    """翻译快捷函数

    Args:
        key: 翻译键
        locale: 语言代码
        default: 默认消息
        **kwargs: 格式化变量

    Returns:
        翻译后的消息

    Example:
        >>> t("success.operation", locale="en_US")
        "Operation successful"
    """
    return get_i18n_manager().translate(key, locale=locale, default=default, **kwargs)


def parse_accept_language(accept_language: Optional[str]) -> str:
    """解析 Accept-Language 请求头，返回最佳匹配的语言代码

    Args:
        accept_language: Accept-Language 请求头值（如 "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7"）

    Returns:
        语言代码（如 "zh_CN", "en_US"），如果无法解析则返回默认语言

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

    # 解析 Accept-Language（格式: "lang;q=priority,lang;q=priority"）
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

    # 按优先级排序
    languages.sort(key=lambda x: x[1], reverse=True)

    # 查找匹配的语言
    for lang, _ in languages:
        # 标准化语言代码（zh-CN -> zh_CN）
        normalized = lang.replace("-", "_")
        
        # 完整匹配
        if normalized in SUPPORTED_LOCALES:
            return normalized
        
        # 部分匹配（zh -> zh_CN, en -> en_US）
        lang_code = normalized.split("_")[0].lower()
        if lang_code == "zh":
            return "zh_CN"
        elif lang_code == "en":
            return "en_US"

    # 默认语言
    return DEFAULT_LOCALE

