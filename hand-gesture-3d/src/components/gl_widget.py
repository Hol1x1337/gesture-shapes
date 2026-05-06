"""
GLWidget - OpenGL виджет для рендеринга и управления 3D объектом

Отвечает за:
1. Рендеринг 3D объектов через OpenGL (куб, сфера, пирамида, тор)
2. Применение трансформаций на основе жестов руки (поддержка 2 рук)
3. Управление вращением, масштабированием и позицией объекта
4. Визуализация скелета руки в 3D пространстве
5. Эффекты обратной связи при распознавании жестов
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import logging
import math
import time

logger = logging.getLogger(__name__)


class GLWidget(QOpenGLWidget):
    """OpenGL виджет для отображения и управления 3D объектом"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Тип текущего объекта
        self.object_type = 'cube'  # cube, sphere, pyramid, torus, cone, cylinder
        
        # Параметры трансформации объекта
        self.rotation_x = 15.0  # Небольшой наклон для лучшего 3D вида
        self.rotation_y = 25.0  # Поворот для демонстрации 3D
        self.rotation_z = 0.0
        
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_z = -9.0  # Увеличено расстояние (было -5.0) для меньшего объекта
        
        self.scale = 1.0
        
        # Целевые значения для плавной анимации
        self.target_rotation_x = 15.0  # Синхронизировано с rotation_x
        self.target_rotation_y = 25.0  # Синхронизировано с rotation_y
        self.target_position_x = 0.0
        self.target_position_y = 0.0
        self.target_position_z = -9.0  # Увеличено расстояние (было -5.0)
        self.target_scale = 1.0
        
        # === РАСШИРЕННАЯ КАСТОМИЗАЦИЯ ОБЪЕКТОВ ===
        # Цвета граней куба (RGBA)
        self.cube_colors = {
            'front': [0.2, 0.4, 1.0, 1.0],    # Синий
            'back': [1.0, 0.2, 0.2, 1.0],     # Красный
            'top': [0.2, 1.0, 0.3, 1.0],      # Зеленый
            'bottom': [1.0, 1.0, 0.2, 1.0],   # Желтый
            'left': [0.2, 1.0, 1.0, 1.0],     # Голубой
            'right': [1.0, 0.2, 1.0, 1.0]     # Пурпурный
        }
        
        # Основной цвет для других объектов (градиент)
        self.object_base_color = [0.4, 0.5, 0.95, 1.0]
        self.object_secondary_color = [0.2, 0.3, 0.8, 1.0]
        
        # Параметры материала
        self.material_shininess = 80.0
        self.material_specular = [1.0, 1.0, 1.0, 1.0]
        
        # Режим отображения
        self.wireframe_mode = False  # Каркасный режим
        self.show_grid = True  # Показывать сетку
        self.show_axes = False  # Показывать оси координат
        
        # Автоматическое вращение
        self.auto_rotate = False
        self.auto_rotate_speed = 0.5
        
        # Размер базового объекта
        self.base_size = 0.3  # Базовый размер для всех объектов
        
        # Флаг активности жестов
        self.gestures_active = False
        
        # Данные для двух рук
        self.left_hand_data = None
        self.right_hand_data = None
        
        # Эффекты обратной связи
        self.gesture_effect_alpha = 0.0  # Прозрачность эффекта
        self.last_gesture_time = 0
        self.effect_color = [1.0, 1.0, 1.0]  # Цвет эффекта
        
        # Таймер для обновления
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_transformations)
        self.update_timer.start(16)  # ~60 FPS
        
        logger.info("GLWidget инициализирован (поддержка 2 рук)")
    
    def initializeGL(self):
        """Инициализация OpenGL контекста"""
        # Настройка цвета фона (градиент темный)
        glClearColor(0.08, 0.08, 0.12, 1.0)
        
        # Включение тестирования глубины
        glEnable(GL_DEPTH_TEST)
        
        # Улучшенное освещение
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_LIGHT2)  # Дополнительный свет для эффектов
        
        # Основной свет (спереди-сверху)
        light0_position = [5.0, 10.0, 5.0, 1.0]
        light0_ambient = [0.4, 0.4, 0.5, 1.0]
        light0_diffuse = [1.0, 1.0, 1.0, 1.0]
        
        glLightfv(GL_LIGHT0, GL_POSITION, light0_position)
        glLightfv(GL_LIGHT0, GL_AMBIENT, light0_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light0_diffuse)
        
        # Дополнительный свет (сбоку для объема)
        light1_position = [-5.0, 0.0, 5.0, 1.0]
        light1_diffuse = [0.5, 0.5, 0.6, 1.0]
        
        glLightfv(GL_LIGHT1, GL_POSITION, light1_position)
        glLightfv(GL_LIGHT1, GL_DIFFUSE, light1_diffuse)
        
        # Третий свет для подсветки эффектов
        light2_position = [0.0, -5.0, 3.0, 1.0]
        light2_diffuse = [0.3, 0.3, 0.4, 1.0]
        
        glLightfv(GL_LIGHT2, GL_POSITION, light2_position)
        glLightfv(GL_LIGHT2, GL_DIFFUSE, light2_diffuse)
        
        # Улучшенный материал объекта
        material_ambient = [0.3, 0.4, 0.8, 1.0]
        material_diffuse = [0.4, 0.5, 0.95, 1.0]
        material_specular = [1.0, 1.0, 1.0, 1.0]
        material_shininess = 80.0
        
        glMaterialfv(GL_FRONT, GL_AMBIENT, material_ambient)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, material_diffuse)
        glMaterialfv(GL_FRONT, GL_SPECULAR, material_specular)
        glMaterialf(GL_FRONT, GL_SHININESS, material_shininess)
        
        # Получаем информацию о GPU
        vendor = glGetString(GL_VENDOR).decode('utf-8') if glGetString(GL_VENDOR) else "Unknown"
        renderer = glGetString(GL_RENDERER).decode('utf-8') if glGetString(GL_RENDERER) else "Unknown"
        
        logger.info(f"OpenGL контекст инициализирован")
        logger.info(f"GPU: {vendor} - {renderer}")
        logger.info("Рендеринг использует GPU (встроенная графика)")
    
    def resizeGL(self, w, h):
        """Обработка изменения размера виджета"""
        if h == 0:
            h = 1
        
        glViewport(0, 0, w, h)
        
        # Настройка проекции
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / h, 0.1, 100.0)
        
        glMatrixMode(GL_MODELVIEW)
    
    def paintGL(self):
        """Рендеринг сцены"""
        # Очистка буферов
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        glLoadIdentity()
        
        # Сначала устанавливаем камеру (фиксированная позиция)
        gluLookAt(0.0, 0.0, -9.0,  # Позиция камеры
                  0.0, 0.0, 0.0,   # Точка взгляда (центр)
                  0.0, 1.0, 0.0)   # Верхний вектор
        
        # Теперь применяем трансформации к объекту
        glTranslatef(self.position_x, self.position_y, self.position_z + 9.0)  # Компенсируем позицию камеры
        glRotatef(self.rotation_x, 1.0, 0.0, 0.0)
        glRotatef(self.rotation_y, 0.0, 1.0, 0.0)
        glRotatef(self.rotation_z, 0.0, 0.0, 1.0)
        glScalef(self.scale, self.scale, self.scale)
        
        # Автоматическое вращение
        if self.auto_rotate:
            self.target_rotation_y += self.auto_rotate_speed
            self.rotation_y = self.target_rotation_y
        
        # Рисуем сетку пола (если включено)
        if self.show_grid:
            self._draw_grid()
        
        # Рисуем оси координат (если включено)
        if self.show_axes:
            self._draw_axes()
        
        # Рисуем выбранный 3D объект
        self._draw_current_object()
        
        # Рисуем визуализацию скелета руки (если есть данные)
        if self.left_hand_data or self.right_hand_data:
            self._draw_hand_skeleton()
        
        # Рисуем эффекты обратной связи (только кольца, без частиц)
        if self.gesture_effect_alpha > 0.01:
            self._draw_gesture_effect()
        
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)
    
    def _draw_grid(self):
        """Отрисовка сетки пола для понимания пространства"""
        glDisable(GL_LIGHTING)
        
        grid_size = 10.0
        grid_divisions = 20
        step = grid_size / grid_divisions
        
        glBegin(GL_LINES)
        
        # Цвет сетки (полупрозрачный серый)
        glColor4f(0.3, 0.3, 0.35, 0.5)
        
        # Линии по X
        for i in range(grid_divisions + 1):
            pos = -grid_size/2 + i * step
            glVertex3f(pos, -grid_size/2, -grid_size/2)
            glVertex3f(pos, -grid_size/2, grid_size/2)
        
        # Линии по Z
        for i in range(grid_divisions + 1):
            pos = -grid_size/2 + i * step
            glVertex3f(-grid_size/2, -grid_size/2, pos)
            glVertex3f(grid_size/2, -grid_size/2, pos)
        
        glEnd()
        
        glEnable(GL_LIGHTING)
    
    def _draw_axes(self):
        """Отрисовка индикаторов осей координат"""
        glDisable(GL_LIGHTING)
        
        axis_length = 2.0
        
        glBegin(GL_LINES)
        
        # Ось X (красная)
        glColor3f(1.0, 0.2, 0.2)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(axis_length, 0.0, 0.0)
        
        # Ось Y (зеленая)
        glColor3f(0.2, 1.0, 0.2)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, axis_length, 0.0)
        
        # Ось Z (синяя)
        glColor3f(0.2, 0.4, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, axis_length)
        
        glEnd()
        
        # Подписи осей
        self._draw_axis_labels(axis_length)
        
        glEnable(GL_LIGHTING)
    
    def _draw_axis_labels(self, axis_length):
        """Рисование подписей осей (упрощенно через точки)"""
        # В реальном приложении здесь был бы рендеринг текста
        # Для простоты рисуем маркеры на концах осей
        
        marker_size = 0.15
        
        glBegin(GL_QUADS)
        
        # Маркер на конце оси X
        glColor3f(1.0, 0.2, 0.2)
        glVertex3f(axis_length - marker_size, -marker_size, -marker_size)
        glVertex3f(axis_length + marker_size, -marker_size, -marker_size)
        glVertex3f(axis_length + marker_size, marker_size, -marker_size)
        glVertex3f(axis_length - marker_size, marker_size, -marker_size)
        
        # Маркер на конце оси Y
        glColor3f(0.2, 1.0, 0.2)
        glVertex3f(-marker_size, axis_length - marker_size, -marker_size)
        glVertex3f(marker_size, axis_length - marker_size, -marker_size)
        glVertex3f(marker_size, axis_length + marker_size, -marker_size)
        glVertex3f(-marker_size, axis_length + marker_size, -marker_size)
        
        # Маркер на конце оси Z
        glColor3f(0.2, 0.4, 1.0)
        glVertex3f(-marker_size, -marker_size, axis_length - marker_size)
        glVertex3f(marker_size, -marker_size, axis_length - marker_size)
        glVertex3f(marker_size, marker_size, axis_length - marker_size)
        glVertex3f(-marker_size, marker_size, axis_length - marker_size)
        
        glEnd()
    
    def _draw_current_object(self):
        """Отрисовка текущего выбранного объекта"""
        if self.object_type == 'cube':
            self._draw_cube()
        elif self.object_type == 'sphere':
            self._draw_sphere()
        elif self.object_type == 'pyramid':
            self._draw_pyramid()
        elif self.object_type == 'torus':
            self._draw_torus()
        elif self.object_type == 'cone':
            self._draw_cone()
        elif self.object_type == 'cylinder':
            self._draw_cylinder()
    
    def _draw_cube(self):
        """Отрисовка куба с улучшенными цветами"""
        size = self.base_size
        
        # Если включен каркасный режим
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        
        glBegin(GL_QUADS)
        
        # Передняя грань (настраиваемый цвет)
        color = self.cube_colors['front']
        glColor4f(*color)
        glNormal3f(0.0, 0.0, 1.0)
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)
        
        # Задняя грань
        color = self.cube_colors['back']
        glColor4f(*color)
        glNormal3f(0.0, 0.0, -1.0)
        glVertex3f(-size, -size, -size)
        glVertex3f(-size, size, -size)
        glVertex3f(size, size, -size)
        glVertex3f(size, -size, -size)
        
        # Верхняя грань
        color = self.cube_colors['top']
        glColor4f(*color)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(-size, size, -size)
        glVertex3f(-size, size, size)
        glVertex3f(size, size, size)
        glVertex3f(size, size, -size)
        
        # Нижняя грань
        color = self.cube_colors['bottom']
        glColor4f(*color)
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(-size, -size, -size)
        glVertex3f(size, -size, -size)
        glVertex3f(size, -size, size)
        glVertex3f(-size, -size, size)
        
        # Левая грань
        color = self.cube_colors['left']
        glColor4f(*color)
        glNormal3f(-1.0, 0.0, 0.0)
        glVertex3f(-size, -size, -size)
        glVertex3f(-size, -size, size)
        glVertex3f(-size, size, size)
        glVertex3f(-size, size, -size)
        
        # Правая грань
        color = self.cube_colors['right']
        glColor4f(*color)
        glNormal3f(1.0, 0.0, 0.0)
        glVertex3f(size, -size, -size)
        glVertex3f(size, size, -size)
        glVertex3f(size, size, size)
        glVertex3f(size, -size, size)
        
        glEnd()
        
        # Возвращаем нормальный режим отрисовки
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    def _draw_sphere(self):
        """Отрисовка сферы с градиентом (только ручная отрисовка)"""
        # Используем только ручную отрисовку, чтобы избежать ошибок GLUT
        self._draw_sphere_manual()
    
    def _draw_sphere_manual(self):
        """Ручная отрисовка сферы (fallback)"""
        slices = 32
        stacks = 16
        radius = self.base_size
        
        # Если включен каркасный режим
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        
        for i in range(stacks):
            lat0 = math.pi * (-0.5 + float(i) / stacks)
            z0 = radius * math.sin(lat0)
            zr0 = radius * math.cos(lat0)
            
            lat1 = math.pi * (-0.5 + float(i + 1) / stacks)
            z1 = radius * math.sin(lat1)
            zr1 = radius * math.cos(lat1)
            
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                lng = 2 * math.pi * float(j) / slices
                x = math.cos(lng)
                y = math.sin(lng)
                
                # Градиентный цвет на основе позиции
                color_val = (math.sin(lng) + 1) / 2
                r = self.object_base_color[0] * (1 - 0.3 * color_val)
                g = self.object_base_color[1] * (1 - 0.3 * color_val)
                b = self.object_base_color[2]
                
                glColor4f(r, g, b, 1.0)
                
                glNormal3f(x * zr0, y * zr0, z0)
                glVertex3f(x * zr0, y * zr0, z0)
                glNormal3f(x * zr1, y * zr1, z1)
                glVertex3f(x * zr1, y * zr1, z1)
            glEnd()
        
        # Возвращаем нормальный режим отрисовки
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    def _draw_pyramid(self):
        """Отрисовка пирамиды"""
        height = self.base_size * 1.5
        base_size = self.base_size * 1.2
        
        # Если включен каркасный режим
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        
        glBegin(GL_TRIANGLES)
        
        # Передняя грань (градиент от основного цвета)
        glColor4f(*self.object_base_color)
        glVertex3f(-base_size/2, -height/2, base_size/2)
        glVertex3f(base_size/2, -height/2, base_size/2)
        glVertex3f(0.0, height/2, 0.0)
        
        # Задняя грань
        glColor4f(self.object_secondary_color[0], self.object_secondary_color[1], 
                 self.object_secondary_color[2], 1.0)
        glVertex3f(-base_size/2, -height/2, -base_size/2)
        glVertex3f(0.0, height/2, 0.0)
        glVertex3f(base_size/2, -height/2, -base_size/2)
        
        # Левая грань
        color_val = 0.8
        glColor4f(self.object_base_color[0] * color_val, 
                 self.object_base_color[1] * color_val,
                 self.object_base_color[2] * color_val, 1.0)
        glVertex3f(-base_size/2, -height/2, -base_size/2)
        glVertex3f(-base_size/2, -height/2, base_size/2)
        glVertex3f(0.0, height/2, 0.0)
        
        # Правая грань
        glColor4f(self.object_secondary_color[0] * 0.9, 
                 self.object_secondary_color[1] * 0.9,
                 self.object_secondary_color[2] * 0.9, 1.0)
        glVertex3f(base_size/2, -height/2, -base_size/2)
        glVertex3f(0.0, height/2, 0.0)
        glVertex3f(base_size/2, -height/2, base_size/2)
        
        glEnd()
        
        # Основание
        glBegin(GL_QUADS)
        glColor4f(self.object_base_color[0] * 0.7, 
                 self.object_base_color[1] * 0.7,
                 self.object_base_color[2] * 0.7, 1.0)
        glVertex3f(-base_size/2, -height/2, -base_size/2)
        glVertex3f(base_size/2, -height/2, -base_size/2)
        glVertex3f(base_size/2, -height/2, base_size/2)
        glVertex3f(-base_size/2, -height/2, base_size/2)
        glEnd()
        
        # Возвращаем нормальный режим отрисовки
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    def _draw_cone(self):
        """Отрисовка конуса"""
        base_radius = self.base_size
        height = self.base_size * 2
        segments = 32
        
        # Если включен каркасный режим
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        
        # Рисуем основание (круг)
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(self.object_base_color[0] * 1.2, 
                 self.object_base_color[1] * 0.8,
                 self.object_base_color[2] * 0.5, 1.0)
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(0.0, -height/2, 0.0)  # Центр основания
        
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            x = base_radius * math.cos(angle)
            z = base_radius * math.sin(angle)
            glVertex3f(x, -height/2, z)
        glEnd()
        
        # Рисуем боковую поверхность
        glBegin(GL_TRIANGLES)
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments
            
            x1 = base_radius * math.cos(angle1)
            z1 = base_radius * math.sin(angle1)
            x2 = base_radius * math.cos(angle2)
            z2 = base_radius * math.sin(angle2)
            
            # Градиентный цвет на основе угла
            color_val = (math.sin(angle1) + 1) / 2
            r = self.object_base_color[0] * (0.8 + 0.4 * color_val)
            g = self.object_base_color[1] * (0.6 + 0.4 * color_val)
            b = self.object_base_color[2]
            
            glColor4f(r, g, b, 1.0)
            
            # Нормаль для освещения
            normal_x = math.cos((angle1 + angle2) / 2)
            normal_z = math.sin((angle1 + angle2) / 2)
            glNormal3f(normal_x, 0.5, normal_z)
            
            glVertex3f(x1, -height/2, z1)
            glVertex3f(x2, -height/2, z2)
            glVertex3f(0.0, height/2, 0.0)  # Вершина конуса
        glEnd()
        
        # Возвращаем нормальный режим отрисовки
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    def _draw_cylinder(self):
        """Отрисовка цилиндра"""
        radius = self.base_size * 0.85
        height = self.base_size * 1.7
        segments = 32
        
        # Если включен каркасный режим
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        
        # Рисуем нижнее основание
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(self.object_base_color[0] * 0.9, 
                 self.object_base_color[1] * 0.9,
                 self.object_base_color[2], 1.0)
        glNormal3f(0.0, -1.0, 0.0)
        glVertex3f(0.0, -height/2, 0.0)
        
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            glVertex3f(x, -height/2, z)
        glEnd()
        
        # Рисуем верхнее основание
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(self.object_base_color[0], 
                 self.object_base_color[1],
                 self.object_base_color[2] * 1.1, 1.0)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, height/2, 0.0)
        
        for i in range(segments + 1):
            angle = 2 * math.pi * (segments - i) / segments
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            glVertex3f(x, height/2, z)
        glEnd()
        
        # Рисуем боковую поверхность
        glBegin(GL_QUAD_STRIP)
        for i in range(segments + 1):
            angle = 2 * math.pi * i / segments
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            
            # Градиентный цвет
            color_val = (math.sin(angle) + 1) / 2
            r = self.object_secondary_color[0] * (0.7 + 0.3 * color_val)
            g = self.object_secondary_color[1] * (0.7 + 0.3 * color_val)
            b = self.object_secondary_color[2]
            
            glColor4f(r, g, b, 1.0)
            
            glNormal3f(math.cos(angle), 0.0, math.sin(angle))
            glVertex3f(x, -height/2, z)
            glVertex3f(x, height/2, z)
        glEnd()
        
        # Возвращаем нормальный режим отрисовки
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    def _draw_torus(self):
        """Отрисовка тора (пончика)"""
        major_radius = self.base_size * 0.8
        minor_radius = self.base_size * 0.3
        major_segments = 32
        minor_segments = 16
        
        # Если включен каркасный режим
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        
        for i in range(major_segments):
            theta1 = 2 * math.pi * i / major_segments
            theta2 = 2 * math.pi * (i + 1) / major_segments
            
            glBegin(GL_QUAD_STRIP)
            for j in range(minor_segments + 1):
                phi = 2 * math.pi * j / minor_segments
                
                # Внешний круг
                x1 = (major_radius + minor_radius * math.cos(phi)) * math.cos(theta1)
                y1 = (major_radius + minor_radius * math.cos(phi)) * math.sin(theta1)
                z1 = minor_radius * math.sin(phi)
                
                # Внутренний круг
                x2 = (major_radius + minor_radius * math.cos(phi)) * math.cos(theta2)
                y2 = (major_radius + minor_radius * math.cos(phi)) * math.sin(theta2)
                z2 = minor_radius * math.sin(phi)
                
                # Градиентный цвет на основе позиции
                color_val = (math.sin(theta1) + 1) / 2
                r = self.object_base_color[0] * (0.6 + 0.5 * color_val)
                g = self.object_base_color[1] * (0.8 - 0.3 * color_val)
                b = self.object_base_color[2]
                
                glColor4f(r, g, b, 1.0)
                
                glVertex3f(x1, y1, z1)
                glVertex3f(x2, y2, z2)
            glEnd()
        
        # Возвращаем нормальный режим отрисовки
        if self.wireframe_mode:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    def _draw_hand_skeleton(self):
        """Визуализация 3D скелета руки"""
        glDisable(GL_LIGHTING)
        
        # Рисуем правую руку (синяя) - СПРАВА
        if self.right_hand_data and 'landmarks' in self.right_hand_data:
            self._draw_single_hand_skeleton(self.right_hand_data['landmarks'], 
                                           [0.2, 0.4, 1.0],  # Синий цвет
                                           offset_x=2.5)  # Исправлено: правая рука справа
        
        # Рисуем левую руку (оранжевая) - СЛЕВА
        if self.left_hand_data and 'landmarks' in self.left_hand_data:
            self._draw_single_hand_skeleton(self.left_hand_data['landmarks'], 
                                           [1.0, 0.5, 0.0],  # Оранжевый цвет
                                           offset_x=-2.5)  # Исправлено: левая рука слева
        
        glEnable(GL_LIGHTING)
    
    def _draw_single_hand_skeleton(self, landmarks, color, offset_x=0):
        """
        Отрисовка скелета одной руки
        
        Args:
            landmarks: Массив координат 21 точки руки
            color: RGB цвет для отрисовки
            offset_x: Смещение по оси X для позиционирования
        """
        # Масштаб для визуализации (уменьшен с 1.0 до 0.7)
        scale = 0.7
        
        # Определяем соединения между точками (кости руки)
        connections = [
            # Запястье к основаниям пальцев
            (0, 1), (1, 2), (2, 3), (3, 4),  # Большой палец
            (0, 5), (5, 6), (6, 7), (7, 8),  # Указательный
            (0, 9), (9, 10), (10, 11), (11, 12),  # Средний
            (0, 13), (13, 14), (14, 15), (15, 16),  # Безымянный
            (0, 17), (17, 18), (18, 19), (19, 20),  # Мизинец
            # Соединения между основаниями пальцев
            (5, 9), (9, 13), (13, 17)
        ]
        
        # Рисуем кости
        glBegin(GL_LINES)
        glColor3f(color[0], color[1], color[2])
        
        for start_idx, end_idx in connections:
            if start_idx < len(landmarks) and end_idx < len(landmarks):
                start = landmarks[start_idx]
                end = landmarks[end_idx]
                
                # Преобразуем координаты MediaPipe в OpenGL
                x1 = (start[0] - 0.5) * 2 * scale + offset_x
                y1 = (0.5 - start[1]) * 2 * scale
                z1 = -start[2] * scale
                
                x2 = (end[0] - 0.5) * 2 * scale + offset_x
                y2 = (0.5 - end[1]) * 2 * scale
                z2 = -end[2] * scale
                
                glVertex3f(x1, y1, z1)
                glVertex3f(x2, y2, z2)
        
        glEnd()
        
        # Рисуем суставы (точки) - уменьшенный размер
        glPointSize(4.0)  # Уменьшено с 6.0 до 4.0
        glBegin(GL_POINTS)
        
        for i, landmark in enumerate(landmarks):
            x = (landmark[0] - 0.5) * 2 * scale + offset_x
            y = (0.5 - landmark[1]) * 2 * scale
            z = -landmark[2] * scale
            
            # Разные цвета для разных частей руки
            if i == 0:  # Запястье
                glColor3f(1.0, 1.0, 0.0)  # Желтый
            elif i in [4, 8, 12, 16, 20]:  # Кончики пальцев
                glColor3f(1.0, 0.5, 0.5)  # Розовый
            else:
                glColor3f(color[0], color[1], color[2])
            
            glVertex3f(x, y, z)
        
        glEnd()
        
        # Подписи для кончиков пальцев - уменьшенный размер
        glPointSize(7.0)  # Уменьшено с 10.0 до 7.0
        glBegin(GL_POINTS)
        glColor3f(1.0, 1.0, 1.0)
        
        fingertip_indices = [4, 8, 12, 16, 20]
        for idx in fingertip_indices:
            if idx < len(landmarks):
                landmark = landmarks[idx]
                x = (landmark[0] - 0.5) * 2 * scale + offset_x
                y = (0.5 - landmark[1]) * 2 * scale
                z = -landmark[2] * scale
                glVertex3f(x, y, z)
        
        glEnd()
    
    def _draw_gesture_effect(self):
        """Отрисовка визуального эффекта при распознавании жеста (упрощенная)"""
        # Затухание эффекта со временем
        current_time = time.time() if 'time' in dir() else 0
        elapsed = current_time - self.last_gesture_time if hasattr(self, 'last_gesture_time') else 0
        
        # Уменьшаем прозрачность
        self.gesture_effect_alpha *= 0.95
        
        if self.gesture_effect_alpha < 0.01:
            return
        
        glDisable(GL_LIGHTING)
        glDepthMask(GL_FALSE)
        
        # Рисуем только одно кольцо вместо трех для производительности
        radius = 2.0 + (elapsed * 2) % 1.0
        alpha = self.gesture_effect_alpha
        
        glBegin(GL_LINE_LOOP)
        glColor4f(self.effect_color[0], self.effect_color[1], 
                 self.effect_color[2], alpha)
        
        segments = 32
        for j in range(segments):
            angle = 2 * math.pi * j / segments
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            glVertex3f(x, y, 0)
        
        glEnd()
        
        glDepthMask(GL_TRUE)
        glEnable(GL_LIGHTING)
    
    def trigger_gesture_effect(self, gesture_type='pinch'):
        """
        Активация визуального эффекта при жесте (с ограничением частоты)
        
        Args:
            gesture_type: Тип жеста ('pinch', 'open_palm', 'ok', 'rotation')
        """
        # Ограничиваем частоту эффектов - не чаще раза в 0.3 секунды
        current_time = time.time() if 'time' in dir() else 0
        if hasattr(self, 'last_gesture_time') and (current_time - self.last_gesture_time) < 0.3:
            return
        
        self.gesture_effect_alpha = 1.0
        self.last_gesture_time = current_time
        
        # Устанавливаем цвет в зависимости от типа жеста
        if gesture_type == 'pinch':
            self.effect_color = [0.0, 1.0, 0.5]  # Зеленый
        elif gesture_type == 'open_palm':
            self.effect_color = [1.0, 0.3, 0.3]  # Красный
        elif gesture_type == 'ok':
            self.effect_color = [0.3, 0.7, 1.0]  # Голубой
        elif gesture_type == 'rotation':
            self.effect_color = [1.0, 1.0, 0.3]  # Желтый
        else:
            self.effect_color = [1.0, 1.0, 1.0]  # Белый
    
    def update_gesture_data(self, hands_data: list):
        """
        Обновление данных жестов от HandTracker с новой системой управления
        
        ЛОГИКА УПРАВЛЕНИЯ:
        - Одна рука + pinch (большой+указательный): ВРАЩЕНИЕ куба
        - Две руки + двойной pinch: МАСШТАБ/Zoom
          * Руки РАЗВОДЯТСЯ в стороны → объект ПРИБЛИЖАЕТСЯ (увеличивается)
          * Руки СВОДЯТСЯ вместе → объект ОТДАЛЯЕТСЯ (уменьшается)
        - Открытая ладонь: остановка всех действий
        
        Args:
            hands_data: Список данных рук (максимум 2)
        """
        if not self.gestures_active:
            logger.warning("Жесты не активны!")
            return
            
        if not hands_data:
            logger.warning("Нет данных о руках!")
            return
        
        logger.info(f"Получены данные о {len(hands_data)} руке(ах)")
        
        # Разделяем данные по рукам
        self.left_hand_data = None
        self.right_hand_data = None
        
        for hand_data in hands_data:
            handedness = hand_data.get('handedness', '')
            if handedness == 'Left':
                self.left_hand_data = hand_data
            elif handedness == 'Right':
                self.right_hand_data = hand_data
        
        num_hands = len(hands_data)
        
        # === ОДНА РУКА + PINCH = ВРАЩЕНИЕ ===
        if num_hands == 1:
            hand_data = hands_data[0]
            handedness = hand_data.get('handedness', 'Unknown')
            open_palm = hand_data.get('open_palm', False)
            pinch_distance = hand_data.get('pinch_distance', 1.0)
            
            logger.info(f"Одна рука ({handedness}): open_palm={open_palm}, pinch={pinch_distance:.3f}")
            
            # Сначала проверяем PINCH (приоритет над открытой ладонью)
            # Pinch жест (пальцы сведены) - режим ВРАЩЕНИЯ
            if pinch_distance < 0.5:
                palm_x = hand_data['palm_x']
                palm_y = hand_data['palm_y']
                
                logger.info(f"✓ PINCH АКТИВЕН (расстояние: {pinch_distance:.3f} < 0.5)! Режим вращения: palm_x={palm_x:.3f}, palm_y={palm_y:.3f}")
                
                # Мертвая зона для предотвращения случайного вращения (уменьшена)
                dead_zone_threshold = 0.1  # Было 0.15, уменьшил для лучшей чувствительности
                
                logger.info(f"Проверка мертвой зоны: |palm_x|={abs(palm_x):.3f}, |palm_y|={abs(palm_y):.3f}, порог={dead_zone_threshold}")
                
                if abs(palm_x) > dead_zone_threshold or abs(palm_y) > dead_zone_threshold:
                    rotation_speed = 3.0
                    
                    old_rot_x = self.target_rotation_x
                    old_rot_y = self.target_rotation_y
                    
                    # Вращение на основе движения руки
                    self.target_rotation_y += palm_x * rotation_speed
                    self.target_rotation_x -= palm_y * rotation_speed
                    
                    self.trigger_gesture_effect('rotation')
                    
                    logger.info(f"ВРАЩЕНИЕ! rot_x: {old_rot_x:.1f} → {self.target_rotation_x:.1f}, rot_y: {old_rot_y:.1f} → {self.target_rotation_y:.1f}")
                else:
                    logger.info(f"Рука в мертвой зоне (порог: {dead_zone_threshold})")
            # Только если pinch НЕ активен, проверяем открытую ладонь
            elif open_palm:
                logger.info("Открытая ладонь - остановка (pinch не активен)")
                self.trigger_gesture_effect('open_palm')
                return
            else:
                logger.debug(f"Pinch не активен (расстояние: {pinch_distance:.3f} >= 0.5)")
        
        # === ДВЕ РУКИ + ДВОЙНОЙ PINCH = МАСШТАБ/ZOOM ===
        elif num_hands == 2:
            left_pinch = self.left_hand_data.get('pinch_distance', 1.0) if self.left_hand_data else 1.0
            right_pinch = self.right_hand_data.get('pinch_distance', 1.0) if self.right_hand_data else 1.0
            
            logger.info(f"Две руки: left_pinch={left_pinch:.3f}, right_pinch={right_pinch:.3f}")
            
            # Проверяем, что ОБЕ руки показывают pinch (двойной pinch)
            if left_pinch < 0.3 and right_pinch < 0.3:
                logger.info("ДВОЙНОЙ PINCH обнаружен! Режим масштаба")
                
                # Вычисляем среднее расстояние между руками для масштаба
                # Используем позицию ладоней для определения расстояния между руками
                left_palm_x = self.left_hand_data.get('palm_x', 0.0)
                right_palm_x = self.right_hand_data.get('palm_x', 0.0)
                
                # Расстояние между руками (абсолютная разница по X)
                hands_distance = abs(right_palm_x - left_palm_x)
                
                logger.info(f"Расстояние между руками: {hands_distance:.3f}")
                
                # Маппинг расстояния между руками к масштабу объекта
                # hands_distance 0.0 (руки вместе) → scale = 0.5 (маленький/отдаление)
                # hands_distance 1.5+ (руки далеко) → scale = 2.5 (большой/приближение)
                self.target_scale = 0.5 + min(hands_distance / 1.5, 1.0) * 2.0
                
                self.trigger_gesture_effect('pinch')
                
                logger.info(f"МАСШТАБ: distance={hands_distance:.3f}, scale={self.target_scale:.2f}")
            else:
                logger.debug("Двойной pinch не активен")
        
        # === РАСШИРЕННЫЕ ЖЕСТЫ (проверяем для всех рук) ===
        for hand_data in hands_data:
            # Жест "кулак" - пауза
            if hand_data.get('fist', False):
                logger.info("Жест КУЛАК обнаружен - пауза вращения")
                # Можно добавить логику паузы
            
            # Жест "указательный палец вверх" - сброс позиции
            if hand_data.get('pointing_up', False):
                logger.info("Жест УКАЗАТЕЛЬНЫЙ ВВЕРХ - сброс позиции")
                self.reset_transformations()
            
            # Жест "победа" (V) - смена объекта
            if hand_data.get('victory', False):
                logger.info("Жест ПОБЕДА (V) - переключение объекта")
                # Циклическое переключение объектов
                object_types = ['cube', 'sphere', 'pyramid', 'torus', 'cone', 'cylinder']
                current_idx = object_types.index(self.object_type) if self.object_type in object_types else 0
                next_idx = (current_idx + 1) % len(object_types)
                self.set_object_type(object_types[next_idx])
            
            # Жест "сердце" - специальный эффект
            if hand_data.get('heart', False):
                logger.info("Жест СЕРДЦЕ - активация радужного эффекта")
                self.trigger_gesture_effect('heart')
    
    def _update_transformations(self):
        """Плавное обновление трансформаций (интерполяция)"""
        # Коэффициент интерполяции для плавности
        lerp_factor = 0.15
        
        # Интерполяция позиции (X, Y, Z)
        self.position_x += (self.target_position_x - self.position_x) * lerp_factor
        self.position_y += (self.target_position_y - self.position_y) * lerp_factor
        self.position_z += (self.target_position_z - self.position_z) * lerp_factor
        
        # Интерполяция масштаба
        self.scale += (self.target_scale - self.scale) * lerp_factor
        
        # Интерполяция вращения
        old_rot_x = self.rotation_x
        old_rot_y = self.rotation_y
        self.rotation_x += (self.target_rotation_x - self.rotation_x) * lerp_factor
        self.rotation_y += (self.target_rotation_y - self.rotation_y) * lerp_factor
        
        if abs(self.rotation_x - old_rot_x) > 0.1 or abs(self.rotation_y - old_rot_y) > 0.1:
            logger.debug(f"Обновление вращения: rot_x={self.rotation_x:.2f}, rot_y={self.rotation_y:.2f}")
        
        # Обновляем виджет
        self.update()
    
    def set_gestures_active(self, active: bool):
        """Включение/выключение управления жестами"""
        self.gestures_active = active
        if not active:
            # Сброс целевых значений при отключении
            self.target_position_x = 0.0
            self.target_position_y = 0.0
            self.target_scale = 1.0
            self.left_hand_data = None
            self.right_hand_data = None
        logger.info(f"Управление жестами: {'активно' if active else 'неактивно'}")
    
    def reset_transformations(self):
        """Сброс всех трансформаций к начальным значениям"""
        self.rotation_x = 15.0  # Начальный наклон для 3D вида
        self.rotation_y = 25.0  # Начальный поворот для 3D вида
        self.rotation_z = 0.0
        self.target_rotation_x = 15.0
        self.target_rotation_y = 25.0
        
        self.position_x = 0.0
        self.position_y = 0.0
        self.position_z = -9.0  # Увеличено с -7.0 до -9.0
        self.target_position_x = 0.0
        self.target_position_y = 0.0
        self.target_position_z = -9.0  # Увеличено с -7.0 до -9.0
        
        self.scale = 1.0
        self.target_scale = 1.0
        
        self.left_hand_data = None
        self.right_hand_data = None
        
        self.update()
        logger.info("Трансформации сброшены")
    
    def set_object_type(self, obj_type: str):
        """
        Установка типа 3D объекта
        
        Args:
            obj_type: Тип объекта ('cube', 'sphere', 'pyramid', 'torus', 'cone', 'cylinder')
        """
        valid_types = ['cube', 'sphere', 'pyramid', 'torus', 'cone', 'cylinder']
        if obj_type in valid_types:
            self.object_type = obj_type
            logger.info(f"Тип объекта изменен на: {obj_type}")
            self.update()
        else:
            logger.warning(f"Недопустимый тип объекта: {obj_type}")
    
    # === МЕТОДЫ РАСШИРЕННОЙ КАСТОМИЗАЦИИ ===
    
    def set_cube_color(self, face: str, color: list):
        """
        Установка цвета грани куба
        
        Args:
            face: Название грани ('front', 'back', 'top', 'bottom', 'left', 'right')
            color: Список RGBA значений [r, g, b, a] (0.0-1.0)
        """
        if face in self.cube_colors and len(color) >= 3:
            self.cube_colors[face] = color[:4]  # Берем первые 4 значения
            logger.info(f"Цвет грани {face} изменен на {color}")
            self.update()
    
    def set_object_color(self, base_color: list, secondary_color: list = None):
        """
        Установка основного цвета объекта
        
        Args:
            base_color: Основной цвет [r, g, b, a]
            secondary_color: Вторичный цвет для градиента (опционально)
        """
        if len(base_color) >= 3:
            self.object_base_color = base_color[:4]
            if secondary_color and len(secondary_color) >= 3:
                self.object_secondary_color = secondary_color[:4]
            logger.info(f"Цвет объекта изменен на {base_color}")
            self.update()
    
    def set_material_properties(self, shininess: float = None, specular: list = None):
        """
        Настройка свойств материала
        
        Args:
            shininess: Блеск материала (0-128)
            specular: Цвет бликов [r, g, b, a]
        """
        if shininess is not None:
            self.material_shininess = max(0.0, min(128.0, shininess))
        if specular and len(specular) >= 3:
            self.material_specular = specular[:4]
        logger.info(f"Материал обновлен: shininess={self.material_shininess}")
        self.update()
    
    def toggle_wireframe(self):
        """Переключение каркасного режима"""
        self.wireframe_mode = not self.wireframe_mode
        logger.info(f"Каркасный режим: {'включен' if self.wireframe_mode else 'выключен'}")
        self.update()
    
    def toggle_grid(self):
        """Переключение отображения сетки"""
        self.show_grid = not self.show_grid
        logger.info(f"Сетка: {'включена' if self.show_grid else 'выключена'}")
        self.update()
    
    def toggle_axes(self):
        """Переключение отображения осей координат"""
        self.show_axes = not self.show_axes
        logger.info(f"Оси координат: {'включены' if self.show_axes else 'выключены'}")
        self.update()
    
    def toggle_auto_rotate(self):
        """Переключение автоматического вращения"""
        self.auto_rotate = not self.auto_rotate
        logger.info(f"Автовращение: {'включено' if self.auto_rotate else 'выключено'}")
    
    def set_auto_rotate_speed(self, speed: float):
        """
        Установка скорости автовращения
        
        Args:
            speed: Скорость вращения (0.1-5.0)
        """
        self.auto_rotate_speed = max(0.1, min(5.0, speed))
        logger.info(f"Скорость автовращения: {self.auto_rotate_speed:.2f}")
    
    def set_base_size(self, size: float):
        """
        Установка базового размера объекта
        
        Args:
            size: Размер (0.1-1.0)
        """
        self.base_size = max(0.1, min(1.0, size))
        logger.info(f"Базовый размер объекта: {self.base_size:.2f}")
        self.update()
    
    def reset_customization(self):
        """Сброс всех настроек кастомизации к значениям по умолчанию"""
        # Сброс цветов куба
        self.cube_colors = {
            'front': [0.2, 0.4, 1.0, 1.0],
            'back': [1.0, 0.2, 0.2, 1.0],
            'top': [0.2, 1.0, 0.3, 1.0],
            'bottom': [1.0, 1.0, 0.2, 1.0],
            'left': [0.2, 1.0, 1.0, 1.0],
            'right': [1.0, 0.2, 1.0, 1.0]
        }
        
        # Сброс основных цветов
        self.object_base_color = [0.4, 0.5, 0.95, 1.0]
        self.object_secondary_color = [0.2, 0.3, 0.8, 1.0]
        
        # Сброс материала
        self.material_shininess = 80.0
        self.material_specular = [1.0, 1.0, 1.0, 1.0]
        
        # Сброс режимов
        self.wireframe_mode = False
        self.show_grid = True
        self.show_axes = False
        self.auto_rotate = False
        self.auto_rotate_speed = 0.5
        self.base_size = 0.3
        
        logger.info("Все настройки кастомизации сброшены")
        self.update()
    
    def closeEvent(self, event):
        """Обработка закрытия виджета"""
        self.update_timer.stop()
        super().closeEvent(event)
