import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import get_window
import matplotlib.pyplot as plt

df = pd.read_csv('circleData/r=10; deltaX=-0.30047; deltaY=0.5681; 0.csv', 
                 sep='\t', 
                 header=None, 
                 quotechar='"')
# Разделяем данные по пробелам и преобразуем в числовой формат
# df[0] - the first and the one column in dataframe
# expand=True - преващает каждый элемент массива в отдельный столбик, иначе было бы просто много значений в одном столбике
# .astype(float) — преобразует все значения в числа с плавающей точкой (float).
df = df[0].str.split(expand=True).astype(float)

# Назначение имен столбцам
df.columns = ['Time', 'x1', 'y1', 'x2', 'y2', 'EDS']  # df.columns - список названий всех столбцов
# Теперь можно обращаться к данным-столбикам как df['Time], df['x1'] и т.д.

# df.head() — выводит первые 5 строк таблицы (чтобы убедиться, что всё загрузилось правильно) Можно указать аргумент - кол-во строк
print(df.head())
print(df.describe())  # Статистика по всем столбцам


# Убираем DC-компоненту (вычитаем среднее значение)
df['EDS'] -= np.mean(df['EDS'])

# Применяем оконную функцию Ханна
window = get_window("hann", len(df['EDS']))  # Создаем окно Ханна
df['EDS'] *= window  # Применяем окно к сигналу

# Выполняем преобразование Фурье
N = len(df['Time'])  # Количество точек во временном ряду
fft_values = fft(df['EDS'])  # Преобразование Фурье для ЭДС

# Вычисление частот (правильный вариант)
dt = df['Time'][1] - df['Time'][0]  # шаг дискретизации
freqs = np.fft.fftfreq(N, d=dt)  # частоты в Гц
omega = 2 * np.pi * freqs  # круговые частоты

# Вычисление амплитуд
amplitudes = 2.0 / N * np.abs(fft_values[:N//2])

# Поиск основной гармоники (игнорируем нулевую)
valid_range = slice(1, N//2)  # исключаем DC-компоненту и берём только положительный частоты 
main_harmonic_index = np.argmax(amplitudes[valid_range]) + 1  # +1 т.к. мы пропустили 0-ю

# Вывод коэффициентов мультипольного разложения
for i, amp in enumerate(amplitudes[:10]):
    print(f"Гармоника {i}: амплитуда = {amp:.3e}")  # Форматируем с одной цифрой после запятой


# Выводим результат
print(f"Основная гармоника: n={main_harmonic_index}")
print(f"Частота: {freqs[main_harmonic_index]:.3f} Гц")
print(f"Круговая частота: {omega[main_harmonic_index]:.3f} рад/с")
print(f"Амплитуда: {amplitudes[main_harmonic_index]:.3e} В")


plt.figure(figsize=(12, 6))
plt.stem(freqs[:N//2], amplitudes, linefmt='b-', markerfmt='bo', basefmt=' ')
plt.xlim(0, 10 * freqs[main_harmonic_index])  # Покажем 10 гармоник
plt.title("Спектр сигнала ЭДС")
plt.xlabel("Частота (Гц)")
plt.ylabel("Амплитуда (В)")
plt.grid()
plt.show()
