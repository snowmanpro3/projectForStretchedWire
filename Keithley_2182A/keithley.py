import pyvisa
import threading
import time

class Keithley2182A:
    def __init__(self, resource: str = "GPIB0::7::INSTR", mode: str = "meas"):
        assert mode in ("fetch", "meas"), "mode должен быть 'fetch' или 'meas'"
        self.mode = mode
        self.rm = pyvisa.ResourceManager()
        self.inst = self.rm.open_resource(resource)
        self.inst.timeout = 2000  # мс

        self.inst.write("*RST")
        self.inst.write("*CLS")
        self.inst.write(":SYST:AZER OFF")  # Выключить автообнуление (ускоряет)
        self.inst.write(f":SENS:CHAN 2")
        self.inst.write(":SENS:FUNC 'VOLT'")
        self.inst.write(":VOLT:NPLC 0.01")  # Быстрое измерение
        self.inst.write(":FORM:ELEM READ")  # Только значение

        self.inst.write(":TRIG:SOUR IMM")   # Немедленный триггер
        self.inst.write(":TRIG:COUNT INF")
        self.inst.write(":INIT:CONT ON")

    def get_voltage(self) -> float:
        """
        Получает значение ЭДС в вольтах.
        - В режиме 'fetch': читает последнее доступное измерение
        - В режиме 'meas': запускает новое измерение и ждёт результат
        """
        try:
            return float(self.inst.query(":FETCH?").strip())
        except Exception as e:
            print(f"[!] Ошибка при получении ЭДС: {e}")
            return float("nan")

    def close(self):
        """Закрывает соединение с вольтметром"""
        self.keithley.close()
        self.rm.close()



    '''Дальнейшие функции только для тестов/диагностики. Запускать только из этого файла'''


    def keithley2182A():
        try:
            # Создаем менеджер ресурсов VISA
            rm = pyvisa.ResourceManager()
            print(rm.list_resources())  #! Выведет список доступных приборов
            
            # Пытаемся подключиться к Keithley 2182A (адрес GPIB обычно 7)
            keithley = rm.open_resource("GPIB0::7::INSTR")
            
            keithley.timeout = 3000  # Устанавливаем таймаут для запроса (в миллисекундах)
            
            response = keithley.query("*IDN?") # Отправляем команду идентификации
            
            voltage = keithley.query(":READ?") # Чтение текущего измерения
            print(f"Текущее напряжение: {voltage} В")
            # Закрываем соединение
            keithley.close()
            
            # Проверяем ответ
            if "KEITHLEY INSTRUMENTS INC.,MODEL 2182A" in response:
                print(f"Успешное подключение! Ответ прибора:\n{response}")
                return True
            else:
                print(f"Подключено неизвестное устройство. Ответ:\n{response}")
                return False
                
        except pyvisa.errors.VisaIOError as e:
            print(f"Ошибка подключения: {e}")
            return False
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return False

if __name__ == '__main__':
    nano = Keithley2182A(resource="GPIB0::7::INSTR", mode='meas')
    # print(k.keithley.supports_event())  # должно быть True (проверка поддержки SRQ)
    start_time = time.time()
    poll_interval = 0.05
    pos_log = []
    N = 0
    while N < 15:
        eds = nano.get_voltage()                                # Получем ЭДС с keithley
        print(eds, time.time() - start_time)
        N += 1
        time.sleep(poll_interval)                                    # Пауза между опросами



