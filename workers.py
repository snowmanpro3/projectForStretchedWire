from PyQt6.QtCore import QThread, pyqtSignal
import acsc_modified as acsc
import time
import numpy as np


class SingleAxisWorker(QThread):
    """Поток для опроса одной оси с максимальной частотой"""
    update_signal = pyqtSignal(int, float, bool, bool)  # axis_id, position, moving, in_position
    error_signal = pyqtSignal(int, str)  # axis_id, error_message
    progress_signal = pyqtSignal(str)  # To send informational messages (like dual_print)

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
    progress_signal = pyqtSignal(str)  # To send informational messages (like dual_print)

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
            self.progress_signal.emit(f"Ошибка при запуске синхронного движения: {e}")
            print(f"Ошибка при запуске синхронного движения: {e}")
        else:
            self.progress_signal.emit(f"Функция acsc.toPointM выполнена без ошибок, нить выведена на старт")
            print(f"Функция acsc.toPointM выполнена без ошибок, нить выведена на старт")
        time.sleep(0.2) #! Чтобы контроллер успел увидеть остановку оси???
        try:    
            distances = [self.distance, self.distance]
            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(self.ffi_axes), tuple(distances), acsc.SYNCHRONOUS)
            time.sleep(0.2)
            #*acsc.toPointM сама добавляет -1 в конец списка осей
        except Exception as e:
            self.progress_signal.emit(f"Ошибка при запуске основного синхронного движения: {e}")
            print(f"Ошибка при запуске основного синхронного движения: {e}")
        else:
            self.progress_signal.emit(f"Измерение FFI успешно запущено, идёт измерение...")
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
    progress_signal = pyqtSignal(str)  # To send informational messages (like dual_print)

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
            self.progress_signal.emit(f"Ошибка при запуске синхронного движения: {e}")
            print(f"Ошибка при запуске синхронного движения: {e}")
        else:
            self.progress_signal.emit(f"Функция acsc.toPointM выполнена без ошибок, нить выведена на старт")
            print(f"Функция acsc.toPointM выполнена без ошибок, нить выведена на старт")
        time.sleep(0.2) #! Чтобы контроллер успел увидеть остановку оси???

        try:    
            distances = [self.distance, -self.distance]
            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(self.sfi_axes), tuple(distances), acsc.SYNCHRONOUS)
            #*acsc.toPointM сама добавляет -1 в конец списка осей
        except Exception as e:
            self.progress_signal.emit(f"Ошибка при запуске основного синхронного движения: {e}")
            print(f"Ошибка при запуске основного синхронного движения: {e}")
        else:
            self.progress_signal.emit(f"Измерение FFI успешно запущено, идёт измерение...")
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


