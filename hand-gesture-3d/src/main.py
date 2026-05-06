"""
Hand Gesture 3D Control - Главное приложение

Приложение для управления 3D-объектом через жесты руки в реальном времени.
Использует MediaPipe Hands для отслеживания 21 точки руки и OpenGL для рендеринга.

Поддерживает до 2 рук одновременно!
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QSplitter,
                             QGroupBox, QFrame, QComboBox, QGridLayout, QDialog,
                             QSlider, QCheckBox, QColorDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QKeySequence, QShortcut, QColor

# Добавляем путь к компонентам
sys.path.insert(0, str(Path(__file__).parent))

from components.hand_tracker import HandTracker
from components.gl_widget import GLWidget


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        
        # Настройка окна
        self.setWindowTitle("🖐️ Hand Gesture 3D Control v3.0 | Управление жестами")
        self.setMinimumSize(1800, 1100)
        self.resize(2200, 1300)  # Размер по умолчанию - максимальный
        
        # Применяем современную темную тему
        self._setup_stylesheet()
        
        # Инициализация компонентов
        self.hand_tracker = HandTracker(camera_id=0)
        self.gl_widget = GLWidget()
        
        # Состояние камеры
        self.is_active = False
        
        # Таймер обработки кадров (~30 FPS)
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_frame)
        
        # Статистика производительности
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = datetime.now()
        
        # Состояния полноэкранного режима и презентации
        self.is_fullscreen = False
        self.is_presentation_mode = False
        self.normal_geometry = None  # Сохранение обычного размера окна
        
        # Создание UI
        self._setup_ui()
        
        # Настройка горячих клавиш
        self._setup_shortcuts()
        
        logger.info("Главное окно инициализировано")
    
    def _setup_stylesheet(self):
        """Настройка профессиональной темы приложения для GitHub"""
        stylesheet = """
            QMainWindow {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #0f0f1a, stop:1 #1a1a2e);
            }
            
            QWidget {
                background-color: transparent;
                color: #e8e8f0;
                font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
                font-size: 13px;
            }
            
            QGroupBox {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 rgba(25, 25, 45, 0.9), 
                                    stop:1 rgba(35, 35, 60, 0.85));
                border: 2px solid qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #4a4a6a, stop:0.5 #6a6a8a, stop:1 #4a4a6a);
                border-radius: 15px;
                margin-top: 20px;
                padding-top: 20px;
                font-weight: bold;
                font-size: 15px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 12px;
                color: #7c8aff;
                font-size: 17px;
                background-color: rgba(15, 15, 30, 0.8);
                border-radius: 8px;
            }
            
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #3a3a5a, stop:1 #2a2a45);
                border: 2px solid #5a5a7a;
                border-radius: 12px;
                padding: 16px 32px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                min-height: 48px;
                min-width: 150px;
            }
            
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #4a4a6a, stop:1 #3a3a55);
                border-color: #8b9aff;
            }
            
            QPushButton:pressed {
                background-color: #2a2a45;
                border-color: #6a6a8a;
            }
            
            QPushButton#startButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #10b981, stop:1 #059669);
                border: 2px solid #059669;
                color: #ffffff;
            }
            
            QPushButton#startButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #059669, stop:1 #047857);
                border-color: #047857;
            }
            
            QPushButton#stopButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #ef4444, stop:1 #dc2626);
                border: 2px solid #dc2626;
                color: #ffffff;
            }
            
            QPushButton#stopButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #dc2626, stop:1 #b91c1c);
                border-color: #b91c1c;
            }
            
            QPushButton#resetButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #6366f1, stop:1 #4f46e5);
                border: 2px solid #4f46e5;
                color: #ffffff;
                min-width: 150px;
            }
            
            QPushButton#resetButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #4f46e5, stop:1 #4338ca);
                border-color: #4338ca;
            }
            
            QPushButton#fullscreenButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #8b5cf6, stop:1 #7c3aed);
                border: 2px solid #7c3aed;
                color: #ffffff;
            }
            
            QPushButton#fullscreenButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #7c3aed, stop:1 #6d28d9);
                border-color: #6d28d9;
            }
            
            QPushButton#presentationButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #ec4899, stop:1 #db2777);
                border: 2px solid #db2777;
                color: #ffffff;
            }
            
            QPushButton#presentationButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #db2777, stop:1 #be185d);
                border-color: #be185d;
            }
            
            QPushButton#customizeButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #f59e0b, stop:1 #d97706);
                border: 2px solid #d97706;
                color: #ffffff;
            }
            
            QPushButton#customizeButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #d97706, stop:1 #b45309);
                border-color: #b45309;
            }
            
            QLabel {
                color: #e8e8f0;
                background-color: transparent;
            }
            
            QLabel#infoLabel {
                color: #a8a8c0;
                font-size: 13px;
                line-height: 1.8;
            }
            
            QLabel#statusActive {
                color: #10b981;
                background-color: rgba(16, 185, 129, 0.1);
                border: 2px solid #10b981;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            
            QLabel#statusInactive {
                color: #ef4444;
                background-color: rgba(239, 68, 68, 0.1);
                border: 2px solid #ef4444;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 16px;
                font-weight: bold;
            }
            
            QComboBox {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2a2a45, stop:1 #1a1a30);
                border: 2px solid #4a4a6a;
                border-radius: 10px;
                padding: 8px 15px;
                color: #ffffff;
                font-size: 13px;
                min-width: 120px;
                min-height: 38px;
            }
            
            QComboBox:hover {
                border-color: #7c8aff;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #1a1a30;
                color: #ffffff;
                selection-background-color: #6366f1;
                border: 2px solid #4a4a6a;
                border-radius: 8px;
            }
            
            QFrame#separator {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 transparent, 
                                    stop:0.5 qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #4a4a6a, stop:1 #6a6a8a),
                                    stop:1 transparent);
                max-height: 3px;
            }
            
            QToolTip {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #2a2a45, stop:1 #1a1a30);
                color: #ffffff;
                border: 2px solid #5a5a7a;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 12px;
            }
        """
        self.setStyleSheet(stylesheet)
    
    def _setup_ui(self):
        """Создание пользовательского интерфейса"""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # === ВЕРХНЯЯ ЧАСТЬ - 3D ВИД (занимает все доступное место) ===
        view3d_group = QGroupBox("🎲 3D Вид с отслеживанием рук")
        view3d_layout = QVBoxLayout(view3d_group)
        view3d_layout.setContentsMargins(8, 8, 8, 8)
        
        # Увеличиваем минимальный размер 3D виджета
        self.gl_widget.setMinimumSize(1400, 900)
        view3d_layout.addWidget(self.gl_widget)
        
        main_layout.addWidget(view3d_group, stretch=10)
        
        # === НИЖНЯЯ ПАНЕЛЬ - УПРАВЛЕНИЕ (компактная, без инструкций) ===
        control_panel = QWidget()
        control_panel.setMaximumHeight(120)  # Ещё меньше высота, так как убрали инструкции
        control_layout_main = QHBoxLayout(control_panel)
        control_layout_main.setContentsMargins(8, 8, 8, 8)
        control_layout_main.setSpacing(12)
        
        # --- Левая часть нижней панели: Кнопки управления ---
        buttons_group = QGroupBox("⚙️ Управление")
        buttons_layout = QVBoxLayout(buttons_group)
        buttons_layout.setContentsMargins(8, 8, 8, 8)
        buttons_layout.setSpacing(6)
        
        # Кнопки в горизонтальном layout
        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        
        self.start_button = QPushButton("▶")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self._toggle_camera)
        self.start_button.setToolTip("Включить камеру и начать отслеживание рук (Пробел)")
        self.start_button.setMinimumHeight(35)
        self.start_button.setMaximumWidth(50)
        button_row.addWidget(self.start_button)
        
        self.stop_button = QPushButton("")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._toggle_camera)
        self.stop_button.setToolTip("Выключить камеру и остановить отслеживание")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setMaximumWidth(50)
        button_row.addWidget(self.stop_button)
        
        self.reset_button = QPushButton("↺")
        self.reset_button.setObjectName("resetButton")
        self.reset_button.clicked.connect(self._reset_object)
        self.reset_button.setToolTip("Вернуть объект в исходное положение (R)")
        self.reset_button.setMinimumHeight(35)
        self.reset_button.setMaximumWidth(50)
        button_row.addWidget(self.reset_button)
        
        # Разделитель
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setStyleSheet("color: #4a4a6a;")
        button_row.addWidget(separator1)
        
        # Кнопка полноэкранного режима
        self.fullscreen_button = QPushButton("⛶")
        self.fullscreen_button.setObjectName("fullscreenButton")
        self.fullscreen_button.clicked.connect(self._toggle_fullscreen)
        self.fullscreen_button.setToolTip("Полноэкранный режим (F11)")
        self.fullscreen_button.setMinimumHeight(35)
        self.fullscreen_button.setMaximumWidth(50)
        button_row.addWidget(self.fullscreen_button)
        
        # Кнопка режима презентации
        self.presentation_button = QPushButton("📺")
        self.presentation_button.setObjectName("presentationButton")
        self.presentation_button.clicked.connect(self._toggle_presentation_mode)
        self.presentation_button.setToolTip("Режим презентации (P)")
        self.presentation_button.setMinimumHeight(35)
        self.presentation_button.setMaximumWidth(50)
        button_row.addWidget(self.presentation_button)
        
        # Разделитель
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet("color: #4a4a6a;")
        button_row.addWidget(separator2)
        
        # Кнопка настроек объекта
        self.object_settings_button = QPushButton("⚙")
        self.object_settings_button.setObjectName("customizeButton")
        self.object_settings_button.clicked.connect(self._open_object_settings)
        self.object_settings_button.setToolTip("Настройки 3D объекта")
        self.object_settings_button.setMinimumHeight(35)
        self.object_settings_button.setMaximumWidth(50)
        button_row.addWidget(self.object_settings_button)
        
        buttons_layout.addLayout(button_row)
        
        # Минималистичная строка с выбором объекта
        object_select_layout = QHBoxLayout()
        object_select_layout.setSpacing(6)
        
        object_label = QLabel("🎲")
        object_label.setStyleSheet("font-size: 16px;")
        object_select_layout.addWidget(object_label)
        
        self.object_combo = QComboBox()
        self.object_combo.addItems(["Куб", "Сфера", "Пирамида", "Тор", "Конус", "Цилиндр"])
        self.object_combo.setCurrentIndex(0)
        self.object_combo.currentIndexChanged.connect(self._on_object_type_changed)
        self.object_combo.setToolTip("Выберите тип 3D объекта")
        self.object_combo.setMinimumHeight(35)
        self.object_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a28;
                border: 2px solid #3a3a4a;
                border-radius: 6px;
                padding: 6px 10px;
                color: #ffffff;
                font-size: 12px;
                min-width: 100px;
            }
            QComboBox:hover {
                border-color: #7c8aff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a28;
                color: #ffffff;
                selection-background-color: #6366f1;
                border: 1px solid #3a3a4a;
            }
        """)
        object_select_layout.addWidget(self.object_combo)
        object_select_layout.addStretch()
        
        buttons_layout.addLayout(object_select_layout)
        
        control_layout_main.addWidget(buttons_group, stretch=1)
        
        # --- Центральная часть нижней панели: Статус и статистика ---
        status_group = QGroupBox("📊 Статус")
        status_layout = QVBoxLayout(status_group)
        status_layout.setContentsMargins(8, 8, 8, 8)
        status_layout.setSpacing(6)
        
        # Статус активности
        self.status_label = QLabel("● НЕАКТИВЕН")
        self.status_label.setObjectName("statusInactive")
        self.status_label.setStyleSheet("font-size: 14px; padding: 8px 12px; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.status_label)
        
        control_layout_main.addWidget(status_group, stretch=1)
        
        main_layout.addWidget(control_panel)
        
        # === FOOTER - Информация о проекте ===
        footer = QLabel("🚀 Hand Gesture 3D Control v3.0 | CPU-оптимизированная версия | Управление 3D объектами через жесты рук")
        footer.setStyleSheet("""
            QLabel {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 rgba(99, 102, 241, 0.1),
                                    stop:0.5 rgba(99, 102, 241, 0.15),
                                    stop:1 rgba(99, 102, 241, 0.1));
                border-top: 2px solid #6366f1;
                padding: 10px 20px;
                color: #a8a8c0;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer)
        
        logger.info("UI инициализирован")
    
    def _setup_shortcuts(self):
        """Настройка горячих клавиш для быстрого управления"""
        
        # F11 - Полноэкранный режим
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self._toggle_fullscreen)
        
        # Esc - Выход из полноэкранного режима / режима презентации
        escape_shortcut = QShortcut(QKeySequence("Escape"), self)
        escape_shortcut.activated.connect(self._exit_fullscreen_or_presentation)
        
        # Пробел - Запуск/остановка камеры
        space_shortcut = QShortcut(QKeySequence("Space"), self)
        space_shortcut.activated.connect(self._toggle_camera)
        
        # R - Сброс объекта
        reset_shortcut = QShortcut(QKeySequence("R"), self)
        reset_shortcut.activated.connect(self._reset_object)
        
        # P - Режим презентации
        presentation_shortcut = QShortcut(QKeySequence("P"), self)
        presentation_shortcut.activated.connect(self._toggle_presentation_mode)
        
        # Стрелки - Управление вращением (когда камера активна)
        left_shortcut = QShortcut(QKeySequence("Left"), self)
        left_shortcut.activated.connect(lambda: self._manual_rotate(-5, 0))
        
        right_shortcut = QShortcut(QKeySequence("Right"), self)
        right_shortcut.activated.connect(lambda: self._manual_rotate(5, 0))
        
        up_shortcut = QShortcut(QKeySequence("Up"), self)
        up_shortcut.activated.connect(lambda: self._manual_rotate(0, -5))
        
        down_shortcut = QShortcut(QKeySequence("Down"), self)
        down_shortcut.activated.connect(lambda: self._manual_rotate(0, 5))
        
        # +/- - Масштабирование
        zoom_in_shortcut = QShortcut(QKeySequence("+"), self)
        zoom_in_shortcut.activated.connect(lambda: self._manual_scale(0.1))
        
        zoom_out_shortcut = QShortcut(QKeySequence("-"), self)
        zoom_out_shortcut.activated.connect(lambda: self._manual_scale(-0.1))
        
        logger.info("Горячие клавиши настроены")
    
    def _toggle_fullscreen(self):
        """Переключение полноэкранного режима"""
        if not self.is_fullscreen:
            # Вход в полноэкранный режим
            self.normal_geometry = self.geometry()  # Сохраняем текущий размер
            self.showFullScreen()
            self.is_fullscreen = True
            logger.info("Полноэкранный режим включен")
        else:
            # Выход из полноэкранного режима
            self._exit_fullscreen()
    
    def _exit_fullscreen(self):
        """Выход из полноэкранного режима"""
        if self.normal_geometry:
            self.setGeometry(self.normal_geometry)
            self.showNormal()
            self.is_fullscreen = False
            logger.info("Полноэкранный режим выключен")
    
    def _exit_fullscreen_or_presentation(self):
        """Выход из полноэкранного режима или режима презентации по Escape"""
        if self.is_presentation_mode:
            self._toggle_presentation_mode()
        elif self.is_fullscreen:
            self._exit_fullscreen()
    
    def _toggle_presentation_mode(self):
        """Переключение режима презентации (полноэкранный + скрытые элементы управления)"""
        if not self.is_presentation_mode:
            # Вход в режим презентации
            self.normal_geometry = self.geometry()
            
            # Скрываем панель управления и футер
            for widget in self.findChildren(QWidget):
                if hasattr(widget, 'objectName'):
                    # Скрываем все группы кроме 3D вида
                    if isinstance(widget, QGroupBox) and "3D Вид" not in widget.title():
                        widget.setVisible(False)
            
            # Показываем только 3D вид на весь экран
            self.showFullScreen()
            self.is_presentation_mode = True
            self.is_fullscreen = True
            
            logger.info("Режим презентации включен")
        else:
            # Выход из режима презентации
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
                self.showNormal()
            
            # Показываем все элементы управления
            for widget in self.findChildren(QWidget):
                if isinstance(widget, QGroupBox):
                    widget.setVisible(True)
            
            self.is_presentation_mode = False
            self.is_fullscreen = False
            
            logger.info("Режим презентации выключен")
    
    def _manual_rotate(self, delta_x: float, delta_y: float):
        """Ручное вращение объекта с помощью клавиатуры"""
        if hasattr(self.gl_widget, 'rotation_x'):
            self.gl_widget.rotation_x += delta_y
            self.gl_widget.rotation_y += delta_x
            self.gl_widget.update()
            logger.debug(f"Ручное вращение: X={self.gl_widget.rotation_x:.1f}, Y={self.gl_widget.rotation_y:.1f}")
    
    def _manual_scale(self, delta_scale: float):
        """Ручное масштабирование объекта с помощью клавиатуры"""
        if hasattr(self.gl_widget, 'scale'):
            new_scale = max(0.1, min(5.0, self.gl_widget.scale + delta_scale))
            self.gl_widget.scale = new_scale
            self.gl_widget.update()
            logger.debug(f"Ручное масштабирование: {new_scale:.2f}x")
    
    def _toggle_camera(self):
        """Запуск/остановка камеры"""
        if not self.is_active:
            # Запуск камеры
            logger.info("Запуск камеры...")
            success = self.hand_tracker.start()
            
            if success:
                self.is_active = True
                self.gl_widget.set_gestures_active(True)
                self.process_timer.start(33)  # Обработка кадров
                
                # Обновляем кнопки
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                # Обновляем статус (более заметный)
                self.status_label.setText("● АКТИВЕН - Отслеживание рук")
                self.status_label.setObjectName("statusActive")
                self.status_label.style().unpolish(self.status_label)
                self.status_label.style().polish(self.status_label)
                
                logger.info("Камера запущена")
            else:
                logger.error("Не удалось запустить камеру")
        else:
            # Остановка камеры
            logger.info("Остановка камеры...")
            self.is_active = False
            self.process_timer.stop()
            self.hand_tracker.stop()
            self.gl_widget.set_gestures_active(False)
            
            # Очищаем информацию о жестах (метод удален)
            
            # Обновляем кнопки
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # Обновляем статус
            self.status_label.setText("● НЕАКТИВЕН")
            self.status_label.setObjectName("statusInactive")
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)
            
            logger.info("Камера остановлена")
    
    def _process_frame(self):
        """Обработка кадра с камеры"""
        if not self.is_active:
            return
        
        try:
            # Обрабатываем кадр (но не отображаем его)
            frame = self.hand_tracker.process_frame()
            
            if frame is not None:
                # Получаем данные жестов
                hands_data = self.hand_tracker.get_gesture_data()
                
                # Обновляем 3D объект и скелет руки
                if hands_data:
                    self.gl_widget.update_gesture_data(hands_data)
                
                # Обновляем счетчик кадров для FPS
                self.frame_count += 1
            
        except Exception as e:
            logger.error(f"Ошибка обработки кадра: {e}", exc_info=True)
    
    def _reset_object(self):
        """Сброс трансформаций 3D объекта"""
        self.gl_widget.reset_transformations()
        logger.info("Объект сброшен пользователем")
    
    def _on_object_type_changed(self, index: int):
        """
        Обработка изменения типа объекта
        
        Args:
            index: Индекс выбранного элемента (0-куб, 1-сфера, 2-пирамида, 3-тор, 4-конус, 5-цилиндр)
        """
        object_types = ['cube', 'sphere', 'pyramid', 'torus', 'cone', 'cylinder']
        if 0 <= index < len(object_types):
            obj_type = object_types[index]
            self.gl_widget.set_object_type(obj_type)
            logger.info(f"Тип объекта изменен на: {obj_type}")
    
    def _open_object_settings(self):
        """Открытие диалога настроек 3D объекта"""
        dialog = QDialog(self)
        dialog.setWindowTitle(" Настройки 3D объекта")
        dialog.setMinimumSize(750, 650)
        dialog.setModal(True)
        
        # Применяем стиль
        dialog.setStyleSheet("""
            QDialog {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #0f0f1a, stop:1 #1a1a2e);
            }
            QLabel {
                color: #e8e8f0;
                font-size: 13px;
            }
            QGroupBox {
                background-color: rgba(25, 25, 45, 0.9);
                border: 2px solid #4a4a6a;
                border-radius: 12px;
                margin-top: 15px;
                padding-top: 20px;
                font-weight: bold;
                font-size: 14px;
                color: #7c8aff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #3a3a5a, stop:1 #2a2a45);
                border: 2px solid #5a5a7a;
                border-radius: 8px;
                padding: 10px 20px;
                color: #ffffff;
                font-weight: bold;
                min-height: 35px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #4a4a6a, stop:1 #3a3a55);
                border-color: #8b9aff;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4a4a6a;
                height: 8px;
                background: #1a1a2e;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7c8aff, stop:1 #5a6aff);
                border: 2px solid #9aafff;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QCheckBox {
                color: #e8e8f0;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a4a6a;
                border-radius: 4px;
                background-color: #1a1a2e;
            }
            QCheckBox::indicator:checked {
                background-color: #7c8aff;
                border-color: #7c8aff;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # === Раздел 1: Размер и материал ===
        size_material_group = QGroupBox("📐 Размер и материал")
        size_material_layout = QGridLayout(size_material_group)
        size_material_layout.setSpacing(10)
        
        # Размер
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Базовый размер:"))
        size_slider = QSlider(Qt.Orientation.Horizontal)
        size_slider.setMinimum(10)
        size_slider.setMaximum(100)
        size_slider.setValue(int(self.gl_widget.base_size * 100))
        size_slider.valueChanged.connect(lambda v: self.gl_widget.set_base_size(v / 100.0))
        size_layout.addWidget(size_slider)
        size_value_label = QLabel(f"{self.gl_widget.base_size:.2f}")
        size_value_label.setStyleSheet("color: #10b981; font-weight: bold; min-width: 40px;")
        size_layout.addWidget(size_value_label)
        size_slider.valueChanged.connect(lambda v: size_value_label.setText(f"{v/100:.2f}"))
        size_material_layout.addLayout(size_layout, 0, 0)
        
        # Блеск
        shininess_layout = QHBoxLayout()
        shininess_layout.addWidget(QLabel("Блеск:"))
        shininess_slider = QSlider(Qt.Orientation.Horizontal)
        shininess_slider.setMinimum(0)
        shininess_slider.setMaximum(128)
        shininess_slider.setValue(int(self.gl_widget.material_shininess))
        shininess_slider.valueChanged.connect(lambda v: self.gl_widget.set_material_properties(shininess=float(v)))
        shininess_layout.addWidget(shininess_slider)
        shininess_value_label = QLabel(f"{int(self.gl_widget.material_shininess)}")
        shininess_value_label.setStyleSheet("color: #f59e0b; font-weight: bold; min-width: 40px;")
        shininess_layout.addWidget(shininess_value_label)
        shininess_slider.valueChanged.connect(lambda v: shininess_value_label.setText(f"{v}"))
        size_material_layout.addLayout(shininess_layout, 1, 0)
        
        layout.addWidget(size_material_group)
        
        # === Раздел 2: Автовращение ===
        autorotate_group = QGroupBox("🔄 Автовращение")
        autorotate_layout = QVBoxLayout(autorotate_group)
        autorotate_layout.setSpacing(8)
        
        autorotate_controls = QHBoxLayout()
        auto_rotate_btn = QPushButton("Выключить" if self.gl_widget.auto_rotate else "Включить")
        
        def toggle_auto_rotate():
            self.gl_widget.toggle_auto_rotate()
            if self.gl_widget.auto_rotate:
                auto_rotate_btn.setText("Выключить")
                auto_rotate_btn.setStyleSheet("""
                    QPushButton {
                        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #ef4444, stop:1 #dc2626);
                        border: 2px solid #dc2626;
                        color: white;
                        font-weight: bold;
                    }
                """)
            else:
                auto_rotate_btn.setText("Включить")
                auto_rotate_btn.setStyleSheet("")
        
        auto_rotate_btn.clicked.connect(toggle_auto_rotate)
        # Устанавливаем начальный стиль
        if self.gl_widget.auto_rotate:
            auto_rotate_btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                        stop:0 #ef4444, stop:1 #dc2626);
                    border: 2px solid #dc2626;
                    color: white;
                    font-weight: bold;
                }
            """)
        
        autorotate_controls.addWidget(auto_rotate_btn)
        
        autorotate_controls.addWidget(QLabel("Скорость:"))
        rotate_speed_slider = QSlider(Qt.Orientation.Horizontal)
        rotate_speed_slider.setMinimum(1)
        rotate_speed_slider.setMaximum(50)
        rotate_speed_slider.setValue(int(self.gl_widget.auto_rotate_speed * 10))
        rotate_speed_slider.valueChanged.connect(lambda v: self.gl_widget.set_auto_rotate_speed(v / 10.0))
        autorotate_controls.addWidget(rotate_speed_slider)
        speed_value_label = QLabel(f"{self.gl_widget.auto_rotate_speed:.1f}")
        speed_value_label.setStyleSheet("color: #60a5fa; font-weight: bold; min-width: 40px;")
        autorotate_controls.addWidget(speed_value_label)
        rotate_speed_slider.valueChanged.connect(lambda v: speed_value_label.setText(f"{v/10:.1f}"))
        
        autorotate_layout.addLayout(autorotate_controls)
        layout.addWidget(autorotate_group)
        
        # === Раздел 3: Режимы отображения ===
        modes_group = QGroupBox("👁 Режимы отображения")
        modes_layout = QVBoxLayout(modes_group)
        modes_layout.setSpacing(8)
        
        wireframe_checkbox = QCheckBox("Каркасный режим (Wireframe)")
        wireframe_checkbox.setChecked(self.gl_widget.wireframe_mode)
        wireframe_checkbox.stateChanged.connect(lambda s: self.gl_widget.toggle_wireframe())
        modes_layout.addWidget(wireframe_checkbox)
        
        grid_checkbox = QCheckBox("Показывать сетку")
        grid_checkbox.setChecked(self.gl_widget.show_grid)
        grid_checkbox.stateChanged.connect(lambda s: self.gl_widget.toggle_grid())
        modes_layout.addWidget(grid_checkbox)
        
        axes_checkbox = QCheckBox("Показывать оси координат")
        axes_checkbox.setChecked(self.gl_widget.show_axes)
        axes_checkbox.stateChanged.connect(lambda s: self.gl_widget.toggle_axes())
        modes_layout.addWidget(axes_checkbox)
        
        layout.addWidget(modes_group)
        
        # === Раздел 4: Цвета ===
        colors_group = QGroupBox("🎨 Цвета объекта")
        colors_layout = QVBoxLayout(colors_group)
        colors_layout.setSpacing(10)
        
        # Цвета граней куба
        cube_faces_layout = QGridLayout()
        cube_faces_layout.setSpacing(8)
        
        faces = ['front', 'back', 'top', 'bottom', 'left', 'right']
        face_names = ['Передняя', 'Задняя', 'Верхняя', 'Нижняя', 'Левая', 'Правая']
        default_colors = [
            [0.2, 0.4, 1.0],  # Синий
            [1.0, 0.2, 0.2],  # Красный
            [0.2, 1.0, 0.3],  # Зеленый
            [1.0, 1.0, 0.2],  # Желтый
            [0.2, 1.0, 1.0],  # Голубой
            [1.0, 0.2, 1.0]   # Пурпурный
        ]
        
        color_buttons = {}
        for i, (face, name, color) in enumerate(zip(faces, face_names, default_colors)):
            btn = QPushButton(f"{name}")
            btn.setMinimumHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)});
                    color: white;
                    font-weight: bold;
                    border: 2px solid rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    border-color: rgba(255, 255, 255, 0.5);
                }}
            """)
            
            # Сохраняем ссылку на кнопку для обновления
            color_buttons[face] = btn
            cube_faces_layout.addWidget(btn, i // 3, i % 3)
            
            # Создаем отдельную функцию для каждой грани с правильным замыканием
            def make_color_handler(face_name, button):
                def handler():
                    current_color = self.gl_widget.cube_colors[face_name]
                    initial_color = QColor.fromRgbF(*current_color[:3])
                    new_color = QColorDialog.getColor(initial_color, dialog, f"Выберите цвет для грани")
                    
                    if new_color.isValid():
                        color_list = [new_color.redF(), new_color.greenF(), new_color.blueF(), 1.0]
                        self.gl_widget.set_cube_color(face_name, color_list)
                        button.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgb({new_color.red()}, {new_color.green()}, {new_color.blue()});
                                color: white;
                                font-weight: bold;
                                border: 2px solid rgba(255, 255, 255, 0.2);
                                border-radius: 8px;
                            }}
                            QPushButton:hover {{
                                border-color: rgba(255, 255, 255, 0.5);
                            }}
                        """)
                return handler
            
            btn.clicked.connect(make_color_handler(face, btn))
        colors_layout.addLayout(cube_faces_layout)
        
        # Основной цвет для других объектов
        colors_layout.addWidget(QLabel("Основной цвет (для сферы, пирамиды и др.):"))
        base_color_btn_layout = QHBoxLayout()
        base_color_btn = QPushButton("Изменить основной цвет")
        base_color_btn.setMinimumHeight(40)
        
        def change_base_color():
            current_color = self.gl_widget.object_base_color
            initial_color = QColor.fromRgbF(*current_color[:3])
            new_color = QColorDialog.getColor(initial_color, dialog, "Выберите основной цвет объекта")
            
            if new_color.isValid():
                color_list = [new_color.redF(), new_color.greenF(), new_color.blueF(), 1.0]
                secondary_color = [c * 0.7 for c in color_list[:3]] + [1.0]
                self.gl_widget.set_object_color(color_list, secondary_color)
        
        base_color_btn.clicked.connect(change_base_color)
        base_color_btn_layout.addWidget(base_color_btn)
        colors_layout.addLayout(base_color_btn_layout)
        
        layout.addWidget(colors_group)
        
        # === Кнопки управления ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        reset_btn = QPushButton("↺ Сбросить все настройки")
        
        def reset_customization():
            self.gl_widget.reset_customization()
            size_slider.setValue(30)
            shininess_slider.setValue(80)
            rotate_speed_slider.setValue(5)
            wireframe_checkbox.setChecked(False)
            grid_checkbox.setChecked(True)
            axes_checkbox.setChecked(False)
            if self.gl_widget.auto_rotate:
                toggle_auto_rotate()
        
        reset_btn.clicked.connect(reset_customization)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #ef4444, stop:1 #dc2626);
                border: 2px solid #dc2626;
                color: white;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #dc2626, stop:1 #b91c1c);
            }
        """)
        buttons_layout.addWidget(reset_btn)
        
        buttons_layout.addStretch()
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.close)
        close_btn.setMinimumWidth(120)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        dialog.exec()
    
    def closeEvent(self, event):
        """Обработка закрытия приложения"""
        logger.info("Закрытие приложения...")
        
        # Останавливаем камеру
        if self.is_active:
            self._toggle_camera()
        
        # Закрываем компоненты
        self.hand_tracker.stop()
        
        logger.info("Приложение закрыто")
        event.accept()


def _setup_logging():
    """Настройка системы логирования"""
    # Создаем директорию для логов
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Формируем имя файла лога с временной меткой
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"app_{timestamp}.log"
    
    # Настройка формата логов
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-20s | Line:%(lineno)-5s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Создаем logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # File handler (все логи в файл)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(file_handler)
    
    # Console handler (только INFO и выше в консоль)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    logger.addHandler(console_handler)
    
    logger.info(f"Логирование настроено. Файл: {log_file}")
    
    return logger


def main():
    """Точка входа в приложение"""
    # Настраиваем логирование
    global logger
    logger = _setup_logging()
    
    try:
        # Создаем приложение
        app = QApplication(sys.argv)
        app.setApplicationName("Hand Gesture 3D Control")
        app.setApplicationVersion("1.0.0")
        
        # Устанавливаем современный стиль
        app.setStyle("Fusion")
        
        # Создаем и показываем главное окно
        window = MainWindow()
        window.show()
        
        logger.info("Приложение запущено")
        
        # Запускаем цикл событий
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
