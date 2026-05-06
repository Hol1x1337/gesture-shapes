"""
Настройки приложения Hand Gesture 3D
Централизованное управление всеми параметрами
"""
import json
import os
from pathlib import Path


class AppSettings:
    """Класс для управления настройками приложения"""
    
    def __init__(self):
        self.config_file = Path(__file__).parent.parent / 'settings.json'
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Загрузка настроек из файла или создание дефолтных"""
        default_settings = {
            # === ВИЗУАЛЬНЫЕ НАСТРОЙКИ ===
            "visual": {
                "theme": "dark",
                "show_grid": True,
                "show_axes": False,
                "shadow_enabled": False,
                "reflection_enabled": False,
                "particle_effects": False,
                "glow_effect": True,
            },
            
            # === КАМЕРА ===
            "camera": {
                "mode": "fixed",
                "distance": 9.0,
                "fov": 45.0,
                "auto_rotate": False,
                "auto_rotate_speed": 0.5,
            },
            
            # === ЧУВСТВИТЕЛЬНОСТЬ ЖЕСТОВ ===
            "gestures": {
                "rotation_speed": 3.0,
                "dead_zone": 0.1,
                "pinch_threshold": 0.5,
                "scale_sensitivity": 2.0,
                "smoothing_factor": 0.15,
            },
            
            # === МАТЕРИАЛЫ И ЦВЕТА ===
            "material": {
                "type": "standard",
                "color_scheme": "blue",
                "custom_color": [0.4, 0.5, 0.95],
                "transparency": 0.0,
                "shininess": 80.0,
            },
            
            # === ОБЪЕКТ ===
            "object": {
                "type": "cube",
                "size": 0.3,
                "auto_rotate": False,
                "auto_rotate_speed": 1.0,
            },
            
            # === ПРОИЗВОДИТЕЛЬНОСТЬ ===
            "performance": {
                "fps_limit": 60,
                "render_quality": "high",
                "use_vsync": True,
                "optimize_hand_tracking": True,
                "cpu_threads": 4,  # Количество потоков CPU для обработки
                "use_cpu_for_tracking": True,  # Использовать CPU для MediaPipe
                "use_gpu_for_rendering": True,  # Использовать GPU для OpenGL
                "frame_buffer_size": 3,  # Размер буфера кадров
            },
            
            # === ДОСТУПНОСТЬ ===
            "accessibility": {
                "keyboard_controls": True,
                "high_contrast": False,
                "ui_scale": 1.0,
                "sound_feedback": False,
            },
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    return self._merge_settings(default_settings, loaded)
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
        
        return default_settings
    
    def _merge_settings(self, default, loaded):
        """Рекурсивное объединение настроек"""
        merged = default.copy()
        for key, value in loaded.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_settings(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def save(self):
        """Сохранение настроек в файл"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            return False
    
    def get(self, category, key, default=None):
        """Получение значения настройки"""
        return self.settings.get(category, {}).get(key, default)
    
    def set(self, category, key, value):
        """Установка значения настройки"""
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
        self.save()
    
    def reset_to_defaults(self):
        """Сброс к настройкам по умолчанию"""
        self.settings = self._load_settings.__func__(self)
        self.save()


# Глобальный экземпляр настроек
app_settings = AppSettings()
