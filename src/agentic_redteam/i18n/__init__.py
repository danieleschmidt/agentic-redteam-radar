"""
Internationalization (i18n) module for Agentic RedTeam Radar
Supporting global deployment with multi-language support
"""

import os
import json
from typing import Dict, Optional
from pathlib import Path


class I18nManager:
    """Manages internationalization for the scanner"""
    
    def __init__(self, default_locale: str = "en"):
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()
    
    def _load_translations(self):
        """Load translation files from locale directory"""
        locale_dir = Path(__file__).parent / "locales"
        if not locale_dir.exists():
            locale_dir.mkdir(exist_ok=True)
            
        for locale_file in locale_dir.glob("*.json"):
            locale = locale_file.stem
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self.translations[locale] = json.load(f)
            except Exception:
                # Fallback to empty dict if loading fails
                self.translations[locale] = {}
    
    def set_locale(self, locale: str):
        """Set the current locale"""
        self.current_locale = locale
    
    def translate(self, key: str, **kwargs) -> str:
        """Translate a key to the current locale"""
        # Try current locale first
        translation = self.translations.get(self.current_locale, {}).get(key)
        
        # Fallback to default locale
        if not translation:
            translation = self.translations.get(self.default_locale, {}).get(key)
        
        # Fallback to key itself
        if not translation:
            translation = key
        
        # Format with provided arguments
        try:
            return translation.format(**kwargs)
        except (KeyError, ValueError):
            return translation
    
    def get_supported_locales(self) -> list:
        """Get list of supported locales"""
        return list(self.translations.keys())


# Global i18n instance
_i18n = I18nManager()

def t(key: str, **kwargs) -> str:
    """Shorthand for translation"""
    return _i18n.translate(key, **kwargs)

def set_locale(locale: str):
    """Set global locale"""
    _i18n.set_locale(locale)

def get_supported_locales() -> list:
    """Get supported locales"""
    return _i18n.get_supported_locales()