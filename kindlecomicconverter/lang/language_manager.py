# -*- coding: utf-8 -*-

from . import tr

class LanguageManager:
    def __init__(self):
        self.current_language = "en"  # Varsayılan dil İngilizce
        self.translations = {
            "tr": tr.translations
        }
    
    def set_language(self, lang_code):
        """Dili değiştirir"""
        if lang_code in self.translations or lang_code == "en":
            self.current_language = lang_code
            return True
        return False
    
    def get_text(self, text):
        """Verilen metni mevcut dile çevirir"""
        if self.current_language == "en":
            return text  # İngilizce için orijinal metni döndür
        
        translations = self.translations.get(self.current_language, {})
        translated_text = translations.get(text)
        
        # Eğer çeviri bulunamazsa orijinal metni döndür
        if translated_text is None:
            return text
            
        return translated_text
    
    def get_available_languages(self):
        """Kullanılabilir dilleri döndürür"""
        return {
            "en": "English",
            "tr": "Türkçe"
        } 