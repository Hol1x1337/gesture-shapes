"""
HandTracker - Компонент отслеживания руки через MediaPipe Hands

Отвечает за:
1. Инициализацию камеры и MediaPipe
2. Обнаружение 21 точки руки в реальном времени (до 2 рук)
3. Вычисление жеста pinch (расстояние между большим и указательным пальцами)
4. Нормализацию координат ладони для управления 3D объектом
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, Dict, List
import logging
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)

# Добавляем путь к config для импорта advanced_gestures
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.advanced_gestures import AdvancedGestures


class HandTracker:
    """Класс для отслеживания руки и вычисления жестов с оптимизацией для CPU"""
    
    def __init__(self, camera_id: int = 0):
        """
        Инициализация трекера руки
        
        Args:
            camera_id: ID камеры (0 - основная камера)
        """
        self.camera_id = camera_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.hands = None
        self.mp_drawing = None
        self.mp_hands = None
        
        # Параметры отслеживания
        self.is_running = False
        self.current_frame: Optional[np.ndarray] = None
        
        # Поддержка двух рук
        self.hands_data: List[Dict] = []  # Данные для каждой руки
        self.max_hands = 2  # Максимум 2 руки
        
        # Многопоточность для CPU
        self.thread_pool = ThreadPoolExecutor(max_workers=4)  # Используем 4 потока CPU
        self.frame_lock = threading.Lock()
        self.processing_queue = []
        
        logger.info("HandTracker инициализирован с оптимизацией для мощного CPU")
    
    def initialize(self) -> bool:
        """
        Инициализация камеры и MediaPipe Hands с оптимизацией для CPU
        
        Returns:
            True если инициализация успешна
        """
        try:
            # Инициализация MediaPipe Hands с оптимизацией для мощного CPU
            self.mp_hands = mp.solutions.hands
            self.mp_drawing = mp.solutions.drawing_utils
            
            # Явно указываем использование CPU (так как он мощнее GPU)
            import os
            os.environ['MEDIAPIPE_DISABLE_GPU'] = '1'  # Принудительное использование CPU
            
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=self.max_hands,  # Поддержка 2 рук
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
                model_complexity=1,  # Full режим для лучшего качества на мощном CPU
            )
            
            # Инициализация камеры
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                logger.error(f"Не удалось открыть камеру {self.camera_id}")
                return False
            
            # Настройка параметров камеры для улучшенного качества
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # Увеличено до HD
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            logger.info("Камера и MediaPipe успешно инициализированы (1280x720 HD)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}", exc_info=True)
            return False
    
    def start(self) -> bool:
        """Запуск отслеживания"""
        if not self.is_running:
            if not self.hands:
                if not self.initialize():
                    return False
            self.is_running = True
            logger.info("Отслеживание руки запущено")
        return True
    
    def stop(self):
        """Остановка отслеживания"""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.hands:
            self.hands.close()
            self.hands = None
        self.hands_data = []
        logger.info("Отслеживание руки остановлено")
    
    def process_frame(self) -> Optional[np.ndarray]:
        """
        Обработка одного кадра с камеры (оптимизировано для мощного CPU)
        
        Returns:
            Обработанный кадр с визуализацией или None
        """
        if not self.is_running or not self.cap:
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Не удалось прочитать кадр с камеры")
            return None
        
        # Переворачиваем кадр для зеркального отображения
        frame = cv2.flip(frame, 1)
        
        # Конвертируем в RGB для MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Обрабатываем кадр через MediaPipe (использует CPU благодаря MEDIAPIPE_DISABLE_GPU=1)
        results = self.hands.process(rgb_frame)
        
        # Сбрасываем данные рук
        self.hands_data = []
        
        # Если руки обнаружены
        if results.multi_hand_landmarks:
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Извлекаем координаты 21 точки
                landmarks_array = np.zeros((21, 3))
                for i, landmark in enumerate(hand_landmarks.landmark):
                    landmarks_array[i] = [landmark.x, landmark.y, landmark.z]
                
                # Вычисляем жесты для этой руки
                gesture_data = self._calculate_gestures(landmarks_array, hand_idx)
                gesture_data['hand_index'] = hand_idx
                
                # Определяем левую/правую руку
                if results.multi_handedness:
                    handedness = results.multi_handedness[hand_idx].classification[0].label
                    gesture_data['handedness'] = handedness  # 'Left' или 'Right'
                
                self.hands_data.append(gesture_data)
                
                # Визуализируем точки руки на кадре с разными цветами
                color = (0, 255, 0) if hand_idx == 0 else (255, 0, 0)  # Зеленый/Синий
                self.mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing.DrawingSpec(color=color, thickness=2, circle_radius=4),
                    self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2)
                )
        
        self.current_frame = frame
        return frame
    
    def _calculate_gestures(self, landmarks: np.ndarray, hand_idx: int) -> Dict:
        """
        Вычисление жестов на основе координат точек руки
        
        Args:
            landmarks: Массив координат 21 точки
            hand_idx: Индекс руки (0 или 1)
            
        Returns:
            Словарь с данными жестов
        """
        # 1. Вычисление pinch жеста (расстояние между большим и указательным пальцами)
        # Landmark 4 - кончик большого пальца
        # Landmark 8 - кончик указательного пальца
        thumb_tip = landmarks[4][:2]  # x, y
        index_tip = landmarks[8][:2]  # x, y
        
        # Евклидово расстояние
        distance = np.linalg.norm(thumb_tip - index_tip)
        
        # Нормализуем расстояние (типичный диапазон 0.02-0.2)
        # Маппинг в диапазон 0-1 где 0 = пальцы вместе, 1 = пальцы далеко
        pinch_distance = np.clip((distance - 0.02) / 0.15, 0.0, 1.0)
        
        # 2. Обнаружение жеста "OK" (кончики большого и указательного почти касаются)
        ok_gesture = distance < 0.05  # Порог для жеста OK
        
        # 3. Вычисление глубины руки (приближение/отдаление от камеры)
        # Используем среднюю Z координату ключевых точек
        depth_points = [
            landmarks[0],   # Запястье
            landmarks[9],   # Центр ладони
            landmarks[5],   # Основание указательного
        ]
        avg_depth = np.mean([p[2] for p in depth_points])  # Среднее Z
        
        # Нормализация глубины (типичный диапазон -0.1 до 0.1)
        # Маппинг в удобный диапазон для управления zoom
        normalized_depth = np.clip((avg_depth + 0.1) / 0.2, 0.0, 1.0)
        
        # 4. Вычисление центра ладони
        palm_x = landmarks[9][0]
        palm_y = landmarks[9][1]
        
        # Нормализация координат в диапазон [-1, 1] для управления 3D объектом
        # X: 0 (слева) -> 1 (справа), маппим в -1 -> 1
        # Y: 0 (сверху) -> 1 (снизу), маппим в 1 -> -1 (инвертируем)
        normalized_x = (palm_x - 0.5) * 2  # Диапазон [-1, 1]
        normalized_y = (0.5 - palm_y) * 2  # Диапазон [-1, 1], инвертированный
        
        # 5. Обнаружение жеста "открытая ладонь" (open palm)
        # Проверяем, все ли пальцы выпрямлены
        open_palm = self._detect_open_palm(landmarks)
        
        # 6. Распознавание расширенных жестов
        advanced = AdvancedGestures.detect_all_gestures(landmarks)
        
        return {
            'hand_detected': True,
            'pinch_distance': pinch_distance,
            'ok_gesture': ok_gesture,  # Жест OK
            'depth': normalized_depth,  # Глубина (приближение/отдаление)
            'palm_x': normalized_x,
            'palm_y': normalized_y,
            'open_palm': open_palm,  # Флаг открытой ладони
            'landmarks': landmarks.copy(),
            # Расширенные жесты
            'fist': advanced['fist'],
            'pointing_up': advanced['pointing_up'],
            'victory': advanced['victory'],
            'heart': advanced['heart'],
        }
    
    def _detect_open_palm(self, landmarks: np.ndarray) -> bool:
        """
        Обнаружение жеста "открытая ладонь"
        
        Проверяет, все ли пальцы выпрямлены (кончики выше оснований пальцев)
        
        Args:
            landmarks: Массив координат 21 точки
            
        Returns:
            True если ладонь открыта
        """
        # Кончики пальцев (tip)
        fingertips = [
            landmarks[4],   # Большой палец
            landmarks[8],   # Указательный
            landmarks[12],  # Средний
            landmarks[16],  # Безымянный
            landmarks[20]   # Мизинец
        ]
        
        # Основания пальцев (MCP joints)
        finger_bases = [
            landmarks[2],   # Большой палец
            landmarks[5],   # Указательный
            landmarks[9],   # Средний
            landmarks[13],  # Безымянный
            landmarks[17]   # Мизинец
        ]
        
        # Запястье как точка отсчета
        wrist = landmarks[0]
        
        # Проверяем каждый палец
        extended_fingers = 0
        for tip, base in zip(fingertips, finger_bases):
            # Для всех пальцев кроме большого: кончик должен быть выше основания
            # (меньше Y координата = выше на экране)
            if tip[1] < base[1]:  # Y инвертирован в MediaPipe
                extended_fingers += 1
            elif tip[0] > base[0]:  # Для большого пальца проверяем горизонтальное положение
                extended_fingers += 1
        
        # Если 4 или 5 пальцев выпрямлены - считаем ладонь открытой
        is_open = extended_fingers >= 4
        
        return is_open
    
    def get_gesture_data(self) -> List[Dict]:
        """
        Получение текущих данных жестов для всех рук
        
        Returns:
            Список словарей с данными жестов (максимум 2)
        """
        return self.hands_data
    
    def __del__(self):
        """Деструктор - освобождение ресурсов"""
        self.stop()
        # Очищаем пул потоков
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)