class FindMagneticAxisWorker(QThread):
    # Signals to communicate with the main GUI thread
    progress_signal = pyqtSignal(str)  # To send informational messages (like dual_print)
    error_signal = pyqtSignal(str)    # To send error messages (like show_error)
    finished_signal = pyqtSignal(dict) # To send the final axis positions upon completion
    # Optional: intermediate_results_signal = pyqtSignal(str, str, float) # scan_type, mode, coordinate

    def __init__(self, stand, keithley, distance, speed, convergence_threshold, max_iterations):
        super().__init__()
        self.stand = stand
        self.keithley = keithley
        self.distance = distance
        self.speed = speed
        self.convergence_threshold = convergence_threshold
        self.max_iterations = max_iterations
        self.running = True
        self.L_wire = 2.0 # Wire length for SFI, or pass as parameter

    def _perform_scan_and_center_worker(self, scan_type, mode, axes_pair, move_distance, current_speed):
        # This method is adapted from ACSControllerGUI._perform_scan_and_center
        master = axes_pair[0]
        slave = axes_pair[1] # Used for SFI pair, FFI effectively uses master for logging

        try:
            for axis_id in axes_pair:
                # Ensure axis is enabled - direct call to controller
                acsc.enable(self.stand.hc, axis_id) # Or self.stand.axes[axis_id].enable() if newACS wraps it
                # Set speed - direct call to controller
                acsc.setSPeed(self.stand.hc, axis_id, current_speed) # Or self.stand.axes[axis_id].set_speed()

            self.progress_signal.emit(f"Скорость {current_speed} мм/с установлена для осей {axes_pair}.")

            log_data_points = {'time': [], 'eds': []}
            if scan_type == "FFI":
                log_data_points['pos'] = [] # For master axis position
            elif scan_type == "SFI":
                log_data_points['pos_0'] = [] # Master axis
                log_data_points['pos_1'] = [] # Slave axis
            
            self.progress_signal.emit(f"Подготовка к сканированию {scan_type} по оси {mode}...")
            if scan_type == "FFI":
                initial_moves = [-(move_distance / 2.0), -(move_distance / 2.0)]
                scan_moves = [move_distance, move_distance]
            elif scan_type == "SFI":
                initial_moves = [-(move_distance / 2.0), (move_distance / 2.0)]
                scan_moves = [move_distance, -move_distance]
            else:
                self.error_signal.emit(f"Неизвестный тип сканирования: {scan_type}")
                return None

            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(axes_pair), tuple(initial_moves), acsc.SYNCHRONOUS)
            acsc.waitMotionEnd(self.stand.hc, master, 30000) 
            time.sleep(0.2)
            self.progress_signal.emit(f"Перемещение на начальную точку сканирования {scan_type} {mode} завершено.")

            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(axes_pair), tuple(scan_moves), acsc.SYNCHRONOUS)
            self.progress_signal.emit(f"Начало сканирования {scan_type} {mode} ({move_distance} мм)...")

            scan_start_time = time.time()
            poll_interval = 0.1 
            max_log_duration = (move_distance / current_speed) * 1.5 + 10 # Increased buffer
            log_end_time = time.time() + max_log_duration

            while time.time() < log_end_time and self.running:
                pos_m = acsc.getFPosition(self.stand.hc, master)
                eds_v = self.keithley.get_voltage() # Assumes keithley object has get_voltage()
                current_t_rel = time.time() - scan_start_time

                log_data_points['time'].append(current_t_rel)
                log_data_points['eds'].append(eds_v)
                if scan_type == "FFI":
                    log_data_points['pos'].append(pos_m)
                elif scan_type == "SFI":
                    log_data_points['pos_0'].append(pos_m)
                    pos_s = acsc.getFPosition(self.stand.hc, slave)
                    log_data_points['pos_1'].append(pos_s)

                mot_state = acsc.getMotorState(self.stand.hc, master)
                if mot_state['in position']:
                    self.progress_signal.emit(f"Сканирование {scan_type} {mode}: Движение завершено, сбор данных остановлен.")
                    break
                time.sleep(poll_interval)
            else: 
                if not self.running:
                    self.progress_signal.emit(f"Сканирование {scan_type} {mode} прервано.")
                    acsc.killAll(self.stand.hc, acsc.SYNCHRONOUS)
                    return None
                self.progress_signal.emit(f"Сканирование {scan_type} {mode}: Превышено время ожидания сбора данных.")
                acsc.killAll(self.stand.hc, acsc.SYNCHRONOUS) # Ensure motion is stopped

            if not log_data_points['time'] or not log_data_points['eds']:
                self.progress_signal.emit(f"Нет данных для обработки {scan_type} {mode}.")
                return None

            min_coord = None
            # Get initial positions for calculating absolute target
            # These are absolute positions *before* this scan's centering move
            initial_pos_master_abs = acsc.getFPosition(self.stand.hc, master)
            initial_pos_slave_abs = acsc.getFPosition(self.stand.hc, slave)

            # Store initial absolute positions from before the scan's relative moves.
            # The `toPointM` for initial_moves was relative.
            # To get the absolute coordinate of the scan start:
            # Get current position, then subtract the scan_moves[0]/2 (or similar logic based on how you define 0)
            # Simpler: Use the recorded positions. The recorded 'pos' or 'pos_0' are already absolute.
            
            scan_path_abs_positions = np.array(log_data_points.get('pos', log_data_points.get('pos_0', [])))
            if len(scan_path_abs_positions) == 0:
                 self.error_signal.emit(f"Нет данных о позиции для {scan_type} {mode}.")
                 return None

            if scan_type == "FFI":
                integral_values = np.array(log_data_points['eds']) / current_speed
                min_id = np.argmin(np.abs(integral_values))
                min_coord_abs = scan_path_abs_positions[min_id]
            elif scan_type == "SFI":
                integral_values = (np.array(log_data_points['eds']) * self.L_wire) / (2.0 * current_speed)
                min_id = np.argmin(np.abs(integral_values))
                min_coord_abs = scan_path_abs_positions[min_id] # SFI minimum refers to master axis's absolute position

            self.progress_signal.emit(f"{scan_type} {mode}: Мин. значение интеграла ({integral_values[min_id]:.4e}) на абсолютной коорд. {min_coord_abs:.4f}")
            
            self.progress_signal.emit(f"Центрирование осей {axes_pair} на новой абсолютной координате {min_coord_abs:.4f}...")
            
            # Calculate relative moves to reach the absolute min_coord_abs from current positions
            current_pos_master_ax_abs = acsc.getFPosition(self.stand.hc, master)
            current_pos_slave_ax_abs = acsc.getFPosition(self.stand.hc, slave)

            move_master_rel = min_coord_abs - current_pos_master_ax_abs
            move_slave_rel = min_coord_abs - current_pos_slave_ax_abs # Both axes go to the same absolute coordinate

            centering_distances = [move_master_rel, move_slave_rel]
            # If axes_pair contains X axes (e.g., [1,3]), centering_distances will be [dx1, dx3]
            # If axes_pair contains Y axes (e.g., [0,2]), centering_distances will be [dy0, dy2]

            acsc.toPointM(self.stand.hc, acsc.AMF_RELATIVE, tuple(axes_pair), tuple(centering_distances), acsc.SYNCHRONOUS)
            acsc.waitMotionEnd(self.stand.hc, master, 30000)
            time.sleep(0.2)

            final_pos_master_abs = acsc.getFPosition(self.stand.hc, master)
            final_pos_slave_abs = acsc.getFPosition(self.stand.hc, slave)
            self.progress_signal.emit(f"{scan_type} {mode}: Оси перемещены. Итоговые позиции: {master}={final_pos_master_abs:.4f}, {slave}={final_pos_slave_abs:.4f} (цель была {min_coord_abs:.4f})")
            
            return min_coord_abs # Return the absolute coordinate found

        except Exception as e:
            self.error_signal.emit(f"Ошибка в _perform_scan_and_center_worker ({scan_type} {mode}): {str(e)}")
            # import traceback
            # self.progress_signal.emit(traceback.format_exc()) # For detailed debugging
            return None

    def run(self):
        self.progress_signal.emit(f"Запуск поиска магнитной оси: Дистанция={self.distance} мм, Скорость={self.speed} мм/с")

        current_iteration = 0
        
        # Log initial positions from the worker's perspective
        pos_data_initial = {}
        for i in range(4): # Assuming 4 axes
            pos_data_initial[f"axis_{i}_initial_pos"] = acsc.getFPosition(self.stand.hc, i)
        self.progress_signal.emit(f"Начальные позиции (0,1,2,3): ({pos_data_initial['axis_0_initial_pos']:.4f}, {pos_data_initial['axis_1_initial_pos']:.4f}, {pos_data_initial['axis_2_initial_pos']:.4f}, {pos_data_initial['axis_3_initial_pos']:.4f})")

        last_positions = {i: acsc.getFPosition(self.stand.hc, i) for i in range(4)}

        while current_iteration < self.max_iterations and self.running:
            self.progress_signal.emit(f"\n--- Итерация {current_iteration + 1} ---")
            
            iter_start_positions = {i: acsc.getFPosition(self.stand.hc, i) for i in range(4)}
            self.progress_signal.emit(
                f"Позиции в начале итерации {current_iteration + 1} (0,1,2,3): "
                f"({iter_start_positions[0]:.4f}, {iter_start_positions[1]:.4f}, "
                f"{iter_start_positions[2]:.4f}, {iter_start_positions[3]:.4f})"
            )

            # 1. FFI по X (axes 1, 3)
            if not self.running: break
            self.progress_signal.emit("Шаг 1: FFI по X...")
            new_x_center = self._perform_scan_and_center_worker('FFI', 'X', [1, 3], self.distance, self.speed)
            if new_x_center is None: self.progress_signal.emit("Ошибка в FFI X. Остановка."); break
            self.progress_signal.emit(f"FFI X: Новый целевой центр X = {new_x_center:.4f}")

            # 2. FFI по Y (axes 0, 2)
            if not self.running: break
            self.progress_signal.emit("Шаг 2: FFI по Y...")
            new_y_center = self._perform_scan_and_center_worker('FFI', 'Y', [0, 2], self.distance, self.speed)
            if new_y_center is None: self.progress_signal.emit("Ошибка в FFI Y. Остановка."); break
            self.progress_signal.emit(f"FFI Y: Новый целевой центр Y = {new_y_center:.4f}")

            # 3. SFI по X (axes 1, 3)
            if not self.running: break
            self.progress_signal.emit("Шаг 3: SFI по X...")
            new_x_center = self._perform_scan_and_center_worker('SFI', 'X', [1, 3], self.distance, self.speed)
            if new_x_center is None: self.progress_signal.emit("Ошибка в SFI X. Остановка."); break
            self.progress_signal.emit(f"SFI X: Новый целевой центр X = {new_x_center:.4f}")

            # 4. SFI по Y (axes 0, 2)
            if not self.running: break
            self.progress_signal.emit("Шаг 4: SFI по Y...")
            new_y_center = self._perform_scan_and_center_worker('SFI', 'Y', [0, 2], self.distance, self.speed)
            if new_y_center is None: self.progress_signal.emit("Ошибка в SFI Y. Остановка."); break
            self.progress_signal.emit(f"SFI Y: Новый целевой центр Y = {new_y_center:.4f}")

            current_positions = {i: acsc.getFPosition(self.stand.hc, i) for i in range(4)}
            self.progress_signal.emit(
                f"Позиции после итерации {current_iteration + 1} (0,1,2,3): "
                f"({current_positions[0]:.4f}, {current_positions[1]:.4f}, "
                f"{current_positions[2]:.4f}, {current_positions[3]:.4f})"
            )

            deltas = {i: abs(current_positions[i] - iter_start_positions[i]) for i in range(4)} # Мб убрать abs
            self.progress_signal.emit(f"Изменения за итерацию (Δ0,Δ1,Δ2,Δ3): "
                                      f"({deltas[0]:.4f}, {deltas[1]:.4f}, {deltas[2]:.4f}, {deltas[3]:.4f})")

            converged = all(deltas[i] < self.convergence_threshold for i in range(4))
            
            if converged:
                self.progress_signal.emit(f"Схождение достигнуто на итерации {current_iteration + 1}. Магнитная ось найдена.")
                break
            
            last_positions = current_positions
            current_iteration += 1
        
        if not self.running:
             self.progress_signal.emit("Поиск магнитной оси прерван пользователем.")
        elif current_iteration == self.max_iterations and not converged:
            self.progress_signal.emit(f"Достигнуто максимальное количество итераций ({self.max_iterations}) без схождения.")

        final_positions = {f"axis_{i}": acsc.getFPosition(self.stand.hc, i) for i in range(4)}
        self.progress_signal.emit(f"Финальные координаты концов нити (0,1,2,3):")
        self.progress_signal.emit(f"  Ось 0 (Y1): {final_positions['axis_0']:.4f} мм")
        self.progress_signal.emit(f"  Ось 1 (X1): {final_positions['axis_1']:.4f} мм")
        self.progress_signal.emit(f"  Ось 2 (Y2): {final_positions['axis_2']:.4f} мм")
        self.progress_signal.emit(f"  Ось 3 (X2): {final_positions['axis_3']:.4f} мм")
        
        self.finished_signal.emit(final_positions)

    def stop(self):
        self.running = False
        self.progress_signal.emit("Получен сигнал остановки...")
        # Optionally, if scans involve blocking calls that don't check self.running,
        # you might need to use acsc.killAll here if immediate stop is critical.
        # However, _perform_scan_and_center_worker already has a self.running check in its loop.