"""
CameraWidget - Виджет для отображения видеопотока с камеры

Отвечает за:
1. Отображение видео с камеры в QLabel
2. Конвертацию кадров OpenCV (BGR) в Qt формат (RGB)
3. Отображение overlay информации (статус руки, FPS, данные жестов)
4. Визуализацию landmarks рук через MediaPipe drawing utils
5. Placeholder когда камера выключена
6. Индикаторы зоны обнаружения и FPS
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QImage, QPixmap, QFont, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QTimer, QPoint
import cv2
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)


class CameraWidget(QWidget):
    """Виджет для отображения камеры и overlay информации"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Основной layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # QLabel для отображения кадров
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumSize(800, 600)  # Увеличен минимальный размер
        self.camera_label.setStyleSheet("""
            QLabel {
                background-color: #0a0a0f;
                border: 3px solid #2a2a35;
                border-radius: 12px;
            }
        """)
        self.layout.addWidget(self.camera_label)
        
        # Таймер обновления
        self.update_timer = None
        
        # Счётчик FPS
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.current_fps = 0
        
        # Флаг активности камеры
        self.is_camera_active = False
        
        logger.info("CameraWidget инициализирован с улучшенным UI")
    
    def start_updates(self, interval_ms: int = 33):
        """
        Запуск автоматического обновления кадров
        
        Args:
            interval_ms: Интервал обновления в миллисекундах (33ms ≈ 30 FPS)
        """
        if not self.update_timer:
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._on_update_timeout)
        
        self.update_timer.start(interval_ms)
        self.is_camera_active = True
        logger.info(f"Обновление камеры запущено (интервал: {interval_ms}мс)")
    
    def stop_updates(self):
        """Остановка обновления кадров"""
        if self.update_timer and self.update_timer.isActive():
            self.update_timer.stop()
        self.is_camera_active = False
        self.show_placeholder()
        logger.info("Обновление камеры остановлено")
    
    def _on_update_timeout(self):
        """Обработчик таймера обновления (вызывается родительским классом)"""
        pass
    
    def show_placeholder(self):
        """Показать placeholder когда камера выключена"""
        # Создаем изображение placeholder
        width = self.camera_label.width() if self.camera_label.width() > 0 else 640
        height = self.camera_label.height() if self.camera_label.height() > 0 else 480
        
        placeholder = np.zeros((height, width, 3), dtype=np.uint8)
        placeholder[:] = (15, 15, 20)  # Темный фон
        
        # Рисуем иконку камеры (упрощенно - круг с точкой)
        center_x, center_y = width // 2, height // 2
        
        # Внешний круг (корпус камеры)
        cv2.circle(placeholder, (center_x, center_y), 60, (60, 60, 70), 4)
        
        # Внутренний круг (объектив)
        cv2.circle(placeholder, (center_x, center_y), 35, (40, 40, 50), -1)
        
        # Точка в центре (линза)
        cv2.circle(placeholder, (center_x, center_y), 15, (80, 80, 100), -1)
        
        # Текст под иконкой
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(placeholder, "КАМЕРА ВЫКЛЮЧЕНА", (center_x - 140, center_y + 100),
                   font, 0.7, (100, 100, 120), 2, cv2.LINE_AA)
        cv2.putText(placeholder, "Нажмите 'Запустить камеру'", (center_x - 150, center_y + 130),
                   font, 0.5, (80, 80, 100), 1, cv2.LINE_AA)
        
        # Рамка зоны обнаружения (пунктирная)
        margin = 40
        pts = [
            (margin, margin),
            (width - margin, margin),
            (width - margin, height - margin),
            (margin, height - margin),
            (margin, margin)
        ]
        for i in range(len(pts) - 1):
            cv2.line(placeholder, pts[i], pts[i+1], (40, 40, 50), 2, cv2.LINE_AA)
        
        # Угловые маркеры
        corner_size = 20
        corners = [
            (margin, margin),
            (width - margin, margin),
            (width - margin, height - margin),
            (margin, height - margin)
        ]
        for corner in corners:
            cv2.drawMarker(placeholder, corner, (60, 60, 80), cv2.MARKER_TILTED_CROSS, 
                          corner_size, 2, cv2.LINE_AA)
        
        self._display_image(placeholder)
    
    def update_frame(self, frame: np.ndarray, hands_data: list = None):
        """
        Обновление кадра с камеры
        
        Args:
            frame: Кадр от OpenCV (BGR формат)
            hands_data: Данные рук для overlay (опционально)
        """
        if frame is None:
            return
        
        # Обновляем счётчик FPS
        self.frame_count += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.current_fps = self.frame_count
            self.frame_count = 0
            self.last_fps_time = current_time
        
        # Если есть данные рук, добавляем overlay информацию
        if hands_data:
            frame = self._draw_overlay(frame, hands_data)
        
        # Рисуем рамку зоны обнаружения
        frame = self._draw_detection_zone(frame)
        
        # Отображаем кадр
        self._display_image(frame)
    
    def _draw_detection_zone(self, frame: np.ndarray) -> np.ndarray:
        """Рисование рамки зоны обнаружения рук"""
        height, width = frame.shape[:2]
        margin = 30
        
        # Полупрозрачная рамка
        overlay = frame.copy()
        
        # Линии рамки
        cv2.rectangle(overlay, (margin, margin), 
                     (width - margin, height - margin),
                     (0, 150, 255), 2, cv2.LINE_AA)
        
        # Угловые маркеры
        corner_size = 25
        corners = [
            (margin, margin),
            (width - margin, margin),
            (width - margin, height - margin),
            (margin, height - margin)
        ]
        for corner in corners:
            cv2.drawMarker(overlay, corner, (0, 200, 255), cv2.MARKER_TILTED_CROSS, 
                          corner_size, 3, cv2.LINE_AA)
        
        # Применяем полупрозрачность
        alpha = 0.3
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        return frame
    
    def _draw_overlay(self, frame: np.ndarray, hands_data: list) -> np.ndarray:
        """
        Рисование overlay информации на кадре
        
        Args:
            frame: Исходный кадр
            hands_data: Список данных рук
            
        Returns:
            Кадр с overlay информацией
        """
        overlay = frame.copy()
        
        # Параметры текста
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        # Позиция для текста
        y_offset = 35
        
        # === Верхняя панель: статус и FPS ===
        # Фон для верхней панели
        panel_height = 65
        cv2.rectangle(overlay, (0, 0), (380, panel_height), (20, 20, 25), -1)
        cv2.rectangle(overlay, (0, 0), (380, panel_height), (50, 50, 60), 2)
        
        # Заголовок с количеством рук
        num_hands = len(hands_data)
        title_text = f"🖐️ РУКИ: {num_hands}"
        cv2.putText(overlay, title_text, (15, 28), font, 0.7, 
                   (0, 255, 100), 2, cv2.LINE_AA)
        
        # Индикатор FPS
        fps_color = (0, 255, 0) if self.current_fps >= 25 else (0, 200, 255) if self.current_fps >= 15 else (0, 100, 255)
        fps_text = f"FPS: {self.current_fps}"
        cv2.putText(overlay, fps_text, (200, 28), font, 0.6, 
                   fps_color, 2, cv2.LINE_AA)
        
        # Индикатор активности (мигающая точка)
        indicator_x = 350
        indicator_y = 20
        cv2.circle(overlay, (indicator_x, indicator_y), 8, (0, 255, 0), -1)
        cv2.circle(overlay, (indicator_x, indicator_y), 8, (0, 200, 0), 2)
        
        y_offset = panel_height + 15
        
        # Информация о каждой руке
        for i, hand_data in enumerate(hands_data):
            handedness = hand_data.get('handedness', 'Unknown')
            pinch = hand_data.get('pinch_distance', 0.0)
            palm_x = hand_data.get('palm_x', 0.0)
            palm_y = hand_data.get('palm_y', 0.0)
            open_palm = hand_data.get('open_palm', False)
            ok_gesture = hand_data.get('ok_gesture', False)
            depth = hand_data.get('depth', 0.5)
            
            # Цвет в зависимости от руки
            color = (0, 255, 0) if handedness == 'Right' else (255, 100, 0)
            
            # Фон для блока руки
            block_height = 95 if ok_gesture or open_palm else 75
            cv2.rectangle(overlay, (8, y_offset - 15), (372, y_offset + block_height), 
                         (25, 25, 30), -1)
            cv2.rectangle(overlay, (8, y_offset - 15), (372, y_offset + block_height), 
                         color, 2)
            
            # Информация о руке
            hand_icon = "🔵" if handedness == 'Right' else "🟢"
            hand_info = f"{hand_icon} {handedness.upper()} #{i+1}"
            cv2.putText(overlay, hand_info, (15, y_offset + 5), font, font_scale * 0.9, 
                       color, 2, cv2.LINE_AA)
            
            y_offset += 28
            
            pinch_text = f"  Pinch: {pinch:.2f}"
            cv2.putText(overlay, pinch_text, (15, y_offset), font, font_scale * 0.7, 
                       (220, 220, 220), 1, cv2.LINE_AA)
            
            y_offset += 22
            
            pos_text = f"  Pos: ({palm_x:+.2f}, {palm_y:+.2f})"
            cv2.putText(overlay, pos_text, (15, y_offset), font, font_scale * 0.7, 
                       (200, 200, 200), 1, cv2.LINE_AA)
            
            y_offset += 22
            
            # Статус жеста OK и глубины
            if ok_gesture:
                zoom_status = "ZOOM IN" if depth > 0.6 else "ZOOM OUT" if depth < 0.4 else "NEUTRAL"
                zoom_color = (0, 255, 150) if depth > 0.6 else (0, 200, 255) if depth < 0.4 else (150, 150, 150)
                status_text = f"  👌 {zoom_status} ({depth:.2f})"
                cv2.putText(overlay, status_text, (15, y_offset), font, font_scale * 0.75, 
                           zoom_color, 2, cv2.LINE_AA)
            elif open_palm:
                status_text = "  ✋ STOP ALL"
                cv2.putText(overlay, status_text, (15, y_offset), font, font_scale * 0.75, 
                           (0, 150, 255), 2, cv2.LINE_AA)
            else:
                status_text = "  🔄 ROTATION"
                cv2.putText(overlay, status_text, (15, y_offset), font, font_scale * 0.65, 
                           (180, 180, 180), 1, cv2.LINE_AA)
            
            y_offset += 40
        
        return overlay
    
    def _display_image(self, frame: np.ndarray):
        """
        Конвертация и отображение изображения
        
        Args:
            frame: Кадр в формате BGR (OpenCV)
        """
        # Конвертируем BGR -> RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Получаем размеры
        height, width, channel = rgb_frame.shape
        
        # Создаем QImage
        bytes_per_line = 3 * width
        q_image = QImage(rgb_frame.data, width, height, bytes_per_line, 
                        QImage.Format.Format_RGB888)
        
        # Конвертируем в QPixmap и отображаем
        pixmap = QPixmap.fromImage(q_image)
        
        # Масштабируем с сохранением пропорций
        scaled_pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.camera_label.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """Обработка изменения размера виджета"""
        super().resizeEvent(event)
        if not self.is_camera_active:
            self.show_placeholder()
    
    def closeEvent(self, event):
        """Обработка закрытия виджета"""
        self.stop_updates()
        super().closeEvent(event)
