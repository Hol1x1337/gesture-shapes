"""
Расширенное распознавание жестов
Дополнительные жесты помимо базовых
"""
import numpy as np
from typing import Dict, List


class AdvancedGestures:
    """Класс для распознавания дополнительных жестов"""
    
    @staticmethod
    def detect_fist(landmarks: np.ndarray) -> bool:
        """
        Обнаружение жеста "кулак"
        Все пальцы согнуты к ладони
        """
        # Кончики пальцев
        fingertips = [4, 8, 12, 16, 20]
        # Основания пальцев (MCP)
        finger_bases = [2, 5, 9, 13, 17]
        
        bent_fingers = 0
        for tip_idx, base_idx in zip(fingertips, finger_bases):
            tip = landmarks[tip_idx][:2]
            base = landmarks[base_idx][:2]
            
            # Проверяем расстояние от кончика до основания запястья
            wrist = landmarks[0][:2]
            dist_tip_wrist = np.linalg.norm(tip - wrist)
            dist_base_wrist = np.linalg.norm(base - wrist)
            
            # Если кончик ближе к запястью чем основание - палец согнут
            if dist_tip_wrist < dist_base_wrist * 0.9:
                bent_fingers += 1
        
        # Кулак если 4+ пальца согнуты
        return bent_fingers >= 4
    
    @staticmethod
    def detect_pointing_up(landmarks: np.ndarray) -> bool:
        """
        Обнаружение жеста "указательный палец вверх"
        Только указательный палец выпрямлен, остальные согнуты
        """
        # Указательный палец должен быть выпрямлен
        index_tip = landmarks[8][1]
        index_base = landmarks[5][1]
        index_extended = index_tip < index_base  # Y инвертирован
        
        # Остальные пальцы должны быть согнуты
        middle_tip = landmarks[12][1]
        middle_base = landmarks[9][1]
        middle_bent = middle_tip > middle_base
        
        ring_tip = landmarks[16][1]
        ring_base = landmarks[13][1]
        ring_bent = ring_tip > ring_base
        
        pinky_tip = landmarks[20][1]
        pinky_base = landmarks[17][1]
        pinky_bent = pinky_tip > pinky_base
        
        return index_extended and middle_bent and ring_bent and pinky_bent
    
    @staticmethod
    def detect_victory(landmarks: np.ndarray) -> bool:
        """
        Обнаружение жеста "победа" (V)
        Указательный и средний пальцы выпрямлены, остальные согнуты
        """
        # Указательный и средний выпрямлены
        index_tip = landmarks[8][1]
        index_base = landmarks[5][1]
        index_extended = index_tip < index_base
        
        middle_tip = landmarks[12][1]
        middle_base = landmarks[9][1]
        middle_extended = middle_tip < middle_base
        
        # Безымянный и мизинец согнуты
        ring_tip = landmarks[16][1]
        ring_base = landmarks[13][1]
        ring_bent = ring_tip > ring_base
        
        pinky_tip = landmarks[20][1]
        pinky_base = landmarks[17][1]
        pinky_bent = pinky_tip > pinky_base
        
        return index_extended and middle_extended and ring_bent and pinky_bent
    
    @staticmethod
    def detect_heart(landmarks: np.ndarray) -> bool:
        """
        Обнаружение жеста "сердце"
        Большой и указательный образуют форму сердца с другими пальцами
        Упрощенная версия: большой и указательный близко, остальные выпрямлены
        """
        thumb_tip = landmarks[4][:2]
        index_tip = landmarks[8][:2]
        
        # Большой и указательный близко друг к другу
        distance = np.linalg.norm(thumb_tip - index_tip)
        close_fingers = distance < 0.1
        
        # Остальные пальцы выпрямлены
        middle_tip = landmarks[12][1]
        middle_base = landmarks[9][1]
        middle_extended = middle_tip < middle_base
        
        ring_tip = landmarks[16][1]
        ring_base = landmarks[13][1]
        ring_extended = ring_tip < ring_base
        
        pinky_tip = landmarks[20][1]
        pinky_base = landmarks[17][1]
        pinky_extended = pinky_tip < pinky_base
        
        return close_fingers and middle_extended and ring_extended and pinky_extended
    
    @staticmethod
    def detect_all_gestures(landmarks: np.ndarray) -> Dict[str, bool]:
        """
        Распознавание всех дополнительных жестов
        
        Returns:
            Словарь с результатами обнаружения каждого жеста
        """
        return {
            'fist': AdvancedGestures.detect_fist(landmarks),
            'pointing_up': AdvancedGestures.detect_pointing_up(landmarks),
            'victory': AdvancedGestures.detect_victory(landmarks),
            'heart': AdvancedGestures.detect_heart(landmarks),
        }
