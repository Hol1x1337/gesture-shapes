"""
Hand Gesture 3D Control - Components Package

Компоненты приложения:
- HandTracker: Отслеживание руки через MediaPipe
- GLWidget: OpenGL рендеринг 3D объектов
- CameraWidget: Виджет отображения камеры
"""

from .hand_tracker import HandTracker
from .gl_widget import GLWidget
from .camera_widget import CameraWidget

__all__ = ['HandTracker', 'GLWidget', 'CameraWidget']
