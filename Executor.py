# -*- coding: utf-8 -*-
"""
ACS Controller Executable Script
-------------------------------
This script connects to the ACS controller and manages axis positions
"""

from __future__ import division, print_function
import acsc_modified as acsc
import newACS
import time
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QMainWindow, QLineEdit
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QSize


'''
if __name__ == '__main__':
    stand = newACS.newAcsController(newACS.acs_ip, newACS.acs_port, contype="simulator", n_axes=4)
    #Подключён контроллер (simulator поменять на Ethernet) и определены его 4 оси: 0, 1, 2, 3
    for axis in stand.axes:
         print(f"Axis {axis.axisno}: Name = {axis.get_name()}, Pos = {axis.get_pos()}")  #Выводим оси просто посмотреть
    stand.enable_all()
    print('All axes are enabled')
    time.sleep(2)
    stand.axes[0].start(500)
    time.sleep(2)
'''


class ACSControllerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.stand = None
        self.axis_states = [False] * 4  # Хранит состояние осей
        self.initUI()

    def initUI(self):
        self.setWindowTitle('ACS Controller')
        self.setGeometry(100, 100, 400, 200)  #Размеры и положения окошка приложухи на экране
        
        layout = QVBoxLayout()
        
        # Подключение к контроллеру
        conn_layout = QHBoxLayout()
        self.connect_button = QPushButton('Подключиться к контроллеру')
        self.connect_button.clicked.connect(self.connect_to_controller)  #Здесь передаём функцию, которая выполнится при клике на кнопку
        conn_layout.addWidget(self.connect_button)
        
        self.status_label = QLabel('Отключено')
        self.status_label.setStyleSheet('color: red')
        conn_layout.addWidget(self.status_label)
        
        self.status_icon = QLabel('🔴')
        conn_layout.addWidget(self.status_icon)
        
        layout.addLayout(conn_layout)
        
        # Оси
        self.axis_buttons = []
        self.position_labels = []
        self.status_icons = []
        self.speed_inputs = []
        self.speed_labels = []
        
        for i in range(4):
            axis_layout = QHBoxLayout()
            
            enable_button = QPushButton(f'Включить ось {i}')
            enable_button.clicked.connect(lambda checked, ax=i: self.toggle_axis(ax))
            axis_layout.addWidget(enable_button)
            self.axis_buttons.append(enable_button)
            
            status_icon = QLabel('🔴')
            axis_layout.addWidget(status_icon)
            self.status_icons.append(status_icon)
            
            pos_button = QPushButton(f'Позиция оси {i}')
            pos_button.clicked.connect(lambda checked, ax=i: self.get_position(ax))
            axis_layout.addWidget(pos_button)
            
            pos_label = QLabel('Pos: ---')
            axis_layout.addWidget(pos_label)
            self.position_labels.append(pos_label)
            
            # Поле для ввода скорости
            speed_input = QLineEdit()
            speed_input.setPlaceholderText('Скорость')
            speed_input.setFixedWidth(80)
            axis_layout.addWidget(speed_input)
            self.speed_inputs.append(speed_input)
            
            # Кнопка "Применить" для установки скорости
            apply_speed_button = QPushButton('Применить')
            apply_speed_button.clicked.connect(lambda checked, ax=i: self.set_speed(ax))
            axis_layout.addWidget(apply_speed_button)
            
            # Метка для отображения текущей скорости
            speed_label = QLabel('Скорость: ---')
            axis_layout.addWidget(speed_label)
            self.speed_labels.append(speed_label)

            #Тестовое перемещение
            move_forward_button = QPushButton(f'Вперёд на 500 (ось {i})')
            move_forward_button.clicked.connect(lambda checked, ax=i: self.move_axis(ax, 500))
            axis_layout.addWidget(move_forward_button)
            
            move_backward_button = QPushButton(f'Назад на 500 (ось {i})')
            move_backward_button.clicked.connect(lambda checked, ax=i: self.move_axis(ax, -500))
            axis_layout.addWidget(move_backward_button)

            layout.addLayout(axis_layout)
        
        self.setLayout(layout)
    
    def connect_to_controller(self):
            self.stand = newACS.newAcsController(newACS.acs_ip, newACS.acs_port, contype='Ethernet', n_axes=4)
            if self.stand.connect() == -1:
                self.status_label.setText('Ошибка подключения')
                self.status_label.setStyleSheet('color: red')
                self.status_icon.setText('🔴')
            else:
                self.status_label.setText('Подключено')
                self.status_label.setStyleSheet('color: green')
                self.status_icon.setText('🟢')
                #self.stand.enable_all()
    
    def toggle_axis(self, axis):
        if self.stand:
            if self.axis_states[axis]:
                self.stand.axes[axis].disable()
                self.axis_buttons[axis].setText(f'Включить ось {axis}')
                self.axis_buttons[axis].setStyleSheet('background-color:')
                self.status_icons[axis].setText('🔴')
            else:
                self.stand.axes[axis].enable()
                self.axis_buttons[axis].setText(f'Ось {axis} включена')
                self.axis_buttons[axis].setStyleSheet('background-color: green')
                self.status_icons[axis].setText('🟢')
            self.axis_states[axis] = not self.axis_states[axis]
    
    def get_position(self, axis):
        if self.stand:
            if self.axis_states[axis]:  # Проверка, включена ли ось
                pos = self.stand.axes[axis].get_pos()
                self.position_labels[axis].setText(f'Pos: {pos:.2f}')
            else:
                self.position_labels[axis].setText('Pos: ---')  # Если ось выключена, позиция не отображается
                
    def move_axis(self, axis, distance):
        if self.stand and self.axis_states[axis]:  # Проверка, включена ли ось
            current_pos = self.stand.axes[axis].get_pos()
            target_pos = current_pos + distance
            self.stand.axes[axis].start(target_pos)
            self.get_position(axis)  # Обновляем позицию после перемещения


if __name__ == '__main__':
    app = QApplication(sys.argv)  #Аргументы для доступа к командной строке???
    window = ACSControllerGUI()
    window.show()
    sys.exit(app.exec())