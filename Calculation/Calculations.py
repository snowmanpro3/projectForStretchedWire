import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.integrate import cumulative_trapezoid # Для интегрирования методом трапеций
from scipy.fft import fft, fftfreq
from scipy.signal import get_window  # Добавляем оконную функцию
import warnings
import chardet

def firstFieldIntegral(X1, X2, Y1, Y2, time, eds, 
                       save_dir="FFI", 
                       filename="first_field_integral.png",
                       save_path=None):
    
    # Полный путь к файлу
    if save_path is None:
        save_path = (f"Calculation/{save_dir}/{filename}")

    try:
        x1_arr = np.array(X1)
        x2_arr = np.array(X2)
        time_arr = np.array(time)
        eds_arr = np.array(eds)

        if not (len(x2_arr) == len(x1_arr) == len(time_arr) == len(eds_arr)):
                print("Ошибка: Длины массивов не соответствуют ожидаемым!")
                print(f"len(X1)={len(x1_arr)}, len(X2)={len(x2_arr)}, len(time)={len(time_arr)}, len(eds)={len(eds_arr)}")
                print("Ожидается: len(X2) == len(eds) == len(X1)-1 == len(time)-1")
                return None
        
        # Вычисление временных интервалов
        dt = time_arr[1:] - time_arr[:-1] # Используем np.diff для краткости
        dt = np.diff(time_arr)

        # Вычисление скорости (поэлементно)
        # Подавляем предупреждения о делении на ноль временно
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            vel = (x2_arr - x1_arr) / dt
            # Заменяем бесконечности (от деления на 0) и NaN на 0 или другое значение
            vel = np.nan_to_num(vel, nan=0.0, posinf=0.0, neginf=0.0)
        
        first_fi = eds / vel 

        # Создаем фигуру перед построением графика
        fig, ax = plt.subplots()
        
        # Строим график зависимости первого магнитного поля от координаты нити (X1, например)
        ax.plot(X2, first_fi)
        ax.xlabel('Координата X2 (мм)')
        ax.ylabel('Первый интеграл магнитного поля')
        ax.title('Зависимость первого интеграла магнитного поля от координаты нити')
        ax.grid(which="both", linestyle="--")  # Сетка для удобства

        if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"График сохранён как {save_path}")
        
        return fig
    
    except Exception as e:
        print(f"Произошла ошибка в firstFieldIntegral: {e}")
        return None

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

def testFFI(pos, time, mode):

    df = pd.DataFrame({
         'pos': pos,
         'time': time
    })
    
    df.to_csv('testlogs/test_log.csv', index=False)
    # Создаем столбец mode, где только первая строка = 'X', остальные NaN
    df['mode'] = ['X'] + [np.nan] * (len(pos) - 1)
    
    pos = np.array(pos, dtype='float32')
    time = np.array(time, dtype='float32')

     


      