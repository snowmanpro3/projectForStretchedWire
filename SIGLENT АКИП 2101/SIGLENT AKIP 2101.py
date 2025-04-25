import pyvisa
from time import sleep

def connect_to_multimeter():
    """Установка соединения с мультиметром"""
    rm = pyvisa.ResourceManager()
    
    # Поиск подключенных устройств
    resources = rm.list_resources()
    if not resources:
        raise Exception("Не найдены подключенные устройства")
    
    print("Найдены устройства:", resources)
    
    # Попробуем подключиться к первому найденному устройству
    multimeter = rm.open_resource(resources[0])
    print(f"Подключено к: {multimeter.query('*IDN?').strip()}")  # query('*IDN?') запрашивает и возвращает модель устройства
    # Метод strip() удаляет пробелы и служебные символы (например, переносы строк \n, табуляцию \t) в начале и в конце строки.
    multimeter.write("CONF:TEMP THER, KITS90")
    print(multimeter.query("SENS:TEMP:TRAN?"))

    return multimeter

def configure_thermocouple(multimeter, thermocouple_type='KITS90'):  # KITS90 : ITS90 - международный стандарт, K - хромель-алюмель
    """Настройка мультиметра для измерения температуры термопарой"""
    # Выбор функции измерения температуры
    multimeter.write(f"CONF:TEMP THER,{thermocouple_type}")
    
    # Установка единиц измерения (C - градусы Цельсия)
    multimeter.write("UNIT:TEMP C")
    
    # Включение автоматического выбора диапазона
    multimeter.write("SENS:TEMP:RANG:AUTO ON")
    
    # Проверка конфигурации
    config = multimeter.query("CONF?")
    print(f"Текущая конфигурация: {config.strip()}")

def measure_temperature(multimeter, num_readings=1, delay=1.0):
    """Измерение температуры"""
    temperatures = []
    
    for _ in range(num_readings):
        try:
            # Запрос измерения температуры
            temp = multimeter.query("MEAS:TEMP? THER, KITS90") #!ЗДЕСЬ ЗАДАЁТСЯ ТИП ТЕРМОПАРЫ, А НЕ СВЕРХУ!!!
            temperatures.append(float(temp))
            
            if num_readings > 1:
                sleep(delay)  # Задержка между измерениями
        except Exception as e:
            error = multimeter.query('SYST:ERR?')
            print(f'Ошибка: {error}')
    
    return temperatures if num_readings > 1 else temperatures[0]

def main():
    try:
        # Подключение к мультиметру
        dmm = connect_to_multimeter()
        
        # Настройка для термопары типа K (можно изменить на другой тип)
        thermocouple_type = 'KITS90'  # Доступные типы: BITS90,EITS90,JITS90,KITS90,NITS90,RITS90,SITS90,TITS90
        configure_thermocouple(dmm, thermocouple_type)
        
        # Измерение температуры (5 измерений с интервалом 1 секунда)
        print("\nИзмерение температуры...")
        temps = measure_temperature(dmm, num_readings=5, delay=1.0) 
        
        # Вывод результатов
        print("\nРезультаты измерений:")
        for i, temp in enumerate(temps, 1):
            print(f"Измерение {i}: {temp:.2f} °C")
        
        # Среднее значение
        if len(temps) > 1:
            avg_temp = sum(temps) / len(temps)
            print(f"\nСредняя температура: {avg_temp:.2f} °C")
    
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        # Закрытие соединения
        if 'dmm' in locals():
            dmm.close()
            print("Соединение с мультиметром закрыто")

if __name__ == "__main__":
    main()