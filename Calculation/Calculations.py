import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.integrate import cumulative_trapezoid # Для интегрирования методом трапеций
from scipy.fft import fft, fftfreq
from scipy.signal import get_window  # Добавляем оконную функцию
import warnings
import chardet

def firstFieldIntegral(log: dict, mode: str, vel: float):
    current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    str_current_time = str(current_time)
    save_path_csv = f"Logs\\FFI\\FFIlog_{str_current_time}.csv"  # Путь сохранения в папку FFItest
    
    df = pd.DataFrame(log)
    if mode == 'X':
          pos = df['x_pos']
    elif mode == 'Y':
          pos = df['y_pos']
    df.index.name = 'Index'  # Присваю имя index индексам (создаются автоматически, можно даже отключить)
    df.to_csv(save_path_csv, sep = ',') 

    pos_previous = pos.to_numpy()[:-1]
    time = np.array(df['time'])[1:]
    current_pos = pos.to_numpy()[1:]
    eds = np.array(df['eds'])[1:]
    ffi = eds / vel
    print(len(current_pos), len(ffi))

    fig, ax = plt.subplots()

    save_path = f"testlogs\\FFItest\\FFIgraph_{str_current_time}.png"
        
    ax.plot(current_pos, ffi)
    ax.set_xlabel(f"Координата, {mode}")
    ax.set_ylabel(f"Первый магнитный интеграл, Тл/м")
    ax.set_title('Распределение первого магнитного интеграла')
    ax.grid(which="both", linestyle="--")  # Сетка для удобства

    if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранён как {save_path}")
    
    return fig

def secondFieldIntegral(log: dict, mode : str, vel: float):
    L = 2 # Длина нити
    current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    str_current_time = str(current_time)
    save_path_csv = f"Logs\\SFI\\SFIlog_{str_current_time}.csv"  # Путь сохранения в папку FFItest
    
    df = pd.DataFrame(log)
    if mode == 'X':
          pos_0 = df['x_pos_0']
          pos_1 = df['x_pos_1']
    elif mode == 'Y':
          pos_0 = df['y_pos_0']
          pos_1 = df['y_pos_1']
    df.index.name = 'Index'  # Присваю имя index индексам (создаются автоматически, можно даже отключить)
    df.to_csv(save_path_csv, sep = ',') 

    pos_0_previous = pos_0.to_numpy()[:-1]
    pos_1_previous = pos_1.to_numpy()[:-1]
    time = np.array(df['time'])[1:]
    current_pos_0 = pos_0.to_numpy()[1:]
    current_pos_1 = pos_1.to_numpy()[1:]
    eds = np.array(df['eds'])[1:]
    sfi = eds*L / (2*vel)
    print(len(current_pos_0), len(sfi))

    fig, ax = plt.subplots()

    save_path = f"testlogs\\SFItest\\SFIgraph_{str_current_time}.png"
        
    ax.plot(current_pos_0, sfi)
    ax.set_xlabel(f"Координата, {mode}")
    ax.set_ylabel(f"Первый магнитный интеграл, Тл/м")
    ax.set_title('Распределение первого магнитного интеграла')
    ax.grid(which="both", linestyle="--")  # Сетка для удобства

    if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранён как {save_path}")
    
    return fig


def demoFirstFieldIntegral(X1, X2, vel, eds, save_path=None):
    first_fi = eds / vel #Удалить пустые строки

    # Создаем фигуру перед построением графика
    fig, ax = plt.subplots()
    
    # Строим график зависимости первого магнитного поля от координаты нити (X1, например)
    ax.plot(X1, first_fi)
    ax.set_xlabel('Координата X2 (мм)')
    ax.set_ylabel('Первый интеграл магнитного поля')
    ax.set_title('Зависимость первого интеграла магнитного поля от координаты нити')
    ax.grid(which="both", linestyle="--")  # Сетка для удобства

    if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранён как {save_path}")
    
    return fig


