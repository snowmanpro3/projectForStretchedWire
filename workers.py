from PyQt6.QtCore import QThread, pyqtSignal
import acsc_modified as acsc
import time


class SingleAxisWorker(QThread):
    """Поток для опроса одной оси с максимальной частотой"""
    update_signal = pyqtSignal(int, float, bool, bool)  # axis_id, position, moving, in_position
    error_signal = pyqtSignal(int, str)  # axis_id, error_message

    def __init__(self, stand, axis_id):
        super().__init__()
        self.stand = stand      # Ссылка на контроллер ACS
        self.axis_id = axis_id  # ID оси (0, 1, 2, 3)
        self.running = False    # Флаг работы потока

    def run(self):
        """Основной цикл потока
        Код внутри этого метода выполняется в отдельном потоке, когда вызывается worker.start()
        """
        self.running = True
        while self.running:
            try:
                # Получаем данные оси
                pos = self.stand.axes[self.axis_id].get_pos()
                axis_state = acsc.getAxisState(self.stand.hc, self.axis_id)
                mot_state = acsc.getMotorState(self.stand.hc, self.axis_id)
                
                # Отправляем в главный поток
                self.update_signal.emit(
                    self.axis_id,
                    pos,
                    axis_state['moving'],
                    mot_state['in position']
                )
            except Exception as e:
                self.error_signal.emit(self.axis_id, str(e))
            
            self.msleep(100)  # Пауза 10 мс (можно уменьшить для более частого опроса)
            #! Здесь определяется частота обновления позиций

    def stop(self):
        """Корректная остановка потока"""
        self.running = False
        self.wait(500)  # Ожидаем завершения (таймаут 500 мс)


class FFIMeasurementWorker(QThread):
    log_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, stand, axes, keithley, distance, speed, mode):
        super().__init__()
        self.stand = stand
        self.axes = axes
        self.keithley = keithley
        self.distance = distance
        self.speed = speed
        self.mode = mode
        self.running = True

    def run(self):
        try:
            master = self.axes[0]
            log = {
                'time': [],
                'x_pos': [],
                'y_pos': [],
                'eds': [],
            }
            start_time = time.time()
            while self.running:
                pos = acsc.getFPosition(self.stand.hc, master)
                eds = self.keithley.get_voltage()
                log['time'].append(time.time() - start_time)
                log['eds'].append(eds)
                if self.mode == 'X':
                    log['x_pos'].append(pos)
                    log['y_pos'].append(0.0)
                else:
                    log['y_pos'].append(pos)
                    log['x_pos'].append(0.0)

                state = acsc.getMotorState(self.stand.hc, master)
                if state['in position']:
                    break
                time.sleep(0.1)
            self.log_ready.emit(log)
        except Exception as e:
            self.error.emit(str(e))


class SFIMeasurementWorker(QThread):
    log_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, stand, axes, keithley, distance, speed, mode):
        super().__init__()
        self.stand = stand
        self.axes = axes
        self.keithley = keithley
        self.distance = distance
        self.speed = speed
        self.mode = mode
        self.running = True

    def run(self):
        try:
            master = self.axes[0]
            log = {
                'time': [],
                'x_pos_0': [],
                'x_pos_1': [],
                'y_pos_0': [],
                'y_pos_1': [],
                'eds': [],
            }
            start_time = time.time()
            while self.running:
                pos = acsc.getFPosition(self.stand.hc, master)
                eds = self.keithley.get_voltage()
                log['time'].append(time.time() - start_time)
                log['eds'].append(eds)
                if self.mode == 'X':
                    log['x_pos'].append(pos)
                    log['y_pos'].append(0.0)
                else:
                    log['y_pos'].append(pos)
                    log['x_pos'].append(0.0)

                state = acsc.getMotorState(self.stand.hc, master)
                if state['in position']:
                    break
                time.sleep(0.1)
            self.log_ready.emit(log)
        except Exception as e:
            self.error.emit(str(e))

