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

        self.inst.write("*RST")                         # Сброс настроек
        self.inst.write(":SYST:AZER OFF")               # Выключаем автообнуление (ускоряет)
        self.inst.write(":VOLT:NPLC 0.01")              # Минимальное время интеграции
        self.inst.write(":TRIG:SOUR IMM")               # Немедленный триггер
        self.inst.write(":FORM:ELEM READ")              # Только значение ЭДС

        if self.mode == "fetch":
            self.inst.write(":TRIG:COUNT INF")          # Бесконечный поток измерений
            self.inst.write(":INIT:CONT ON")            # Запуск непрерывных измерений
        else:
            self.inst.write(":TRIG:COUNT 1")            # Одно измерение на вызов

    def get_voltage(self) -> float:
        """
        Получает значение ЭДС в вольтах.
        - В режиме 'fetch': читает последнее доступное измерение
        - В режиме 'meas': запускает новое измерение и ждёт результат
        """
        try:
            if self.mode == "fetch":
                response = self.inst.query(":FETCH?")
            else:
                response = self.inst.query(":MEAS?")
            return float(response.strip())
        except Exception as e:
            print(f"[!] Ошибка при получении ЭДС ({self.mode}): {e}")
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
    k = Keithley2182A()
    print(k.keithley.supports_event())  # должно быть True (проверка поддержки SRQ)



