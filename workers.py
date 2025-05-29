from PyQt6.QtCore import QThread, pyqtSignal
import acsc_modified as acsc
import newACS
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
                pos = acsc.getFPosition(self.stand.hc, self.axis_id)
                axis_state = acsc.getAxisState(self.stand.hc, self.axis_id)
                mot_state = acsc.getMotorState(self.stand.hc, self.axis_id)
                
                # Отправляем в главный поток информацию об оси в текущей итерации
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
    pos_new = pyqtSignal(float)

    def __init__(self, stand, axes, keithley, distance, speed, mode):
        super().__init__()
        self.stand = stand
        self.ffi_axes = axes
        self.keithley = keithley
        self.distance = distance
        self.speed = speed
        self.mode = mode
        self.running = True

    def run(self):
        distances = [-(self.distance/2), -(self.distance/2)]
        try:
            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(self.ffi_axes), tuple(distances), acsc.SYNCHRONOUS)
            acsc.waitMotionEnd(self.stand.hc, self.ffi_axes[0], 20000)
        except Exception as e:
            print(f"Ошибка при запуске синхронного движения: {e}")
        else:
            print(f"Функция acsc.toPointM выполнена без ошибок, нить выведена на старт")
        time.sleep(0.2) #! Чтобы контроллер успел увидеть остановку оси???
        try:    
            distances = [self.distance, self.distance]
            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(self.ffi_axes), tuple(distances), acsc.SYNCHRONOUS)
            time.sleep(0.2)
            #*acsc.toPointM сама добавляет -1 в конец списка осей
        except Exception as e:
            print(f"Ошибка при запуске основного синхронного движения: {e}")
        else:
            print(f"Измерение FFI успешно запущено, идёт измерение...")
        try:
            master = self.ffi_axes[0]
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
                log['eds'].append(eds)
                log['time'].append(time.time() - start_time)
                if self.mode == 'X':
                    log['x_pos'].append(pos)
                    log['y_pos'].append(0.0)
                elif self.mode == 'Y':
                    log['y_pos'].append(pos)
                    log['x_pos'].append(0.0)

                mot_state = acsc.getMotorState(self.stand.hc, master)
                if mot_state['in position']:
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
        self.sfi_axes = axes
        self.keithley = keithley
        self.distance = distance
        self.speed = speed
        self.mode = mode
        self.running = True

    def run(self):
        distances = [-(self.distance/2), (self.distance/2)]
        try:
            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(self.sfi_axes), tuple(distances), acsc.SYNCHRONOUS)
            acsc.waitMotionEnd(self.stand.hc, master, 20000)
        except Exception as e:
            print(f"Ошибка при запуске синхронного движения: {e}")
        else:
            print(f"Функция acsc.toPointM выполнена без ошибок, нить выведена на старт")
        time.sleep(0.2) #! Чтобы контроллер успел увидеть остановку оси???

        try:    
            distances = [self.distance, -self.distance]
            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(self.sfi_axes), tuple(distances), acsc.SYNCHRONOUS)
            #*acsc.toPointM сама добавляет -1 в конец списка осей
        except Exception as e:
            print(f"Ошибка при запуске основного синхронного движения: {e}")
        else:
            print(f"Измерение FFI успешно запущено, идёт измерение...")

        try:
            master = self.sfi_axes[0]
            slave = self.sfi_axes[1]
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
                pos_m = acsc.getFPosition(self.stand.hc, master)
                pos_s = acsc.getFPosition(self.stand.hc, slave)
                eds = self.keithley.get_voltage()
                log['time'].append(time.time() - start_time)
                log['eds'].append(eds)
                if self.mode == 'X':
                    log['x_pos_0'].append(pos_m)
                    log['x_pos_1'].append(pos_s)
                    log['y_pos_0'].append(0.0)
                    log['y_pos_1'].append(0.0)
                else:
                    log['y_pos_0'].append(pos_m)
                    log['y_pos_1'].append(pos_s)
                    log['x_pos_0'].append(0.0)
                    log['x_pos_1'].append(0.0)

                state = acsc.getMotorState(self.stand.hc, master)
                if state['in position']:
                    break
                time.sleep(0.1)
            self.log_ready.emit(log)
        except Exception as e:
            self.error.emit(str(e))

