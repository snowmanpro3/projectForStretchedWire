# -*- coding: utf-8 -*-
"""
ACS Controller Executable Script
-----------------------------------
This script connects to the ACS controller and manages axis positions
"""

from __future__ import division, print_function
import acsc_modified as acsc
import newACS
from Calculation import Calculations as calc #!КАК ИМПОРТИРОВАТЬ
from Keithley_2182A.keithley import Keithley2182A as ktl
import time
from PyQt6 import QtGui
import io
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QPlainTextEdit, QTabWidget
from PyQt6.QtGui import QTextCursor, QColor
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal, QThread, pyqtSlot
# Импортируем сгенерированный класс. Команда: pyuic6 GUI_for_controller_with_tabs2.ui -o GUI_for_controller_with_tabs2.py
from GUI_for_controller_with_tabs2 import Ui_MainWindow
from workers import SingleAxisWorker, FFIMeasurementWorker, SFIMeasurementWorker
import numpy as np
import csv
import matplotlib.pyplot as plt
import traceback


class ACSControllerGUI(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # Инициализация интерфейса
        self.stand = None
        self.axis_workers = {}  # Словарь: {axis_id: worker}

        # Тестовый вывод
        self.dual_print("Программа запущена!")
        
        # Настройка окна для вывода принтов
        #?? Блок настройки логгера
        self._setup_logger(self.Console)

        self.initTabText()

        # Создаём словари для 4 осей:
        '''Где есть getattr(self, f"чётотам{i}") - это функция, которая возвращает объект QLineEdit для ввода перемещения оси i.'''
        self.axes_data = {
            i: {
                "state": False,
                "speed_input": getattr(self, f"speed_input_{i}"),
                "acceleration_input": getattr(self, f"acceleration_input_{i}"),
                "deceleration_input": getattr(self, f"deceleration_input_{i}"),
                "kill_deceleration_input": getattr(self, f"kill_deceleration_input_{i}"),
                "jerk_input": getattr(self, f"jerk_input_{i}"),
                "axis_state_indicator": getattr(self, f"axis_state_indicator_{i}"),
                "pos_label": getattr(self, f"pos_label_{i}"),
                "is_moving_label": getattr(self, f"is_moving_label_{i}"),
                "is_acc_label": getattr(self, f"is_acc_label_{i}"),
                "is_in_pos_label": getattr(self, f"is_in_pos_label_{i}"),
                "is_in_pos_indicator": getattr(self, f"is_in_pos_indicator_{i}"),
                "choose_axis_button": getattr(self, f"choose_axis_{i}"),
                "enable_axis_button": getattr(self, f"enable_axis_button_{i}"),
                "start_axis_button": getattr(self, f"start_axis_{i}"),
                "move_distance": getattr(self, f"move_by_input_{i}"),
                "current_pos": 0.0,
                "axis_obj": None, #!Здесь хранятся ссылки на ось как объект из модуля newACS, к которым можно применять его методы
                "is_moving_indicator": getattr(self, f"is_moving_indicator_{i}")
            }
            for i in range(4)
        }

        self.connect_ui_elements()                               # Подключаем функции к элементам интерфейса
        self.selected_axes = []

        # self.pos_timer = QTimer(self)                            # Таймер для обновления current_pos
        # self.pos_timer.setInterval(250)                          # Обновление позиций каждые 250 мс
        # self.pos_timer.timeout.connect(self.update_positions)    # Вызываем функцию update_positions каждый период таймера

    def connect_ui_elements(self):                               # Кнопки общего действия: старт, стоп, ресет
        self.connect_button.clicked.connect(self.connect_to_controller)
        self.reset_button.clicked.connect(self.set_default_values)
        self.zeropos_button.clicked.connect(self.zeropos_axes)
        self.start_choosen_axis_button.clicked.connect(self.startM)
        self.stop_button.clicked.connect(self.stop_all_axes)
        self.stop_button_2.clicked.connect(self.stop_all_axes)
        self.start_mode_motion.clicked.connect(self.check_mode_then_start)
        self.stop_button_test.clicked.connect(self.stop_all_axes)
        self.start_mode_motion_test.clicked.connect(self.check_mode_then_start_test)
        self.tab1.currentChanged.connect(self.currentTab)
        self.findMagAxes_button.clicked.connect(self.findMagneticAxis)
        

        for i in range(4):
            '''Перед connect стоит т.н. сигнал, а сам connect связывает сигнал с обработчиком'''
            data = self.axes_data[i]
            data["speed_input"].textChanged.connect(lambda text, ax=i: self.set_speed(ax, text))
            data["acceleration_input"].textChanged.connect(lambda text, ax=i: self.set_acceleration(ax, text))
            data["deceleration_input"].textChanged.connect(lambda text, ax=i: self.set_deceleration(ax, text))
            data["kill_deceleration_input"].textChanged.connect(lambda text, ax=i: self.set_kill_deceleration(ax, text))
            data["jerk_input"].textChanged.connect(lambda text, ax=i: self.set_jerk(ax, text))
            data["move_distance"].textChanged.connect(lambda text, ax=i: self.set_move_distance(ax, text))
            data["enable_axis_button"].clicked.connect(lambda checked, ax=i: self.toggle_axis(ax))
            data["start_axis_button"].clicked.connect(lambda checked, ax=i: self.start(ax))
            data["choose_axis_button"].stateChanged.connect(lambda state, ax=i: self.update_selected_axes(ax, state))

    def set_default_values(self): # Выставляет дефолтные параметры движения осей в общем окне
        for i in range(4):
            axis = self.axes_data[i]
            axis["speed_input"].setText("0.2")
            axis["acceleration_input"].setText("100")
            axis["deceleration_input"].setText("100")
            axis["kill_deceleration_input"].setText("166.67")
            axis["jerk_input"].setText("133.33")
    
    def dual_print(self, message, log_window=None):
        """
        Основной метод вывода:
        - message: текст сообщения
        - print(): вывод в консоль
        - appendPlainText(): вывод в GUI
        - _auto_scroll(): прокрутка вниз
        """
        if log_window == None:
            log_window = self.Console
        print(message)  # Консольный вывод
        log_window.appendPlainText(message)  # GUI-вывод
        self._auto_scroll(log_window)  # Автопрокрутка

    def _setup_logger(self, log_window=None):
        """Приватный метод для настройки логгера"""
        if log_window == None:
            log_window = self.Console
        # 1. Делаем лог только для чтения
        log_window.setReadOnly(True)
        
        # 2. Отключаем перенос строк (удобно для логов)
        log_window.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # 3. Опционально: задаем шрифт с фиксированной шириной
        font = log_window.font()
        font.setFamily("Courier New")  # Моноширинный шрифт
        log_window.setFont(font)

    def _auto_scroll(self, log_window):
        """Приватный метод для автопрокрутки"""
        cursor = log_window.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        log_window.setTextCursor(cursor)

    def clear_logs(self, log_window=None):
        """Очистка лога"""
        if log_window == None:
            log_window = self.Console
        log_window.clear()

#!МБ ЭТО УБРАТЬ И СДЕЛАТЬ ЧЕРЕЗ ДИЗАЙНЕР
    def initTabText(self):
        # current_tab = self.tab1.currentIndex()   # Объект текущего окна
        # current_tab_name = self.tab1.tabText(current_tab)  # Название текущего окна
        
        self.tablePosition.item(0, 0).setText(f"{0}")
        self.tablePosition.item(1, 0).setText(f"{1}") # 4.15151:.3f
        self.tablePosition.item(2, 0).setText(f"{2}")
        self.tablePosition.item(3, 0).setText(f"{3}")

    def zeropos_axes(self):
        self.axes_data[0]["axis_obj"].set_pos(0)
        self.axes_data[1]["axis_obj"].set_pos(0)
        self.axes_data[2]["axis_obj"].set_pos(0)
        self.axes_data[3]["axis_obj"].set_pos(0)
        pass

    def connect_to_controller(self):
        """Подключается к контроллеру. Инициализирует оси как объекты в ключе 'axis_obj """
        self.stand = newACS.newAcsController(newACS.acs_ip, newACS.acs_port, contype='Ethernet', n_axes=4)
        if self.stand.connect() == -1:
            self.show_error("Ошибка подключения к контроллеру")
            self.label.setStyleSheet('background-color: red')
            self.stand = None
        else:
            self.label.setStyleSheet('background-color: green')
            # self.set_default_values() # Устанавливаем дефолтные значения при успешном подключении
            for i in range(4):        # После успешного подключения обновляем ссылки на оси в словарях
                self.axes_data[i]["axis_obj"] = self.stand.axes[i]
                

    def toggle_axis(self, axis):
        """Включает/выключает ось. Присваивает ключу 'state' значение True или False"""
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return
        
        data = self.axes_data[axis] #! Короткая ссылка
        if data["state"]:
            data['axis_obj'].disable()
            data["axis_state_indicator"].setStyleSheet('background-color: red')
            data["state"] = False
        else:
            data['axis_obj'].enable()
            data["axis_state_indicator"].setStyleSheet('background-color: green')
            data["state"] = True

    def update_selected_axes(self, axis, state):
        """Обновляет список выбранных осей."""
        state = Qt.CheckState(state) # Эта строка преобразует число в понятное для Qt значение (мб 'checked')
        if state == Qt.CheckState.Checked:  # Если галочка поставлена
            if axis not in self.selected_axes:
                self.selected_axes.append(axis)
                self.selected_axes = sorted(self.selected_axes)
                print('Добавили в список')
        if state == Qt.CheckState.Unchecked:  # Если галочка снята
            if axis in self.selected_axes:
                self.selected_axes.remove(axis)
                print('Удалили из списка')
        print(f'Список выбранных осей: {self.selected_axes}')

    def set_speed(self, axis, text):
        if not self.stand:
            # self.show_error("Контроллер не подключён!")
            return
        
        data = self.axes_data[axis]
        try:
            speed = float(text)
            data['axis_obj'].set_speed(speed) # Передаём значение в контроллер
            data["speed"] = speed # Сохраняем скорость в словаре для оси `axis`
        except ValueError:
            self.show_error("Некорректный ввод скорости")

    def set_acceleration(self, axis, text):
        if not self.stand:
            # self.show_error("Контроллер не подключён!")
            return
        
        data = self.axes_data[axis]
        try:
            acceleration = float(text)
            data['axis_obj'].set_acceleration(acceleration) # Это другая set_acceleration из модуля newACS
            data["acceleration"] = acceleration  # Сохраняем ускорение в словаре для оси `axis`
        except ValueError:
            self.show_error("Некорректный ввод скорости")

    def set_deceleration (self, axis, text):
        if not self.stand:
            # self.show_error("Контроллер не подключён!")
            return
        
        data = self.axes_data[axis]
        try:
            deceleration = float(text)
            data['axis_obj'].set_deceleration(deceleration) # Передаём значение в контроллер
            data["deceleration"] = deceleration  # Сохраняем замедление в словаре для оси `axis`
        except ValueError:
            self.show_error("Некорректный ввод скорости")

    def set_kill_deceleration (self, axis, text):
        if not self.stand:
            # self.show_error("Контроллер не подключён!")
            return

        data = self.axes_data[axis]
        try:
            kill_deceleration = float(text)
            data['axis_obj'].set_kill_deceleration(kill_deceleration) # Передаём значение в контроллер
            data["kill_deceleration"] = kill_deceleration  # Сохраняем замедление в словаре для оси `axis`
        except ValueError:
            self.show_error("Некорректный ввод скорости")

    def set_jerk(self, axis, text):
        if not self.stand:
            # self.show_error("Контроллер не подключён!")
            return

        data = self.axes_data[axis]
        try:
            jerk = float(text)
            data['axis_obj'].set_jerk(jerk) # Передаём значение в контроллер
            data["jerk"] = jerk  # Сохраняем рывок в словаре для оси `axis`
        except ValueError:
            self.show_error("Некорректный ввод скорости")

    def set_move_distance(self, axis, text):
        if not self.stand:
            # self.show_error("Контроллер не подключён!")
            return

        data = self.axes_data[axis]
        try:
            distance = float(text)
            data["move_distance"] = distance
        except ValueError:
            self.show_error("Некорректный ввод перемещения")

    def start(self, axis):
        '''Простое перемещение одной оси (тестовое)'''
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return
        
        self.oneAxisLog = {  # Инициализация лога
            'time': [],
            'pos': [],
        }

        data = self.axes_data[axis]
        if data['state'] and axis in self.selected_axes:
            try:
                '''Здесь amf_relative - это флаг, который указывает, что перемещение будет относительным.'''
                acsc.toPoint(self.stand.hc, acsc.AMF_RELATIVE, axis, data['move_distance'], acsc.SYNCHRONOUS)
                data["is_in_pos_indicator"].setStyleSheet("background-color:rgb(255, 0, 0)")
                self.start_position_updates()
            except Exception as e:
                self.show_error(f"Ошибка при запуске движения оси {axis}: {e}")
        else:
            self.show_error(f"Ось {axis} не включена или не выбрана!")

    def startM(self):
        '''Синхронный старт движения выбранныхосей'''
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return
        
        self.dual_print(f"Открытая вкладка: {self.tab1.tabText(self.tab1.currentIndex())}")
        data = self.axes_data
        move_distances = []
        self.startpointM = data[self.selected_axes[0]]['axis_obj'].get_pos()
        leader = self.selected_axes[0]
        for i in self.selected_axes:
            if data[i]['state'] and data[i]['move_distance'] != 0:
                move_distances.append(data[i]['move_distance'])
        try:
            '''
            Здесь функция toPointM вызывается напрямую из модуля acsc_modified
            ТАМ УЖЕ ДОБАВЛЯЕТСЯ -1 В КОНЦЕ СПИСКА ОСЕЙ!!!!!!!!!!!!
            Здесь acsc.AMF_RELATIVE - это флаг, который указывает, что перемещение будет относительным.
            '''
            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(self.selected_axes), tuple(move_distances), acsc.SYNCHRONOUS)
            for i in self.selected_axes:
                data[i]["is_in_pos_indicator"].setStyleSheet("background-color:rgb(255, 0, 0)")
            print('Успешно запущенно движение осей')
            # Запускаем таймер обновления позиций
            self.start_position_updates()
        except Exception as e:
            self.show_error(f"Ошибка при запуске движения: {e}")

    def stop_all_axes(self):
        """Останавливает все оси."""
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return

        try:
            acsc.killAll(self.stand.hc, acsc.SYNCHRONOUS)
        except Exception as e:
            self.show_error(f"Ошибка при остановке осей: {e}")

    def show_error(self, message):
        """Показывает сообщение об ошибке."""
        QMessageBox.critical(self, "Ошибка", message)

    def currentTab(self):
        self.currentTab = self.tab1.currentIndex()
        self.currentTabName = self.tab1.tabText(self.currentTab)
        self.dual_print(f'Вкладка переключена на "{self.currentTabName}"')

    def start_position_updates(self):
        """Запуск отдельного потока для каждой выбранной оси"""
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return

        for axis_id in self.selected_axes:
            # Останавливаем предыдущий поток оси, если был
            if axis_id in self.axis_workers:
                self.axis_workers[axis_id].stop()

            # Создаём и настраиваем новый поток
            worker = SingleAxisWorker(self.stand, axis_id)
            worker.update_signal.connect(self.handle_axis_update)
            '''"Когда worker излучит update_signal, вызови мой метод handle_axis_update и передай ему данные из сигнала"'''
            worker.error_signal.connect(self.handle_axis_error)
            worker.start()
            
            self.axis_workers[axis_id] = worker

    def stop_position_updates(self):
        """Остановка всех потоков осей"""
        for axis_id, worker in self.axis_workers.items():
            worker.stop()
        self.axis_workers.clear()

    @pyqtSlot(int, float, bool, bool) 
    def handle_axis_update(self, axis_id, pos, moving, in_pos):
        """Обновление данных оси в GUI (выполняется в главном потоке)"""
        axis_data = self.axes_data[axis_id]

        # current_tab = self.tab1.currentIndex()   # Объект текущего окна
        # current_tab_name = self.tab1.tabText(current_tab)  # Название текущего окна
        #! Тут остановился!!!

        if self.currentTabName == "Settings":  # Замените на актуальное название вкладки
            # Обновляем значения
            axis_data["pos_label"].setText(f"Позиция: {pos:.4f} мм")
            axis_data["is_moving_label"].setText(f"Движение: {'Да' if moving else 'Нет'}")
            axis_data["is_in_pos_label"].setText(f"На месте: {'Да' if in_pos else 'Нет'}")

            # Меняем цвет индикаторов
            moving_color = "rgb(0, 128, 0)" if moving else "rgb(255, 0, 0)"  # Красный/Зелёный
            in_pos_color = "rgb(0, 128, 0)" if in_pos else "rgb(255, 0, 0)"
            
            axis_data["is_moving_indicator"].setStyleSheet(f"background-color: {moving_color}")
            axis_data["is_in_pos_indicator"].setStyleSheet(f"background-color: {in_pos_color}")

        elif self.currentTabName == "Выбор режимов движения":
            self.tablePosition.item(axis_id, 1).setText(f"Позиция: {pos:.4f} мм")

    @pyqtSlot(int, str)
    def handle_axis_error(self, axis_id, error_msg):
        """Обработка ошибок оси"""
        self.show_error(f"Ось {axis_id}: {error_msg}")
        if axis_id in self.axis_workers:
            self.axis_workers[axis_id].stop()

    def closeEvent(self, event):
        """Остановка потоков при закрытии окна"""
        self.stop_position_updates()
        super().closeEvent(event)

    def findMagAxis(self):
        '''
        Сначала необходимо на странице настроек/управления расположить нить на
        предополагаемую магнитную ось (на глаз)
        '''
        #! x-компонента (СНАЧАЛА довести до ума первый и второй интеграл, т.к. нахождение оси с их помощью)
        pass



    #TODO добавить провекру на совпадение координат противположных осей???
    def start_circular_motion(self): #! ПОКА ЧТО НАЧИНАЕТ ДВИЖЕНИЕ ИЗ ТОЧКИ ГДЕ СЕЙЧАС НАХОДИТСЯ
        """
        Запускает движение нити по окружности с заданными параметрами.
        Концы нити всегда находятся в одних и тех же координатах.
        """
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return

        # Инициализация лога координат
        self.circular_motion_log = {
            'time': [],
            'theta': [],
            'x_pos': [],
            'y_pos': [],
            'eds':[],
        }
        self.start_time = time.time()
        vector_velocity = float(self.circ_speed_input.text())
        radius = float(self.circ_radius_input.text())

        axesM = [0, 1, 2, 3]  # List of axes to move (all) for toPointM
        leader = axesM[0]

        center_x = self.axes_data[1]["axis_obj"].get_pos()  # Получаем текущую позицию оси 1
        center_y = self.axes_data[0]["axis_obj"].get_pos()  # Получаем текущую позицию оси 0
        circle_angle_rad = 2*np.pi  # Whole circle
        center_point = [center_x, center_y]
        center_points = [center_y, center_x, center_y, center_x]

        start_x = center_x + radius
        start_y = center_y
        start_point = [start_x, start_y]
        start_points = [start_y, start_x, start_y, start_x]

        self.stand.enable_all()  # Включаем все оси перед движением
        acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, axesM, start_points, acsc.SYNCHRONOUS)
        acsc.waitMotionEnd(self.stand.hc, leader, 30000)
        print('Прибыла в начальную точку')

        try:
            acsc.extendedSegmentedMotionV2(self.stand.hc, acsc.AMF_VELOCITY,
                                        axesM, start_points,
                                        vector_velocity, #? Tangential velocity 😎😎😎!!!!! (мб 10 мм/с)
                                        acsc.NONE, # EndVelocity
                                        acsc.NONE, # JunctionVelocity
                                        acsc.NONE, # Angle
                                        acsc.NONE, # CurveVelocity
                                        acsc.NONE, # Deviation
                                        radius, # Radius
                                        acsc.NONE, # MaxLength
                                        acsc.NONE, # StarvationMargin
                                        None,      # Segments (имя массива, если нужно > 50 сегм.)
                                        acsc.NONE, # ExtLoopType
                                        acsc.NONE, # MinSegmentLength
                                        acsc.NONE, # MaxAllowedDeviation
                                        acsc.NONE, # OutputIndex
                                        acsc.NONE, # BitNumber
                                        acsc.NONE, # Polarity
                                        acsc.NONE, # MotionDelay
                                        None       # Wait (синхронный вызов планирования)
                                        )
        except Exception as e:
            print(f"Ошибка при запуске движения по окружности (extendedSegmentedMotionV2)")
        
        try:
            '''Добавляем дугу (360 градусов окружнсоть) 😊😊😊😊😊'''
            acsc.segmentArc2V2(self.stand.hc,
                               acsc.AMF_VELOCITY,
                               axesM,
                               center_points,
                               circle_angle_rad,
                               None,           # FinalPoint (для вторичных осей, если есть)
                               vector_velocity,      #? Using the previous velosity we input
                               acsc.NONE,      # EndVelocity 
                               acsc.NONE,      # Time
                               None,           # Values (для user variables)
                               None,           # Variables (для user variables)
                               acsc.NONE,      # Index (для user variables)
                               None,           # Masks (для user variables)
                               acsc.NONE,      # ExtLoopType
                               acsc.NONE,      # MinSegmentLength
                               acsc.NONE,      # MaxAllowedDeviation
                               acsc.NONE,      # LciState
                               None            # Wait (синхронный вызов планирования)
                               )
        except Exception as e:
            print(f"Ошибка при добавлении дуги (acsc.segmentArc2V2)")
        
        try:
            acsc.endSequenceM(self.stand.hc, axesM, None)
            '''The function informs the controller, that no more points 
        or segments will be specified for the current multi-axis motion.
        Эта функция сигнализирует контроллеру: "Все, описание траектории закончено.
        Больше сегментов не будет.'''
        except Exception as e:
            print(f"Ошибка при завершении сегмента (acsc.endSequenceM)")
        
        acsc.waitMotionEnd(self.stand.hc, leader, 30000)
        print('Прибыла в начальную точку')
        

    def start_ffi_motion(self):
        """Проверяет режим движения и запускает соответствующий метод."""
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return
        
        #! МОЖНО СДЕЛАТЬ QDoubleValidator и автоматическую замену запятой на точку
        try:
            distance = float(self.ffi_distance_input.text())
        except ValueError:
            self.show_error("Ошибка: введите число через точку")
            self.ffi_distance_input.setText('0.0')
            distance = 0.0  # или другое значение по умолчанию
        else:
            self.dual_print(f"Дистанция успешно введена и установлена")

        try:
            mode = (self.ffi_mode_input.text())
            if mode and distance != 0:
                if mode == 'X':
                    ffi_axes = [1,3]
                    self.selected_axes = ffi_axes
                    for axis in ffi_axes:
                        if not self.axes_data[axis]["state"]:
                            self.axes_data[axis]['axis_obj'].enable()
                            self.axes_data[axis]["state"] = True
                elif mode == 'Y':
                    ffi_axes = [0,2]
                    self.selected_axes = ffi_axes
                    for axis in ffi_axes:
                        if not self.axes_data[axis]["state"]:
                            self.axes_data[axis]['axis_obj'].enable()
                            self.axes_data[axis]["state"] = True
        except Exception as e:
            self.show_error("Ошибка: Введите капсом 'X' или 'Y'")
        else:
            self.dual_print(f"Мод успешно выбран")

        try:
            speed = float(self.ffi_speed_input.text())
            for axis in ffi_axes:  # Задаём скорость осям с поля ввода
                    self.axes_data[axis]['axis_obj'].set_speed(speed)
        except ValueError:
            self.show_error(" Ошибка: Что-то со скоростью мб")
        else:
            self.dual_print(f"Скорость успешно введена и установлена")

        try:
            nano = ktl(resource="GPIB0::7::INSTR", mode='meas')              #! Создаём экземпляр класса Keithley2182A
        except Exception as e:
            self.dual_print("Ошибка подключения к Keithley")
        else:
            self.dual_print("Успешное подключение к Keithley")

        
        self.ffi_worker = FFIMeasurementWorker(self.stand, ffi_axes, nano, distance, speed, mode)
        self.ffi_worker.log_ready.connect(self.handle_ffi_log)
        self.ffi_worker.error.connect(lambda msg: self.show_error(f"FFI ошибка: {msg}"))
        self.ffi_worker.start()
        self.start_position_updates()
        self.dual_print(f"Измерение FFI успешно запущено, идёт измерение...")

    @pyqtSlot(dict)
    def handle_ffi_log(self, log):
        # self.ffi_motion_log = log
        fig = calc.firstFieldIntegral(log, self.ffi_worker.mode, self.ffi_worker.speed)

        try:
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(buf.getvalue())
            buf.close()
            plt.close(fig)

            self.plot_pic.setPixmap(pixmap)
            self.plot_pic.setScaledContents(True)
            self.dual_print("График отображён в QLabel")
        except Exception as e:
            self.show_error(f"Ошибка отображения графика: {e}")
            if fig:
                plt.close(fig)

        
    def start_sfi_motion(self):
        """Проверяет режим движения и запускает соответствующий метод."""
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return
        
        #! МОЖНО СДЕЛАТЬ QDoubleValidator и автоматическую замену запятой на точку
        try:
            distance = float(self.sfi_distance_input.text())
        except ValueError:
            self.show_error("Ошибка: введите число через точку")
            self.sfi_distance_input.setText('0.0')
            distance = 0.0  # или другое значение по умолчанию
        else:
            self.dual_print(f"Дистанция успешно введена и установлена")

        try:
            mode = (self.sfi_mode_input.text())
            if mode and distance != 0:
                if mode == 'X':
                    sfi_axes = [1,3]
                    master = sfi_axes[0]
                    slave = sfi_axes[1]
                    for axis in sfi_axes:
                        if not self.axes_data[axis]["state"]:
                            self.axes_data[axis]['axis_obj'].enable()
                            self.axes_data[axis]["state"] = True
                elif mode == 'Y':
                    sfi_axes = [0,2]
                    master = sfi_axes[0]
                    slave = sfi_axes[1]
                    for axis in sfi_axes:
                        if not self.axes_data[axis]["state"]:
                            self.axes_data[axis]['axis_obj'].enable()
                            self.axes_data[axis]["state"] = True
        except Exception as e:
            self.show_error("Ошибка: Введите капсом 'X' или 'Y'")
        else:
            self.dual_print(f"Мод успешно выбран")

        try:
            speed = float(self.sfi_speed_input.text())
            for axis in sfi_axes:  # Задаём скорость осям с поля ввода
                    self.axes_data[axis]['axis_obj'].set_speed(speed)
        except ValueError:
            self.show_error(" Ошибка: Что-то со скоростью мб")
        else:
            self.dual_print(f"Скорость успешно введена и установлена")
        
        try:
            nano = ktl(resource="GPIB0::7::INSTR", mode='meas')              #! Создаём экземпляр класса Keithley2182A
        except Exception as e:
            self.dual_print("Ошибка подключения к Keithley")
        else:
            self.dual_print("Успешное подключение к Keithley")

        self.fi_worker = SFIMeasurementWorker(self.stand, sfi_axes, nano, distance, speed, mode)
        self.fi_worker.log_ready.connect(self.handle_sfi_log)
        self.fi_worker.error.connect(lambda msg: self.show_error(f"SFI ошибка: {msg}"))
        self.fi_worker.start()
        self.start_position_updates()
        self.dual_print(f"Измерение SFI успешно запущено, идёт измерение...")
            
    @pyqtSlot(dict)
    def handle_sfi_log(self, log):
        fig = calc.secondFieldIntegral(log, self.sfi_worker.mode, self.sfi_worker.speed)
            
        try:
            # 1. Создаем буфер в памяти
            buf = io.BytesIO()
            # 2. Сохраняем фигуру в буфер в формате PNG
            #    dpi можно подобрать для нужного размера/качества на экране (напр. 96)
            fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0) # Перемещаем указатель в начало буфера

            # 3. Загружаем данные из буфера в QPixmap
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(buf.getvalue())
            buf.close() # Закрываем буфер

            # !!! ВАЖНО: Закрываем фигуру Matplotlib после использования, чтобы освободить память !!!
            plt.close(fig)

            # 4. Устанавливаем QPixmap в ваш QLabel
            self.plot_pic.setPixmap(pixmap)
            # (Опционально) Масштабируем изображение под размер QLabel
            self.plot_pic.setScaledContents(True)
            print("График отображен в QLabel.")
        except Exception as e:
            self.show_error(f"Неизвестная ошибка в calc.sevondFieldIntegral или отображении графика: {e}")
            if fig: plt.close(fig) # Закрыть фигуру и при других ошибках


    def check_mode_then_start(self):
        """Проверяет режим движения и запускает соответствующий метод."""
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return
        
        selected_mode = self.check_mode.currentText()
        print(f"Нажата кнопка 'Старт', выбран режим: {selected_mode}")

        if selected_mode == "По окружности":
            self.start_circular_motion()
        elif selected_mode == "Первый магнитный интеграл":
            self.start_ffi_motion()
        elif selected_mode == "Второй магнитный интеграл":  #Todo добавить возврат в ноль мб
            self.start_sfi_motion()


    def _perform_scan_and_center(self, scan_type, mode, axes_pair, distance, speed, nano):
        master = axes_pair[0]
        slave = axes_pair[1] # Used for SFI pair, FFI effectively uses master for logging

        for axis_id in axes_pair:
            if not self.axes_data[axis_id]["state"]:
                self.axes_data[axis_id]['axis_obj'].enable() #
                self.axes_data[axis_id]["state"] = True #
                self.dual_print(f"Ось {axis_id} включена.")
            self.axes_data[axis_id]['axis_obj'].set_speed(speed) #
        self.dual_print(f"Скорость {speed} мм/с установлена для осей {axes_pair}.")

        log_data_points = {'time': [], 'eds': []}
        if scan_type == "FFI":
            log_data_points['pos'] = [] # For master axis position
        elif scan_type == "SFI":
            log_data_points['pos_0'] = [] # Master axis
            log_data_points['pos_1'] = [] # Slave axis
        
        # --- Motion Sequence ---
        self.dual_print(f"Подготовка к сканированию {scan_type} по оси {mode}...")
        if scan_type == "FFI":
            initial_moves = [-(distance / 2.0), -(distance / 2.0)]
            scan_moves = [distance, distance]
        elif scan_type == "SFI":
            initial_moves = [-(distance / 2.0), (distance / 2.0)]
            scan_moves = [distance, -distance]
        else:
            self.show_error(f"Неизвестный тип сканирования: {scan_type}")
            return None

        acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(axes_pair), tuple(initial_moves), acsc.SYNCHRONOUS) #
        acsc.waitMotionEnd(self.stand.hc, master, 30000) # Increased timeout
        time.sleep(0.2) #
        self.dual_print(f"Перемещение на начальную точку начала сканирования {scan_type} {mode} завершено.")

        acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(axes_pair), tuple(scan_moves), acsc.SYNCHRONOUS) #
        self.dual_print(f"Начало сканирования {scan_type} {mode} ({distance} мм)...")
        
        # --- Data Logging ---
        scan_start_time = time.time()
        poll_interval = 0.1 # Poll more frequently for better data
        
        max_log_duration = (distance / speed) * 1.5 + 5 # Estimate max duration + buffer
        log_end_time = time.time() + max_log_duration

        while time.time() < log_end_time:
            pos_m = acsc.getFPosition(self.stand.hc, master) #
            eds_v = nano.get_voltage() #
            current_t_rel = time.time() - scan_start_time

            log_data_points['time'].append(current_t_rel)
            log_data_points['eds'].append(eds_v)
            if scan_type == "FFI":
                log_data_points['pos'].append(pos_m)
            elif scan_type == "SFI":
                log_data_points['pos_0'].append(pos_m)
                pos_s = acsc.getFPosition(self.stand.hc, slave) #
                log_data_points['pos_1'].append(pos_s)

            motor_state_val = acsc.getMotorState(self.stand.hc, master) #
            if motor_state_val['in position']: #
                self.dual_print(f"Сканирование {scan_type} {mode}: Движение завершено, сбор данных остановлен.")
                break
            time.sleep(poll_interval)
        else: # Loop exited due to timeout
            self.dual_print(f"Сканирование {scan_type} {mode}: Превышено время ожидания сбора данных.")
            # Ensure motion is stopped if it didn't complete
            acsc.killAll(self.stand.hc, acsc.SYNCHRONOUS)


        # --- Process Data and Find Minimum ---
        if not log_data_points['time'] or not log_data_points['eds']: # Check if any data was logged
            self.dual_print(f"Нет данных для обработки {scan_type} {mode}. Сканирование могло быть слишком быстрым или коротким.")
            return None
        if scan_type == "FFI" and not log_data_points['pos']:
            self.dual_print(f"Нет данных о позиции для FFI {mode}.")
            return None
        if scan_type == "SFI" and not log_data_points['pos_0']:
            self.dual_print(f"Нет данных о позиции для SFI {mode}.")
            return None

        min_coord = None
        try:
            if scan_type == "FFI":
                integral_values = np.array(log_data_points['eds']) / speed
                positions_abs = np.array(log_data_points['pos'])
                if len(positions_abs) == 0: raise ValueError("Пустой массив позиций для FFI")
                min_id = np.argmin(np.abs(integral_values))
                min_coord = positions_abs[min_id]
            elif scan_type == "SFI":
                L_wire = 2.0 # Should be a class constant or parameter
                integral_values = (np.array(log_data_points['eds']) * L_wire) / (2.0 * speed)
                positions_abs = np.array(log_data_points['pos_0']) # SFI minimum refers to master axis position
                if len(positions_abs) == 0: raise ValueError("Пустой массив позиций для SFI")
                min_id = np.argmin(np.abs(integral_values))
                min_coord = positions_abs[min_id]
            
            self.dual_print(f"{scan_type} {mode}: Мин. интеграла ({integral_values[min_id]:.4e}) на коорд. {min_coord:.4f}")
        except Exception as e:
            self.show_error(f"Ошибка при поиске минимума для {scan_type} {mode}: {e}")
            return None
            
        if min_coord is None:
            self.show_error(f"Не удалось определить координату минимума для {scan_type} {mode}.")
            return None

        # --- Move Axes to Center on the New Minimum Coordinate ---
        self.dual_print(f"Центрирование осей {axes_pair} на новой координате {min_coord:.4f}...")
        current_pos_master_ax = self.axes_data[master]['axis_obj'].get_pos()
        current_pos_slave_ax = self.axes_data[slave]['axis_obj'].get_pos()

        move_master_rel = min_coord - current_pos_master_ax
        move_slave_rel = min_coord - current_pos_slave_ax # Both axes go to the same absolute coordinate

        centering_distances = [move_master_rel, move_slave_rel]
        acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(axes_pair), tuple(centering_distances), acsc.SYNCHRONOUS) #
        acsc.waitMotionEnd(self.stand.hc, master, 30000) #
        time.sleep(0.2)

        # Final check of position
        final_pos_master = self.axes_data[master]['axis_obj'].get_pos()
        final_pos_slave = self.axes_data[slave]['axis_obj'].get_pos()
        self.dual_print(f"{scan_type} {mode}: Оси перемещены. Позиции: {master}={final_pos_master:.4f}, {slave}={final_pos_slave:.4f} (цель была {min_coord:.4f})")
        
        return min_coord # Return the target coordinate for this dimension


    def findMagneticAxis(self):
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return

        try:
            distance = float(self.fma_distance_input.text()) #
            speed = float(self.fma_speed_input.text()) #
        except ValueError:
            self.show_error("Ошибка: введите число через точку для дистанции/скорости.")
            return
        else:
            self.dual_print(f"Поиск магнитной оси: Дистанция={distance} мм, Скорость={speed} мм/с") #

        try:
            # Assuming nano is accessible or initialized here
            # self.nano = ktl(resource="GPIB0::7::INSTR", mode='meas') # Or pass as argument
            if not hasattr(self, 'nano') or self.nano is None: # Simplified Keithley check
                # Initialize self.nano if not done globally or pass it
                self.nano = ktl(resource="GPIB0::7::INSTR", mode='meas') #
            self.dual_print("Успешное подключение к Keithley.") #
        except Exception as e:
            self.dual_print(f"Ошибка подключения к Keithley: {e}") #
            return

        CONVERGENCE_THRESHOLD = 0.05  # mm порог сходимости
        MAX_ITERATIONS = 2
        current_iteration = 0

        # Достаточно вывести начальные положения для информации.
        initial_pos_axis0 = self.axes_data[0]["axis_obj"].get_pos()
        initial_pos_axis1 = self.axes_data[1]["axis_obj"].get_pos()
        initial_pos_axis2 = self.axes_data[2]["axis_obj"].get_pos()
        initial_pos_axis3 = self.axes_data[3]["axis_obj"].get_pos()
        self.dual_print(
                f"Позиции в начале итерации (Axis_0, Axis_1, Axis_2, Axis_3): "
                f"({initial_pos_axis0:.4f}, {initial_pos_axis1:.4f}, "
                f"{initial_pos_axis2:.4f}, {initial_pos_axis3:.4f})"
            )


        while current_iteration < MAX_ITERATIONS:
            self.dual_print(f"\n--- Итерация {current_iteration + 1} ---")

            # Get current X and Y centers before adjustment in this iteration
            # Using master axes as representative of the pair's position for simplicity in reporting start of iter
            iter_start_pos_axis0 = self.axes_data[0]["axis_obj"].get_pos()
            iter_start_pos_axis1 = self.axes_data[1]["axis_obj"].get_pos()
            iter_start_pos_axis2 = self.axes_data[2]["axis_obj"].get_pos()
            iter_start_pos_axis3 = self.axes_data[3]["axis_obj"].get_pos()
            self.dual_print(
                f"Позиции в начале итерации (Axis_0, Axis_1, Axis_2, Axis_3): "
                f"({iter_start_pos_axis0:.4f}, {iter_start_pos_axis1:.4f}, "
                f"{iter_start_pos_axis2:.4f}, {iter_start_pos_axis3:.4f})"
            )

            # 1. FFI по X
            self.dual_print("Шаг 1: FFI по X...")
            # Axes for X are 1 and 3. Master can be 1.
            new_x_center = self._perform_scan_and_center('FFI', 'X', [1, 3], distance, speed, self.nano)
            if new_x_center is None: self.dual_print("Ошибка в FFI X."); return
            self.dual_print(f"FFI X: Новый целевой центр X = {new_x_center:.4f}")

            # 2. FFI по Y
            self.dual_print("Шаг 2: FFI по Y...")
            # Axes for Y are 0 and 2. Master can be 0.
            new_y_center = self._perform_scan_and_center('FFI', 'Y', [0, 2], distance, speed, self.nano)
            if new_y_center is None: self.dual_print("Ошибка в FFI Y."); return
            self.dual_print(f"FFI Y: Новый целевой центр Y = {new_y_center:.4f}")

            # 3. SFI по X
            self.dual_print("Шаг 3: SFI по X...")
            new_x_center = self._perform_scan_and_center('SFI', 'X', [1, 3], distance, speed, self.nano)
            if new_x_center is None: self.dual_print("Ошибка в SFI X."); return
            self.dual_print(f"SFI X: Новый целевой центр X = {new_x_center:.4f}")

            # 4. SFI по Y
            self.dual_print("Шаг 4: SFI по Y...")
            new_y_center = self._perform_scan_and_center('SFI', 'Y', [0, 2], distance, speed, self.nano)
            if new_y_center is None: self.dual_print("Ошибка в SFI Y."); return
            self.dual_print(f"SFI Y: Новый целевой центр Y = {new_y_center:.4f}")

            # Current actual centers after all adjustments in this iteration
            current_pos_axis0 = self.axes_data[0]["axis_obj"].get_pos()
            current_pos_axis1 = self.axes_data[1]["axis_obj"].get_pos()
            current_pos_axis2 = self.axes_data[2]["axis_obj"].get_pos()
            current_pos_axis3 = self.axes_data[3]["axis_obj"].get_pos()
            self.dual_print(
                f"Позиции после завершения итерации (Axis_0, Axis_1, Axis_2, Axis_3): "
                f"({current_pos_axis0:.4f}, {current_pos_axis1:.4f}, {current_pos_axis2:.4f}, {current_pos_axis3:.4f})"
            )

            # For convergence, compare the positions of the primary axes for X and Y movement
            # to their positions at the start of this iteration.
            delta_0 = abs(current_pos_axis0 - iter_start_pos_axis0)
            delta_1 = abs(current_pos_axis1 - iter_start_pos_axis1)
            delta_2 = abs(current_pos_axis2 - iter_start_pos_axis2)
            delta_3 = abs(current_pos_axis3 - iter_start_pos_axis3)
            self.dual_print(f"Изменения за итерацию (ΔAxis_0,ΔAxis_1,ΔAxis_2,ΔAxis_3): "
                            f"({delta_0:.4f}, {delta_1:.4f}, {delta_2:.4f}, {delta_3:.4f})")

            # Проверяем, что изменение КАЖДОЙ оси меньше порога
            converged = (delta_0 < CONVERGENCE_THRESHOLD and
                        delta_1 < CONVERGENCE_THRESHOLD and
                        delta_2 < CONVERGENCE_THRESHOLD and
                        delta_3 < CONVERGENCE_THRESHOLD)
            
            if converged:
                self.dual_print(f"Схождение достигнуто на итерации {current_iteration + 1}.")
                break
            
            current_iteration += 1
        else: # Executed if the loop finished due to MAX_ITERATIONS
            self.dual_print(f"Достигнуто максимальное количество итераций ({MAX_ITERATIONS}).")

        # Сообщаем конечные координаты всех четырех моторов.
        # Эти четыре значения определяют положение нити, которое соответствует найденной магнитной оси.
        final_pos_axis0 = self.axes_data[0]["axis_obj"].get_pos()
        final_pos_axis1 = self.axes_data[1]["axis_obj"].get_pos()
        final_pos_axis2 = self.axes_data[2]["axis_obj"].get_pos()
        final_pos_axis3 = self.axes_data[3]["axis_obj"].get_pos()
        self.dual_print(f"Финальные координаты концов нити, определяющие магнитную ось:")
        self.dual_print(f"  Ось 0 (Y1): {final_pos_axis0:.4f} мм")
        self.dual_print(f"  Ось 1 (X1): {final_pos_axis1:.4f} мм")
        self.dual_print(f"  Ось 2 (Y2): {final_pos_axis2:.4f} мм")
        self.dual_print(f"  Ось 3 (X2): {final_pos_axis3:.4f} мм")


    def circle_test(self):
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return

        # Инициализация лога координат
        self.circular_motion_log = {
            'time': [],
            'x_pos': [],
            'y_pos': [],
        }
        self.start_time = time.time()
        vector_velocity = float(self.circ_speed_input_test.text())
        radius = float(self.circ_radius_input_test.text())

        axesM = [0, 1]
        leader = axesM[0]
        
        center_y = self.axes_data[0]["axis_obj"].get_pos()  # Получаем текущую позицию оси 0
        center_x = self.axes_data[1]["axis_obj"].get_pos()  # Получаем текущую позицию оси 1
        circle_angle_rad = 2*np.pi
        center_points = [center_y, center_x]

        start_x = center_x + radius
        start_y = center_y
        start_points = [start_y, start_x]

        self.stand.enable_all()  # Включаем все оси перед движением
        acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, axesM, start_points, acsc.SYNCHRONOUS)
        acsc.waitMotionEnd(self.stand.hc, leader, 15000)
        self.dual_print('Прибыла в начальную точку')

        #!Радиус самой дуги задается через ее геометрические параметры (центр, угол/конечная точка) в команде segmentArc....
        try:
            acsc.extendedSegmentedMotionV2(self.stand.hc, acsc.AMF_VELOCITY,
                                        axesM, start_points,
                                        vector_velocity, #? Tangential velocity 😎😎😎!!!!! (мб 10 мм/с)
                                        acsc.NONE, # EndVelocity
                                        acsc.NONE, # JunctionVelocity
                                        acsc.NONE, # Angle
                                        acsc.NONE, # CurveVelocity
                                        acsc.NONE, # Deviation
                                        acsc.NONE, # Radius только с флагом ACSC_AMF_CORNERRADIUS
                                        acsc.NONE, # MaxLength
                                        acsc.NONE, # StarvationMargin
                                        acsc.NONE,      # Segments (имя массива, если нужно > 50 сегм.)
                                        acsc.NONE, # ExtLoopType
                                        acsc.NONE, # MinSegmentLength
                                        acsc.NONE, # MaxAllowedDeviation
                                        acsc.NONE, # OutputIndex
                                        acsc.NONE, # BitNumber
                                        acsc.NONE, # Polarity
                                        acsc.NONE, # MotionDelay
                                        None       # Wait (синхронный вызов планирования)
                                        )
        except Exception as e:
            self.dual_print(f"Ошибка при запуске движения по окружности (extendedSegmentedMotionV2): {e}")
            traceback.print_exc()
        else:
            self.dual_print(f"Функция acsc.extendedSegmentedMotionV2 выполнена без ошибок")
        
        #!!!⬇️⬇️⬇️⬇️
        '''
        Ты все еще передаешь флаг acsc.AMF_VELOCITY и значение vector_velocity в функцию acsc.segmentArc2V2. 
        Cкорость для сегмента должна наследоваться от той, что задана в extendedSegmentedMotionV2. 
        Нужно передать 0 во флаги и acsc.NONE (-1) в скорость
        '''
        try:
            '''Добавляем дугу (360 градусов окружнсоть) 😊😊😊😊😊'''
            acsc.segmentArc2V2(self.stand.hc,
                               0,
                               axesM,
                               center_points,
                               circle_angle_rad,
                               None,           # FinalPoint (для вторичных осей, если есть)
                               acsc.NONE,      #? Using the previous velosity we input
                               acsc.NONE,      # EndVelocity 
                               acsc.NONE,      # Time
                               None,           # Values (для user variables)
                               None,           # Variables (для user variables)
                               acsc.NONE,      # Index (для user variables)
                               None,           # Masks (для user variables)
                               acsc.NONE,      # ExtLoopType
                               acsc.NONE,      # MinSegmentLength
                               acsc.NONE,      # MaxAllowedDeviation
                               acsc.NONE,      # LciState
                               None            # Wait (синхронный вызов планирования)
                               )
        except Exception as e:
            self.dual_print(f"Ошибка при добавлении дуги (acsc.segmentArc2V2): {e}")
            traceback.print_exc()
        else:
            self.dual_print(f"Функция acsc.segmentArc2V2 выполнена без ошибок")
        
        try:
            acsc.endSequenceM(self.stand.hc, axesM, None)
            '''The function informs the controller, that no more points 
        or segments will be specified for the current multi-axis motion.
        Эта функция сигнализирует контроллеру: "Все, описание траектории закончено.
        Больше сегментов не будет.'''
        except Exception as e:
            self.dual_print(f"Ошибка при завершении сегмента (acsc.endSequenceM)")
            #!ВОЗМОЖНО СТОИТ ПЕРВУЮ ФУНКЦИЮ ЗАПУСТИТЬ ПОСЛЕДНЕЙ!!!!
        else:
            self.dual_print(f"Функция acsc.endSequenceM выполнена без ошибок")
        
        acsc.waitMotionEnd(self.stand.hc, leader, 30000)
        self.dual_print('Прибыла в начальную точку')


    def check_mode_then_start_test(self):
        """Проверяет режим движения и запускает соответствующий метод."""
        if not self.stand:
            self.show_error("Контроллер не подключён!")
            return
        
        selected_mode = self.check_mode_test.currentText()
        print(f"Нажата кнопка 'Старт', выбран режим: {selected_mode}")

        if selected_mode == "По окружности":
            self.circle_test()
        elif selected_mode == "Первый магнитный интеграл":
            self.ffi_test()
        elif selected_mode == "Второй магнитный интеграл":  #Todo добавить возврат в ноль мб
            self.sfi_test()



if __name__ == '__main__':
    app = QApplication([])
    window = ACSControllerGUI()
    window.show()
    app.exec()
    # window.axisstate()
    # print(ACSControllerGUI.__dict__) # Shows all attributes the object have


# TODO В первой итерации из произвольной точки, выставление оси нужно будет добавить потом