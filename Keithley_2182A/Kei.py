import pyvisa
from datetime import datetime
import time
from PyQt6.QtCore import QObject, pyqtSignal

class KeithleyError(Exception):
    """Класс для ошибок Keithley 2182A"""
    pass

class Keithley2182A(QObject):
    """
    Класс для управления нановольтметром Keithley 2182A через GPIB
    """
    new_measurement = pyqtSignal(float, dict)  # (timestamp, data)
    error_occurred = pyqtSignal(str)

    def __init__(self, gpib_address="GPIB0::10::INSTR"):
        super().__init__()
        self.gpib_address = gpib_address
        self.rm = None
        self.device = None
        self.is_measuring = False
        self.config = {
            'range': 10,        # Диапазон измерения (В)
            'nplc': 1,          # Скорость измерений (NPLC)
            'trigger_source': 'BUS'
        }

    def connect(self):
        """Подключение к прибору"""
        try:
            self.rm = pyvisa.ResourceManager()
            self.device = self.rm.open_resource(self.gpib_address)
            self.device.timeout = 5000  # Таймаут 5 секунд
            self._configure_device()
            return True
        except pyvisa.errors.VisaIOError as e:
            self.error_occurred.emit(f"Ошибка подключения: {str(e)}")
            return False

    def _configure_device(self):
        """Настройка параметров прибора"""
        if not self.device:
            raise KeithleyError("Прибор не подключен")

        self.device.write("*RST")  # Сброс настроек
        self.device.write(f":SENS:FUNC 'VOLT:DC'")
        self.device.write(f":SENS:VOLT:DC:RANGE {self.config['range']}")
        self.device.write(f":SENS:VOLT:DC:NPLC {self.config['nplc']}")
        self.device.write(f":TRIG:SOUR {self.config['trigger_source']}")

    def set_config(self, param, value):
        """Установка параметров конфигурации"""
        if param in self.config:
            self.config[param] = value
            if self.device:
                self._configure_device()
        else:
            raise KeithleyError(f"Недопустимый параметр конфигурации: {param}")

    def start_measurements(self, interval=0.1):
        """Запуск цикла измерений"""
        if not self.device:
            self.error_occurred.emit("Прибор не подключен")
            return

        self.is_measuring = True
        try:
            while self.is_measuring:
                start_time = time.time()
                
                # Синхронное измерение
                self.device.write("*TRG")
                voltage = float(self.device.query(":READ?"))
                
                # Формирование данных
                timestamp = time.time()
                data = {
                    'voltage': voltage,
                    'unit': 'V',
                    'range': self.config['range'],
                    'status': 'OK'
                }
                
                self.new_measurement.emit(timestamp, data)
                
                # Поддержание интервала измерений
                sleep_time = interval - (time.time() - start_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except Exception as e:
            self.error_occurred.emit(f"Ошибка измерения: {str(e)}")
        finally:
            self.stop_measurements()

    def stop_measurements(self):
        """Остановка измерений"""
        self.is_measuring = False

    def single_measurement(self):
        """Одиночное измерение"""
        if not self.device:
            raise KeithleyError("Прибор не подключен")
        
        self.device.write("*TRG")
        return float(self.device.query(":READ?"))

    def close(self):
        """Корректное отключение прибора"""
        if self.device:
            self.stop_measurements()
            self.device.close()
            self.device = None

    def __del__(self):
        self.close()







keithley = Keithley2182A(gpib_address="GPIB0::10::INSTR")
keithley.connect()

if keithley.device:  # проверяем атрибут device объекта keithley
    print('Успешное подключение к Keithley 2182A')
else:
    print('Не удалось подключиться к Keithley 2182A')