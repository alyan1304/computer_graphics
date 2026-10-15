import tkinter as tk
from tkinter import ttk, colorchooser

# Единицы измерения: RGB 0..255, CMYK 0..100 (%), H 0..360, L и S 0..100 (%)

def rgb_to_cmyk(r, g, b):
    c, m, y = 1 - r / 255, 1 - g / 255, 1 - b / 255
    k = min(c, m, y)
    if k >= 1:                      # чистый черный: делить на (1 - K) нельзя
        return 0, 0, 0, 100
    return ((c - k) / (1 - k) * 100,
            (m - k) / (1 - k) * 100,
            (y - k) / (1 - k) * 100,
            k * 100)


def cmyk_to_rgb(c, m, y, k):
    c, m, y, k = c / 100, m / 100, y / 100, k / 100
    return (255 * (1 - c) * (1 - k),
            255 * (1 - m) * (1 - k),
            255 * (1 - y) * (1 - k))


def rgb_to_hls(r, g, b):
    r, g, b = r / 255, g / 255, b / 255
    mx, mn = max(r, g, b), min(r, g, b)
    l = (mx + mn) / 2
    d = mx - mn
    if d == 0:                      # серый цвет: тон не определен, S = 0
        return 0, l * 100, 0
    s = d / (mx + mn) if l <= 0.5 else d / (2 - mx - mn)
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60, l * 100, s * 100


def hls_to_rgb(h, l, s):
    l, s = l / 100, s / 100
    m2 = l * (1 + s) if l < 0.5 else l + s - l * s
    m1 = 2 * l - m2

    def channel(hue):
        hue %= 360
        if hue < 60:
            return m1 + (m2 - m1) * hue / 60
        if hue < 180:
            return m2
        if hue < 240:
            return m1 + (m2 - m1) * (240 - hue) / 60
        return m1

    return (255 * channel(h + 120),
            255 * channel(h),
            255 * channel(h - 120))


MODELS = {
    "RGB":  (["R", "G", "B"],      [255, 255, 255]),
    "CMYK": (["C", "M", "Y", "K"], [100, 100, 100, 100]),
    "HLS":  (["H", "L", "S"],      [360, 100, 100]),
}
TO_RGB = {"RGB": lambda r, g, b: (r, g, b),
          "CMYK": cmyk_to_rgb,
          "HLS": hls_to_rgb}
FROM_RGB = {"RGB": lambda r, g, b: (r, g, b),
            "CMYK": rgb_to_cmyk,
            "HLS": rgb_to_hls}


class App:
    def __init__(self, root): 
        self.root = root
        root.title("Цветовые модели: CMYK - RGB - HLS")
        root.resizable(False, False)

        self.sliders = {} # для чисел с плавающей точкой, к этой переменной привязываются ползунки.
        self.texts = {}  # для строк (поля ввода).
        self.lock = False # флаг: пока мы программно обновляем виджеты, события не должны снова вызывать пересчёт

        # Верхняя панель
        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        self.preview = tk.Canvas(top, width=120, height=60,
                                 highlightthickness=1,
                                 highlightbackground="gray") # Canvas — прямоугольник, который мы будем перекрашивать в текущий цвет 
        self.preview.pack(side="left")
        info = ttk.Frame(top)
        info.pack(side="left", padx=10)
        self.hex_label = ttk.Label(info, font=("Arial", 14, "bold")) # показывает код вида #C86432
        self.hex_label.pack(anchor="w")
        ttk.Button(info, text="Выбрать из палитры...",
                   command=self.pick_color).pack(anchor="w", pady=(5, 0))

        # По панели на каждую модель
        for model in MODELS:
            self.build_panel(model)

        self.update_from("RGB", (200, 100, 50))

    def build_panel(self, model):
        names, maxes = MODELS[model]
        frame = ttk.LabelFrame(self.root, text=model, padding=8)
        frame.pack(fill="x", padx=10, pady=5)
        self.sliders[model], self.texts[model] = [], []

        for i, (name, mx) in enumerate(zip(names, maxes)):
            var = tk.DoubleVar()
            text = tk.StringVar()
            self.sliders[model].append(var)
            self.texts[model].append(text)

            ttk.Label(frame, text=name, width=2).grid(row=i, column=0)
            ttk.Scale(frame, from_=0, to=mx, variable=var, length=320, # ползунок
                      command=lambda _v, m=model: self.on_slider(m)
                      ).grid(row=i, column=1, padx=8, pady=2)
            entry = ttk.Entry(frame, textvariable=text, width=8)
            entry.grid(row=i, column=2)
            entry.bind("<Return>", lambda _e, m=model, k=i: self.on_entry(m, k))
            entry.bind("<FocusOut>", lambda _e, m=model, k=i: self.on_entry(m, k)) # entry.bind(...) — обработка нажатия Enter и потери фокуса (когда пользователь кликнул вне поля)

    
    def on_slider(self, model):
        if self.lock:
            return
        self.update_from(model, [v.get() for v in self.sliders[model]])

    def on_entry(self, model, i):
        if self.lock:
            return
        values = [v.get() for v in self.sliders[model]]
        try:
            value = float(self.texts[model][i].get().replace(",", "."))
        except ValueError:
            value = values[i]       # некорректный ввод: возвращаем прежнее
        values[i] = min(max(value, 0), MODELS[model][1][i])
        self.update_from(model, values)

    def pick_color(self):
        rgb, _ = colorchooser.askcolor(color=self.hex_label.cget("text"))
        if rgb:
            self.update_from("RGB", rgb)


    def update_from(self, source, values):
        rgb = TO_RGB[source](*values)
        rgb = tuple(min(max(x, 0), 255) for x in rgb)

        self.lock = True
        for model in MODELS:
            if model == source:
                shown = values     
            else:                   
                shown = FROM_RGB[model](*rgb)
            for var, text, v in zip(self.sliders[model],
                                    self.texts[model], shown):
                var.set(v)
                text.set(f"{v:.1f}" if model != "RGB" else f"{v:.0f}")
        self.lock = False

        color = "#%02x%02x%02x" % tuple(round(x) for x in rgb)
        self.preview.configure(bg=color)
        self.hex_label.configure(text=color.upper())


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()