def harmonicAnalysis(X1, X2, Y1, Y2, time, eds, save_path=None):
    vel = []
    vel = (X2 - X1) / time

    # Убираем DC-компоненту (вычитаем среднее значение)
    eds -= np.mean(eds)

    # Применяем оконную функцию Ханна
    window = get_window("hann", len(eds))  # Создаем окно Ханна
    eds *= window  # Применяем окно к сигналу

    # Выполняем преобразование Фурье
    N = len(time)  # Количество точек во временном ряду
    fft_values = fft(eds)  # Преобразование Фурье для ЭДС
    freqs = np.fft.fftfreq(N, d=(time[1] - time[0])) * 2 * np.pi  # Преобразуем в круговую частоту

    # Вычисление амплитуд гармоник
    amplitudes = 2.0 / N * np.abs(fft_values[:N // 2])  # Вычисление модуля спектра

    # Отбрасываем слишком малые амплитуды (шум)
    threshold = 1e-10  # Порог отсечения
    amplitudes[amplitudes < threshold] = np.nan  # Меняем малые значения на NaN, чтобы они не отображались

    # Вывод коэффициентов мультипольного разложения
    for i, amp in enumerate(amplitudes[:10]):  # Перебираем первые 10 гармоник
        print(f"Гармоника {i}: амплитуда = {amp:.3e}")  # Форматируем с одной цифрой после запятой



    fig, ax = plt.subplots()
    
    # Строим график зависимости первого магнитного поля от координаты нити (X1, например)
    ax.plot(freqs[:N // 2], amplitudes)
    ax.xlabel('Круговая частота (рад/с)')
    ax.ylabel('Амплитуда')
    ax.title('Мультипольное разложение ЭДС (логарифмическая шкала)')
    ax.grid(which="both", linestyle="--")  # Сетка для удобства

    if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранён как {save_path}")
    
    return fig

def testFFI(log: dict, mode: str):
    current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    str_current_time = str(current_time)
    save_path_csv = f"testlogs\\FFItest\\FFIlog_{str_current_time}.csv"  # Путь сохранения в папку FFItest
    
    df = pd.DataFrame(log)
    #! Если нужно удалить колонку ЭДС раскоментируй след строку
    df.drop(columns='eds')
    df.index.name = 'Index'  # Присваю имя index индексам (создаются автоматически, можно даже отключить)
    df.to_csv(save_path_csv, sep = ',') 

    x_pos_previous = df['x_pos'].to_numpy()[:-1]
    time = np.array(df['time'])[1:]
    x_pos = df['x_pos'].to_numpy()[1:]
    print(len(time), len(x_pos))

    fig, ax = plt.subplots()

    save_path = f"testlogs\\FFItest\\FFIgraph_{str_current_time}.png"
        
    ax.plot(time, x_pos)
    ax.set_xlabel('Время')
    ax.set_ylabel(f"Координата, {mode}")
    ax.set_title('Зависимость')
    ax.grid(which="both", linestyle="--")  # Сетка для удобства

    if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранён как {save_path}")
    
    return fig


def testSFI(log: dict, mode: str):
    current_time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    str_current_time = str(current_time)
    save_path_csv = f"testlogs\\SFItest\\SFIlog_{str_current_time}.csv"  # Путь сохранения в папку FFItest

    df = pd.DataFrame(log)
    #! Если нужно удалить колонку ЭДС раскоментируй след строку
    df.drop(columns='eds')
    df.index.name = 'Index'  # Присваю имя index индексам (создаются автоматически, можно даже отключить)
    df.to_csv(save_path_csv, sep = ',') 

    x_pos_previous = df['x_pos_0'].to_numpy()[:-1]
    time = np.array(df['time'])[1:]
    x_pos_0 = df['x_pos_0'].to_numpy()[1:]
    x_pos_1 = df['x_pos_1'].to_numpy()[1:]
    print(len(time), len(x_pos_0))

    fig, ax = plt.subplots()

    save_path = f"testlogs\\SFItest\\SFIgraph_{str_current_time}.png"
        
    ax.plot(time, x_pos_0)
    ax.set_xlabel('Время')
    ax.set_ylabel(f"Координата, {mode}")
    ax.set_title('Зависимость')
    ax.grid(which="both", linestyle="--")  # Сетка для удобства

    if save_path:
            fig.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"График сохранён как {save_path}")

    return fig