
import math
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

try:
    import control as ctrl
except ImportError as exc:
    raise SystemExit("Falta la librería 'control'. Instálala con: pip install control") from exc


class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#fffbe6",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            wraplength=340,
            padx=8,
            pady=6,
        )
        label.pack()

    def hide(self, _event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class TankApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Tanques acoplados - PID manual, observador y TIA")
        self.root.geometry("1540x940")
        self.root.configure(bg="#f4f6fb")

        self.vars = {}
        self.figures = {}
        self.metrics = {}
        self.models = {}

        self._build_style()
        self._build_ui()
        self._set_defaults()

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TNotebook", background="#f4f6fb")
        style.configure("TNotebook.Tab", padding=(16, 10), font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#21314d", background="#f4f6fb")
        style.configure("Section.TLabelframe", background="#ffffff")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Info.TLabel", font=("Segoe UI", 10), background="#ffffff")
        style.configure("Metric.TLabel", font=("Segoe UI", 11, "bold"), background="#ffffff", foreground="#14345b")
        style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=8)

    def _fmt_num(self, x, nd=8):
        return f"{float(x):.{nd}f}"

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text="Proyecto de automatización de dos tanques acoplados",
            style="Title.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "Interfaz para resistencias, función de transferencia, PID calculado manualmente, "
                "observador, servosistema y datos finales para TIA Portal."
            ),
            font=("Segoe UI", 10),
            background="#f4f6fb",
            foreground="#50627d",
        ).pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(main)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 10))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        self._build_parameters_panel(left)
        self._build_notebook(right)

    def _build_parameters_panel(self, parent):
        card = ttk.LabelFrame(parent, text="Parámetros de entrada", style="Section.TLabelframe", padding=12)
        card.pack(fill="y", expand=False)

        fields = [
            ("alto_tanque", "Alto del tanque [m]", "Altura interna del tanque."),
            ("ancho_tanque", "Ancho del tanque [m]", "Ancho interno del tanque."),
            ("fondo_tanque", "Fondo del tanque [m]", "Profundidad interna del tanque."),
            ("D1", "Diámetro conexión R1 [m]", "Diámetro interno del tubo entre tanques."),
            ("L1", "Longitud conexión R1 [m]", "Longitud del tubo entre tanques."),
            ("f1", "Factor fricción R1", "Factor de fricción del tramo entre tanques."),
            ("Kminor1", "Pérdidas menores R1", "Suma de pérdidas menores entre tanques."),
            ("altura_union_tanques", "Altura unión tanques [m]", "Altura del tubo de unión respecto a la base."),
            ("Delta_h10", "Δh nominal entre tanques [m]", "Diferencia nominal h1-h2 para linealizar R1."),
            ("D2", "Diámetro salida R2 [m]", "Diámetro interno de la salida del tanque 2."),
            ("L2", "Longitud salida R2 [m]", "Longitud de la tubería de salida del tanque 2."),
            ("f2", "Factor fricción R2", "Factor de fricción de la salida."),
            ("Kminor2", "Pérdidas menores R2", "Suma de pérdidas menores en la salida."),
            ("nivel_nominal_t2", "Nivel nominal tanque 2 [m]", "Nivel de operación nominal del tanque 2."),
            ("altura_salida_t2", "Altura salida tanque 2 [m]", "Altura del eje de salida respecto a la base."),
            ("Qmax_Lh", "Caudal máximo bomba [L/h]", "Caudal máximo nominal de la bomba."),
            ("fraccion_caudal", "Fracción de caudal", "Fracción del caudal máximo usada en la simulación abierta."),
            ("href", "Referencia [m]", "Referencia para el servosistema."),
            ("Ts_obj", "Ts deseado [s]", "Tiempo de establecimiento deseado para el PID manual y el servosistema."),
            ("zeta", "Amortiguamiento ζ", "Amortiguamiento deseado."),
            ("alpha_factor", "Factor polo extra PID", "Factor usado para el polo adicional del PID: alpha = factor*wn."),
            ("factor_observador", "Factor observador", "Qué tan más rápido será el observador respecto a la planta."),
            ("x0h1_real", "x0 h1 real [m]", "Condición inicial real de h1."),
            ("x0h2_real", "x0 h2 real [m]", "Condición inicial real de h2."),
            ("x0h1_est", "x0 h1 estimado [m]", "Condición inicial estimada de h1."),
            ("x0h2_est", "x0 h2 estimado [m]", "Condición inicial estimada de h2."),
            ("tmax", "Tiempo simulación [s]", "Tiempo total de simulación."),
            ("dt", "Paso simulación [s]", "Paso de simulación y Ts sugerido para el PLC."),
        ]

        canvas = tk.Canvas(card, width=400, highlightthickness=0, bg="#ffffff")
        scrollbar = ttk.Scrollbar(card, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for idx, (key, label_text, tip) in enumerate(fields):
            label = ttk.Label(scroll_frame, text=label_text, style="Info.TLabel")
            label.grid(row=idx, column=0, sticky="w", padx=(0, 8), pady=4)
            ToolTip(label, tip)
            var = tk.StringVar()
            entry = ttk.Entry(scroll_frame, textvariable=var, width=16)
            entry.grid(row=idx, column=1, sticky="ew", pady=4)
            ToolTip(entry, tip)
            self.vars[key] = var

        scroll_frame.columnconfigure(1, weight=1)

        btns = ttk.Frame(parent)
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="Calcular todo", style="Action.TButton", command=self.calculate_all).pack(fill="x")
        ttk.Button(btns, text="Restablecer valores", command=self._set_defaults).pack(fill="x", pady=(8, 0))

    def _build_notebook(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True)

        self.tab_res = ttk.Frame(notebook, padding=10)
        self.tab_tf = ttk.Frame(notebook, padding=10)
        self.tab_pid = ttk.Frame(notebook, padding=10)
        self.tab_obs = ttk.Frame(notebook, padding=10)
        self.tab_servo = ttk.Frame(notebook, padding=10)
        self.tab_tia = ttk.Frame(notebook, padding=10)

        notebook.add(self.tab_res, text="Resistencias")
        notebook.add(self.tab_tf, text="Función de transferencia")
        notebook.add(self.tab_pid, text="PID manual")
        notebook.add(self.tab_obs, text="Observador")
        notebook.add(self.tab_servo, text="Servosistema")
        notebook.add(self.tab_tia, text="TIA Portal")

        self._build_res_tab()
        self._build_tf_tab()
        self._build_pid_tab()
        self._build_obs_tab()
        self._build_servo_tab()
        self._build_tia_tab()

    def _metric_box(self, parent, title, key, tip):
        frame = ttk.LabelFrame(parent, text=title, style="Section.TLabelframe", padding=10)
        ttk.Label(frame, textvariable=self.metrics.setdefault(key, tk.StringVar(value="-")), style="Metric.TLabel").pack(anchor="w")
        ToolTip(frame, tip)
        return frame

    def _build_res_tab(self):
        top = ttk.Frame(self.tab_res)
        top.pack(fill="x")
        boxes = [
            ("R1 estimada", "R1", "Resistencia hidráulica equivalente entre tanque 1 y tanque 2."),
            ("R2 estimada", "R2", "Resistencia hidráulica equivalente en la salida del tanque 2."),
            ("Kh1", "Kh1", "Constante hidráulica no lineal del tramo entre tanques."),
            ("Kh2", "Kh2", "Constante hidráulica no lineal de la salida."),
        ]
        for i, (title, key, tip) in enumerate(boxes):
            box = self._metric_box(top, title, key, tip)
            box.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            top.columnconfigure(i, weight=1)

        self.res_text = tk.Text(self.tab_res, height=18, wrap="word", font=("Consolas", 10))
        self.res_text.pack(fill="both", expand=True, pady=(10, 0))

    def _build_tf_tab(self):
        top = ttk.Frame(self.tab_tf)
        top.pack(fill="x")
        boxes = [
            ("Nivel final [m]", "nivel_final", "Valor final aproximado del nivel del tanque 2."),
            ("Nivel final [cm]", "nivel_final_cm", "Valor final aproximado en centímetros."),
            ("Ganancia DC", "ganancia_dc", "Ganancia estática de la función de transferencia."),
        ]
        for i, (title, key, tip) in enumerate(boxes):
            box = self._metric_box(top, title, key, tip)
            box.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            top.columnconfigure(i, weight=1)

        self.tf_text = tk.Text(self.tab_tf, height=9, wrap="word", font=("Consolas", 10))
        self.tf_text.pack(fill="x", pady=(10, 10))

        fig = plt.Figure(figsize=(8, 5), dpi=100)
        self.figures["tf"] = fig
        self.tf_canvas = FigureCanvasTkAgg(fig, master=self.tab_tf)
        self.tf_canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_pid_tab(self):
        top = ttk.Frame(self.tab_pid)
        top.pack(fill="x")
        boxes = [
            ("Kp manual", "Kp", "Ganancia proporcional calculada manualmente por comparación de coeficientes."),
            ("Ki manual", "Ki", "Ganancia integral calculada manualmente por comparación de coeficientes."),
            ("Kd manual", "Kd", "Ganancia derivativa calculada manualmente por comparación de coeficientes."),
            ("Polo extra α", "alpha_pid", "Polo adicional usado en el diseño manual del PID."),
        ]
        for i, (title, key, tip) in enumerate(boxes):
            box = self._metric_box(top, title, key, tip)
            box.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            top.columnconfigure(i, weight=1)

        self.pid_text = tk.Text(self.tab_pid, height=18, wrap="word", font=("Consolas", 10))
        self.pid_text.pack(fill="x", pady=(10, 10))

        container = ttk.Frame(self.tab_pid)
        container.pack(fill="both", expand=True)

        fig1 = plt.Figure(figsize=(7, 4), dpi=100)
        self.figures["pid_resp"] = fig1
        self.pid_resp_canvas = FigureCanvasTkAgg(fig1, master=container)
        self.pid_resp_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

        fig2 = plt.Figure(figsize=(7, 4), dpi=100)
        self.figures["pid_u"] = fig2
        self.pid_u_canvas = FigureCanvasTkAgg(fig2, master=container)
        self.pid_u_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

    def _build_obs_tab(self):
        top = ttk.Frame(self.tab_obs)
        top.pack(fill="x")
        boxes = [
            ("Rango controlabilidad", "rango_ctrl", "Rango de la matriz de controlabilidad."),
            ("Rango observabilidad", "rango_obs", "Rango de la matriz de observabilidad."),
            ("e1 final [m]", "e1_final", "Error final de estimación del estado 1."),
            ("e2 final [m]", "e2_final", "Error final de estimación del estado 2."),
        ]
        for i, (title, key, tip) in enumerate(boxes):
            box = self._metric_box(top, title, key, tip)
            box.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            top.columnconfigure(i, weight=1)

        self.obs_text = tk.Text(self.tab_obs, height=12, wrap="word", font=("Consolas", 10))
        self.obs_text.pack(fill="x", pady=(10, 10))

        container = ttk.Frame(self.tab_obs)
        container.pack(fill="both", expand=True)

        fig1 = plt.Figure(figsize=(5.3, 4), dpi=100)
        self.figures["obs_h1"] = fig1
        self.obs_h1_canvas = FigureCanvasTkAgg(fig1, master=container)
        self.obs_h1_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

        fig2 = plt.Figure(figsize=(5.3, 4), dpi=100)
        self.figures["obs_h2"] = fig2
        self.obs_h2_canvas = FigureCanvasTkAgg(fig2, master=container)
        self.obs_h2_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

        fig3 = plt.Figure(figsize=(5.3, 4), dpi=100)
        self.figures["obs_err"] = fig3
        self.obs_err_canvas = FigureCanvasTkAgg(fig3, master=container)
        self.obs_err_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

    def _build_servo_tab(self):
        top = ttk.Frame(self.tab_servo)
        top.pack(fill="x")
        boxes = [
            ("K = [k1 k2]", "K_servo", "Ganancia de realimentación de estados."),
            ("Nbar", "Nbar", "Precompensador para seguimiento de referencia."),
            ("L = [l1 l2]", "L_servo", "Ganancia del observador usada en el servosistema."),
            ("Error final [cm]", "servo_error_final_cm", "Error final de seguimiento del servosistema."),
        ]
        for i, (title, key, tip) in enumerate(boxes):
            box = self._metric_box(top, title, key, tip)
            box.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            top.columnconfigure(i, weight=1)

        self.servo_text = tk.Text(self.tab_servo, height=10, wrap="word", font=("Consolas", 10))
        self.servo_text.pack(fill="x", pady=(10, 10))

        container = ttk.Frame(self.tab_servo)
        container.pack(fill="both", expand=True)

        fig1 = plt.Figure(figsize=(5.3, 4), dpi=100)
        self.figures["servo_y"] = fig1
        self.servo_y_canvas = FigureCanvasTkAgg(fig1, master=container)
        self.servo_y_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

        fig2 = plt.Figure(figsize=(5.3, 4), dpi=100)
        self.figures["servo_states"] = fig2
        self.servo_states_canvas = FigureCanvasTkAgg(fig2, master=container)
        self.servo_states_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

        fig3 = plt.Figure(figsize=(5.3, 4), dpi=100)
        self.figures["servo_u"] = fig3
        self.servo_u_canvas = FigureCanvasTkAgg(fig3, master=container)
        self.servo_u_canvas.get_tk_widget().pack(side="left", fill="both", expand=True)

    def _build_tia_tab(self):
        top = ttk.Frame(self.tab_tia)
        top.pack(fill="x")
        boxes = [
            ("Ts PLC [s]", "tia_ts", "Tiempo de muestreo usado en las ecuaciones discretas."),
            ("Control final", "tia_control", "Ecuación final del servosistema."),
            ("Salida estimada", "tia_yhat", "Ecuación final de la salida estimada."),
            ("Error observador", "tia_ey", "Ecuación final del error del observador."),
        ]
        for i, (title, key, tip) in enumerate(boxes):
            box = self._metric_box(top, title, key, tip)
            box.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)
            top.columnconfigure(i, weight=1)

        self.tia_text = tk.Text(self.tab_tia, height=30, wrap="word", font=("Consolas", 10))
        self.tia_text.pack(fill="both", expand=True, pady=(10, 0))

    def _set_defaults(self):
        defaults = {
            "alto_tanque": 0.20,
            "ancho_tanque": 0.15,
            "fondo_tanque": 0.15,
            "D1": 0.0127,
            "L1": 0.235,
            "f1": 0.03,
            "Kminor1": 1.5,
            "altura_union_tanques": 0.03,
            "Delta_h10": 0.02,
            "D2": 0.0127,
            "L2": 0.05,
            "f2": 0.03,
            "Kminor2": 1.5,
            "nivel_nominal_t2": 0.08,
            "altura_salida_t2": 0.03,
            "Qmax_Lh": 240.0,
            "fraccion_caudal": 0.70,
            "href": 0.10,
            "Ts_obj": 20.0,
            "zeta": 0.7,
            "alpha_factor": 5.0,
            "factor_observador": 8.0,
            "x0h1_real": 0.0,
            "x0h2_real": 0.0,
            "x0h1_est": 0.02,
            "x0h2_est": 0.01,
            "tmax": 200.0,
            "dt": 0.1,
        }
        for key, value in defaults.items():
            self.vars[key].set(str(value))

    def _get_float(self, key):
        try:
            return float(self.vars[key].get())
        except ValueError as exc:
            raise ValueError(f"Valor inválido en '{key}'.") from exc

    def _collect_inputs(self):
        data = {key: self._get_float(key) for key in self.vars}
        if data["nivel_nominal_t2"] <= data["altura_salida_t2"]:
            raise ValueError("El nivel nominal del tanque 2 debe ser mayor que la altura de la salida.")
        if data["Delta_h10"] <= 0:
            raise ValueError("La diferencia nominal entre tanques debe ser mayor que cero.")
        if data["dt"] <= 0 or data["tmax"] <= 0:
            raise ValueError("El tiempo total y el paso deben ser mayores que cero.")
        return data

    def calculate_all(self):
        try:
            p = self._collect_inputs()
            self._calculate_resistances(p)
            self._calculate_transfer_function(p)
            self._calculate_pid_manual(p)
            self._calculate_observer(p)
            self._calculate_servo(p)
            messagebox.showinfo("Cálculo completado", "Se actualizaron las pestañas con el PID manual y los datos corregidos de TIA.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _calculate_resistances(self, p):
        g = 9.81
        A_tanque = p["ancho_tanque"] * p["fondo_tanque"]
        At1 = math.pi * p["D1"] ** 2 / 4
        At2 = math.pi * p["D2"] ** 2 / 4
        Delta_h20 = p["nivel_nominal_t2"] - p["altura_salida_t2"]

        Kh1 = (p["f1"] * (p["L1"] / p["D1"]) + p["Kminor1"]) / (2 * g * At1 ** 2)
        R1 = 2 * math.sqrt(Kh1 * p["Delta_h10"])
        Kh2 = (p["f2"] * (p["L2"] / p["D2"]) + p["Kminor2"]) / (2 * g * At2 ** 2)
        R2 = 2 * math.sqrt(Kh2 * Delta_h20)

        self.models.update({
            "A_tanque": A_tanque,
            "At1": At1,
            "At2": At2,
            "Kh1": Kh1,
            "Kh2": Kh2,
            "R1": R1,
            "R2": R2,
            "Delta_h20": Delta_h20,
        })

        self.metrics["R1"].set(f"{R1:.4f} s/m²")
        self.metrics["R2"].set(f"{R2:.4f} s/m²")
        self.metrics["Kh1"].set(f"{Kh1:.4e}")
        self.metrics["Kh2"].set(f"{Kh2:.4e}")

        text = (
            "RESUMEN DE RESISTENCIAS HIDRÁULICAS\n"
            f"Área del tanque A = {A_tanque:.6f} m²\n"
            f"Área interna tubo R1 = {At1:.8f} m²\n"
            f"Área interna tubo R2 = {At2:.8f} m²\n"
            f"Δh10 nominal = {p['Delta_h10']:.4f} m\n"
            f"Δh20 efectivo = {Delta_h20:.4f} m\n"
            f"Kh1 = {Kh1:.4e}\n"
            f"Kh2 = {Kh2:.4e}\n"
            f"R1 = {R1:.6f} s/m²\n"
            f"R2 = {R2:.6f} s/m²\n"
        )
        self.res_text.delete("1.0", tk.END)
        self.res_text.insert(tk.END, text)

    def _calculate_transfer_function(self, p):
        A_tanque = self.models["A_tanque"]
        R1 = self.models["R1"]
        R2 = self.models["R2"]

        num = [1.0]
        den = [A_tanque ** 2 * R1, A_tanque * (2 + R1 / R2), 1.0 / R2]
        G = ctrl.tf(num, den)
        self.models["G"] = G
        self.models["den_G"] = den

        Qmax = (p["Qmax_Lh"] / 1000.0) / 3600.0
        Qin_constante = p["fraccion_caudal"] * Qmax
        t = np.arange(0, p["tmax"] + p["dt"], p["dt"])
        u = Qin_constante * np.ones_like(t)
        t_out, y_out = ctrl.forced_response(G, T=t, U=u)

        ganancia_dc = ctrl.dcgain(G)
        nivel_final = float(y_out[-1])

        self.metrics["nivel_final"].set(f"{nivel_final:.6f}")
        self.metrics["nivel_final_cm"].set(f"{nivel_final * 100:.2f}")
        self.metrics["ganancia_dc"].set(f"{float(ganancia_dc):.6f}")

        a2, a1, a0 = den
        tf_text = (
            "FUNCIÓN DE TRANSFERENCIA\n"
            f"G(s) = H2(s)/Qin(s)\n\n{G}\n"
            f"Denominador usado en el PID manual:\n"
            f"a2 = {self._fmt_num(a2, 10)}\n"
            f"a1 = {self._fmt_num(a1, 10)}\n"
            f"a0 = {self._fmt_num(a0, 10)}\n\n"
            f"Caudal máximo asumido = {Qmax:.8e} m³/s\n"
            f"Fracción de caudal = {p['fraccion_caudal']:.2f}\n"
            f"Caudal aplicado = {Qin_constante:.8e} m³/s\n"
            f"Nivel final estimado = {nivel_final:.6f} m ({nivel_final*100:.2f} cm)"
        )
        self.tf_text.delete("1.0", tk.END)
        self.tf_text.insert(tk.END, tf_text)

        fig = self.figures["tf"]
        fig.clear()
        ax = fig.add_subplot(111)
        ax.plot(t_out, y_out, linewidth=2)
        ax.set_title("Respuesta del nivel h₂(t) a un caudal constante")
        ax.set_xlabel("Tiempo [s]")
        ax.set_ylabel("Nivel h₂(t) [m]")
        ax.grid(True)
        self.tf_canvas.draw()

    def _calculate_pid_manual(self, p):
        if "G" not in self.models or "den_G" not in self.models:
            raise ValueError("Primero debe calcularse la función de transferencia.")

        a2, a1, a0 = [float(v) for v in self.models["den_G"]]

        zeta = p["zeta"]
        Ts = p["Ts_obj"]
        alpha_factor = p["alpha_factor"]

        wn = 4.0 / (zeta * Ts)
        alpha = alpha_factor * wn

        # Polinomio deseado: (s + alpha)(s^2 + 2*zeta*wn*s + wn^2)
        beta2 = 2.0 * zeta * wn + alpha
        beta1 = wn**2 + 2.0 * zeta * wn * alpha
        beta0 = alpha * wn**2

        # Ecuación característica con PID:
        # a2 s^3 + (a1 + Kd)s^2 + (a0 + Kp)s + Ki = 0
        Kd = a2 * beta2 - a1
        Kp = a2 * beta1 - a0
        Ki = a2 * beta0

        self.models["Kp_manual"] = Kp
        self.models["Ki_manual"] = Ki
        self.models["Kd_manual"] = Kd

        self.metrics["Kp"].set(self._fmt_num(Kp))
        self.metrics["Ki"].set(self._fmt_num(Ki))
        self.metrics["Kd"].set(self._fmt_num(Kd))
        self.metrics["alpha_pid"].set(self._fmt_num(alpha))

        Cpid = ctrl.tf([Kd, Kp, Ki], [1, 0])
        T = ctrl.feedback(Cpid * self.models["G"], 1)
        self.models["Cpid_manual"] = Cpid
        self.models["Tpid_manual"] = T

        t = np.arange(0, p["tmax"] + p["dt"], p["dt"])
        t_step, y_unit = ctrl.step_response(T, T=t)
        y_ref = p["href"] * y_unit

        e = p["href"] - y_ref
        e_int = np.concatenate([[0], np.cumsum((e[:-1] + e[1:]) * 0.5 * p["dt"])])
        e_der = np.gradient(e, p["dt"])
        u_control = Kp * e + Ki * e_int + Kd * e_der
        u_control_Lh = u_control * 3600 * 1000

        pid_text = (
            "DISEÑO MANUAL DEL PID POR COMPARACIÓN DE COEFICIENTES\n"
            "=====================================================\n\n"
            "1) Planta usada\n"
            f"G(s) = 1 / ({self._fmt_num(a2,10)} s^2 + {self._fmt_num(a1,10)} s + {self._fmt_num(a0,10)})\n\n"
            "2) Estructura del PID\n"
            "C(s) = Kp + Ki/s + Kd*s = (Kd*s^2 + Kp*s + Ki)/s\n\n"
            "3) Especificaciones\n"
            f"Ts = {self._fmt_num(Ts)} s\n"
            f"zeta = {self._fmt_num(zeta)}\n"
            f"wn = 4/(zeta*Ts) = {self._fmt_num(wn)} rad/s\n\n"
            "4) Polo adicional\n"
            f"alpha = factor*wn = {self._fmt_num(alpha_factor)}*{self._fmt_num(wn)} = {self._fmt_num(alpha)}\n\n"
            "5) Polinomio deseado\n"
            "(s + alpha)(s^2 + 2*zeta*wn*s + wn^2)\n"
            f"s^3 + {self._fmt_num(beta2)} s^2 + {self._fmt_num(beta1)} s + {self._fmt_num(beta0)}\n\n"
            "6) Ecuación característica real con PID\n"
            f"{self._fmt_num(a2,10)} s^3 + ({self._fmt_num(a1,10)} + Kd)s^2 + ({self._fmt_num(a0,10)} + Kp)s + Ki = 0\n\n"
            "7) Igualación de coeficientes\n"
            f"Kd = a2*beta2 - a1 = {self._fmt_num(a2,10)}*{self._fmt_num(beta2)} - {self._fmt_num(a1,10)} = {self._fmt_num(Kd)}\n"
            f"Kp = a2*beta1 - a0 = {self._fmt_num(a2,10)}*{self._fmt_num(beta1)} - {self._fmt_num(a0,10)} = {self._fmt_num(Kp)}\n"
            f"Ki = a2*beta0      = {self._fmt_num(a2,10)}*{self._fmt_num(beta0)} = {self._fmt_num(Ki)}\n\n"
            "8) PID final manual\n"
            f"C(s) = {self._fmt_num(Kp)} + {self._fmt_num(Ki)}/s + {self._fmt_num(Kd)} s\n"
        )
        self.pid_text.delete("1.0", tk.END)
        self.pid_text.insert(tk.END, pid_text)

        fig = self.figures["pid_resp"]
        fig.clear()
        ax = fig.add_subplot(111)
        ax.plot(t_step, y_ref, label="h₂(t)", linewidth=2)
        ax.axhline(p["href"], color="r", linestyle="--", label=f"Referencia {p['href']*100:.1f} cm")
        ymin = min(np.min(y_ref), p["href"])
        ymax = max(np.max(y_ref), p["href"])
        margen = max(0.02 * max(p["href"], 1e-6), 0.005)
        ax.set_ylim(ymin - margen, ymax + margen)
        ax.set_xlim(0, max(4 * p["Ts_obj"], p["dt"]))
        ax.set_title("Respuesta del sistema con PID manual")
        ax.set_xlabel("Tiempo [s]")
        ax.set_ylabel("Nivel [m]")
        ax.grid(True)
        ax.legend()
        self.pid_resp_canvas.draw()

        fig2 = self.figures["pid_u"]
        fig2.clear()
        ax2 = fig2.add_subplot(111)
        ax2.plot(t_step, u_control_Lh, color="m", linewidth=2)
        ax2.set_title("Señal de control estimada del PID manual")
        ax2.set_xlabel("Tiempo [s]")
        ax2.set_ylabel("Caudal de control [L/h]")
        ax2.grid(True)
        self.pid_u_canvas.draw()

    def _calculate_observer(self, p):
        A_t = self.models["A_tanque"]
        R1 = self.models["R1"]
        R2 = self.models["R2"]

        A = np.array([
            [-1 / (A_t * R1), 1 / (A_t * R1)],
            [1 / (A_t * R1), -(1 / (A_t * R1) + 1 / (A_t * R2))],
        ], dtype=float)
        B = np.array([[1 / A_t], [0]], dtype=float)
        C = np.array([[0, 1]], dtype=float)
        D = np.array([[0]], dtype=float)

        self.models.update({"A": A, "B": B, "C": C, "D": D})

        Co = ctrl.ctrb(A, B)
        Ob = ctrl.obsv(A, C)
        rango_ctrl = np.linalg.matrix_rank(Co)
        rango_obs = np.linalg.matrix_rank(Ob)

        polos_planta = np.linalg.eigvals(A)
        polos_obs = p["factor_observador"] * polos_planta
        L = ctrl.place(A.T, C.T, polos_obs).T
        self.models["L"] = L

        qin = p["fraccion_caudal"] * ((p["Qmax_Lh"] / 1000.0) / 3600.0)
        t = np.arange(0, p["tmax"] + p["dt"], p["dt"])
        u = qin * np.ones_like(t)

        sys_ss = ctrl.ss(A, B, C, D)
        x0_real = np.array([p["x0h1_real"], p["x0h2_real"]])
        _, _, _x_real = ctrl.forced_response(sys_ss, T=t, U=u, X0=x0_real, return_x=True)

        A_ext = np.block([
            [A, np.zeros_like(A)],
            [L @ C, A - L @ C],
        ])
        B_ext = np.vstack([B, B])
        C_ext = np.eye(4)
        D_ext = np.zeros((4, 1))
        sys_ext = ctrl.ss(A_ext, B_ext, C_ext, D_ext)

        x0_ext = np.array([p["x0h1_real"], p["x0h2_real"], p["x0h1_est"], p["x0h2_est"]])
        _, _, x_ext = ctrl.forced_response(sys_ext, T=t, U=u, X0=x0_ext, return_x=True)
        x_ext = x_ext.T

        h1_real = x_ext[:, 0]
        h2_real = x_ext[:, 1]
        h1_est = x_ext[:, 2]
        h2_est = x_ext[:, 3]

        e1 = h1_real - h1_est
        e2 = h2_real - h2_est

        self.metrics["rango_ctrl"].set(str(rango_ctrl))
        self.metrics["rango_obs"].set(str(rango_obs))
        self.metrics["e1_final"].set(f"{e1[-1]:.3e}")
        self.metrics["e2_final"].set(f"{e2[-1]:.3e}")

        obs_text = (
            "ESPACIO DE ESTADOS Y OBSERVADOR\n"
            f"A =\n{A}\n\n"
            f"B =\n{B}\n\n"
            f"C =\n{C}\n\n"
            f"D =\n{D}\n\n"
            f"Rango controlabilidad = {rango_ctrl}\n"
            f"Rango observabilidad = {rango_obs}\n"
            f"Polos de la planta = {polos_planta}\n"
            f"Polos del observador = {polos_obs}\n"
            f"L =\n{L}\n"
        )
        self.obs_text.delete("1.0", tk.END)
        self.obs_text.insert(tk.END, obs_text)

        fig = self.figures["obs_h1"]
        fig.clear()
        ax = fig.add_subplot(111)
        ax.plot(t, h1_real, label="h1 real", linewidth=2)
        ax.plot(t, h1_est, "--", label="h1 estimado", linewidth=2)
        ax.set_title("Comparación h1 real vs estimado")
        ax.set_xlabel("Tiempo [s]")
        ax.set_ylabel("Nivel [m]")
        ax.grid(True)
        ax.legend()
        self.obs_h1_canvas.draw()

        fig2 = self.figures["obs_h2"]
        fig2.clear()
        ax2 = fig2.add_subplot(111)
        ax2.plot(t, h2_real, label="h2 real", linewidth=2)
        ax2.plot(t, h2_est, "--", label="h2 estimado", linewidth=2)
        ax2.set_title("Comparación h2 real vs estimado")
        ax2.set_xlabel("Tiempo [s]")
        ax2.set_ylabel("Nivel [m]")
        ax2.grid(True)
        ax2.legend()
        self.obs_h2_canvas.draw()

        fig3 = self.figures["obs_err"]
        fig3.clear()
        ax3 = fig3.add_subplot(111)
        ax3.plot(t, e1, label="e1 = h1 - h1_est", linewidth=2)
        ax3.plot(t, e2, label="e2 = h2 - h2_est", linewidth=2)
        ax3.set_title("Error de estimación")
        ax3.set_xlabel("Tiempo [s]")
        ax3.set_ylabel("Error [m]")
        ax3.grid(True)
        ax3.legend()
        self.obs_err_canvas.draw()

    def _calculate_servo(self, p):
        A = self.models["A"]
        B = self.models["B"]
        C = self.models["C"]

        wn = 4.0 / (p["zeta"] * p["Ts_obj"])
        wd = wn * np.sqrt(max(0.0, 1 - p["zeta"] ** 2))

        p1 = -p["zeta"] * wn + 1j * wd
        p2 = -p["zeta"] * wn - 1j * wd
        polos_control = np.array([p1, p2])

        K = ctrl.place(A, B, polos_control)
        Nbar = (-1.0 / (C @ np.linalg.inv(A - B @ K) @ B)).item()

        polos_planta = np.linalg.eigvals(A)
        polos_obs = p["factor_observador"] * polos_planta
        L = ctrl.place(A.T, C.T, polos_obs).T

        A_ext = np.block([
            [A, -B @ K],
            [L @ C, A - B @ K - L @ C],
        ])
        B_ext = np.vstack([B * Nbar, B * Nbar])
        C_ext = np.hstack([C, np.zeros_like(C)])
        D_ext = np.array([[0.0]])
        sys_ext = ctrl.ss(A_ext, B_ext, C_ext, D_ext)

        t = np.arange(0, p["tmax"] + p["dt"], p["dt"])
        r = p["href"] * np.ones_like(t)
        x0_ext = np.array([p["x0h1_real"], p["x0h2_real"], p["x0h1_est"], p["x0h2_est"]])

        t_out, y_out, x_ext = ctrl.forced_response(sys_ext, T=t, U=r, X0=x0_ext, return_x=True)
        x_ext = x_ext.T

        h1_real = x_ext[:, 0]
        h2_real = x_ext[:, 1]
        h1_est = x_ext[:, 2]
        h2_est = x_ext[:, 3]

        u = np.zeros(len(t_out))
        for k in range(len(t_out)):
            xhat_k = np.array([[h1_est[k]], [h2_est[k]]])
            u[k] = (-(K @ xhat_k) + Nbar * r[k]).item()

        u_Lh = u * 3600.0 * 1000.0
        error_final_cm = float((p["href"] - y_out[-1]) * 100.0)

        self.models["K_servo"] = K
        self.models["Nbar"] = Nbar
        self.models["L_servo"] = L

        self.metrics["K_servo"].set(f"[{K[0,0]:.6f}, {K[0,1]:.6f}]")
        self.metrics["Nbar"].set(f"{Nbar:.10f}")
        self.metrics["L_servo"].set(f"[{L[0,0]:.6f}, {L[1,0]:.6f}]")
        self.metrics["servo_error_final_cm"].set(f"{error_final_cm:.4f}")

        servo_text = (
            "SERVOSISTEMA CON OBSERVADOR\n"
            f"Polos de control = {polos_control}\n"
            f"K = {K}\n"
            f"Nbar = {Nbar:.10f}\n"
            f"Polos del observador = {polos_obs}\n"
            f"L =\n{L}\n\n"
            "Ley de control:\n"
            "u = -K*xhat + Nbar*r\n\n"
            f"Error final = {error_final_cm:.4f} cm\n"
        )
        self.servo_text.delete("1.0", tk.END)
        self.servo_text.insert(tk.END, servo_text)

        fig1 = self.figures["servo_y"]
        fig1.clear()
        ax1 = fig1.add_subplot(111)
        ax1.plot(t_out, y_out, linewidth=2, label="h2(t)")
        ax1.axhline(p["href"], color="r", linestyle="--", label=f"Referencia {p['href']*100:.1f} cm")
        ymin = min(np.min(y_out), p["href"])
        ymax = max(np.max(y_out), p["href"])
        margen = max(0.02 * max(p["href"], 1e-6), 0.005)
        ax1.set_ylim(ymin - margen, ymax + margen)
        ax1.set_xlim(0, max(4 * p["Ts_obj"], p["dt"]))
        ax1.set_title("Respuesta del servosistema con observador")
        ax1.set_xlabel("Tiempo [s]")
        ax1.set_ylabel("Nivel h₂(t) [m]")
        ax1.grid(True)
        ax1.legend()
        self.servo_y_canvas.draw()

        fig2 = self.figures["servo_states"]
        fig2.clear()
        ax2 = fig2.add_subplot(111)
        ax2.plot(t_out, h1_real, linewidth=2, label="h1 real")
        ax2.plot(t_out, h2_real, linewidth=2, label="h2 real")
        ax2.plot(t_out, h1_est, "--", linewidth=2, label="h1 estimado")
        ax2.plot(t_out, h2_est, "--", linewidth=2, label="h2 estimado")
        ax2.set_title("Estados reales y estimados")
        ax2.set_xlabel("Tiempo [s]")
        ax2.set_ylabel("Nivel [m]")
        ax2.grid(True)
        ax2.legend()
        self.servo_states_canvas.draw()

        fig3 = self.figures["servo_u"]
        fig3.clear()
        ax3 = fig3.add_subplot(111)
        ax3.plot(t_out, u_Lh, linewidth=2)
        ax3.set_title("Señal de control del servosistema")
        ax3.set_xlabel("Tiempo [s]")
        ax3.set_ylabel("Caudal [L/h]")
        ax3.grid(True)
        self.servo_u_canvas.draw()

        self._update_tia_tab(p, A, B, C, K, L, Nbar)

    def _update_tia_tab(self, p, A, B, C, K, L, Nbar):
        Ts = float(p["dt"])

        a11 = float(A[0, 0]); a12 = float(A[0, 1])
        a21 = float(A[1, 0]); a22 = float(A[1, 1])
        b1 = float(B[0, 0]); b2 = float(B[1, 0])
        c1 = float(C[0, 0]); c2 = float(C[0, 1])
        k1 = float(K[0, 0]); k2 = float(K[0, 1])
        l1 = float(L[0, 0]); l2 = float(L[1, 0])

        ad11 = 1.0 + Ts * a11
        ad12 = Ts * a12
        ad21 = Ts * a21
        ad22 = 1.0 + Ts * a22
        bd1 = Ts * b1
        bd2 = Ts * b2
        ld1 = Ts * l1
        ld2 = Ts * l2

        self.metrics["tia_ts"].set(self._fmt_num(Ts))
        self.metrics["tia_control"].set(
            f"u = {self._fmt_num(-k1)}*xhat1 + {self._fmt_num(-k2)}*xhat2 + {self._fmt_num(Nbar)}*r"
        )
        self.metrics["tia_yhat"].set("yhat = xhat2")
        self.metrics["tia_ey"].set("e_y = y - xhat2")

        texto = (
            "DATOS FINALES PARA PROGRAMAR EN TIA PORTAL\n"
            "============================================================\n\n"

            "1) ¿QUÉ REPRESENTA CADA VARIABLE?\n"
            "------------------------------------------------------------\n"
            "r       : referencia del nivel deseado\n"
            "y       : nivel real medido del tanque 2\n"
            "yhat    : nivel estimado por el observador\n"
            "e_y     : error del observador\n"
            "u       : señal de control del servosistema\n"
            "xhat1   : estado estimado 1 (nivel estimado del tanque 1)\n"
            "xhat2   : estado estimado 2 (nivel estimado del tanque 2)\n"
            "xhat1_n : siguiente valor de xhat1\n"
            "xhat2_n : siguiente valor de xhat2\n\n"

            "2) PARÁMETROS FINALES QUE DEBES LLEVAR AL PLC\n"
            "------------------------------------------------------------\n"
            f"Ts   = {self._fmt_num(Ts, 10)}\n"
            f"a11  = {self._fmt_num(a11, 10)}\n"
            f"a12  = {self._fmt_num(a12, 10)}\n"
            f"a21  = {self._fmt_num(a21, 10)}\n"
            f"a22  = {self._fmt_num(a22, 10)}\n"
            f"b1   = {self._fmt_num(b1, 10)}\n"
            f"b2   = {self._fmt_num(b2, 10)}\n"
            f"c1   = {self._fmt_num(c1, 10)}\n"
            f"c2   = {self._fmt_num(c2, 10)}\n"
            f"k1   = {self._fmt_num(k1, 10)}\n"
            f"k2   = {self._fmt_num(k2, 10)}\n"
            f"l1   = {self._fmt_num(l1, 10)}\n"
            f"l2   = {self._fmt_num(l2, 10)}\n"
            f"Nbar = {self._fmt_num(Nbar, 10)}\n\n"

            "3) ECUACIÓN FINAL DE CONTROL DEL SERVOSISTEMA\n"
            "------------------------------------------------------------\n"
            f"u = {self._fmt_num(-k1, 10)}*xhat1 + {self._fmt_num(-k2, 10)}*xhat2 + {self._fmt_num(Nbar, 10)}*r\n\n"

            "4) ECUACIÓN FINAL DE SALIDA ESTIMADA\n"
            "------------------------------------------------------------\n"
            "yhat = c1*xhat1 + c2*xhat2\n"
            f"yhat = {self._fmt_num(c1, 10)}*xhat1 + {self._fmt_num(c2, 10)}*xhat2\n"
            "Como C = [0 1], realmente queda:\n"
            "yhat = xhat2\n\n"

            "5) ECUACIÓN FINAL DEL ERROR DEL OBSERVADOR\n"
            "------------------------------------------------------------\n"
            "e_y = y - yhat\n"
            "e_y = y - xhat2\n\n"

            "6) OBSERVADOR CONTINUO\n"
            "------------------------------------------------------------\n"
            "xhat_dot = A*xhat + B*u + L*(y - C*xhat)\n\n"

            "7) OBSERVADOR DISCRETIZADO FINAL (EULER)\n"
            "------------------------------------------------------------\n"
            f"xhat1_n = {self._fmt_num(ad11, 10)}*xhat1 + {self._fmt_num(ad12, 10)}*xhat2 + {self._fmt_num(bd1, 10)}*u + {self._fmt_num(ld1, 10)}*e_y\n"
            f"xhat2_n = {self._fmt_num(ad21, 10)}*xhat1 + {self._fmt_num(ad22, 10)}*xhat2 + {self._fmt_num(bd2, 10)}*u + {self._fmt_num(ld2, 10)}*e_y\n\n"

            "8) ACTUALIZACIÓN DE ESTADOS\n"
            "------------------------------------------------------------\n"
            "xhat1 = xhat1_n\n"
            "xhat2 = xhat2_n\n\n"

            "9) BLOQUE SCL LISTO PARA PEGAR\n"
            "------------------------------------------------------------\n"
            "yhat := xhat2;\n"
            "e_y := y - xhat2;\n\n"
            f"u := {self._fmt_num(-k1, 10)}*xhat1 + {self._fmt_num(-k2, 10)}*xhat2 + {self._fmt_num(Nbar, 10)}*r;\n\n"
            f"xhat1_n := {self._fmt_num(ad11, 10)}*xhat1 + {self._fmt_num(ad12, 10)}*xhat2 + {self._fmt_num(bd1, 10)}*u + {self._fmt_num(ld1, 10)}*e_y;\n"
            f"xhat2_n := {self._fmt_num(ad21, 10)}*xhat1 + {self._fmt_num(ad22, 10)}*xhat2 + {self._fmt_num(bd2, 10)}*u + {self._fmt_num(ld2, 10)}*e_y;\n\n"
            "xhat1 := xhat1_n;\n"
            "xhat2 := xhat2_n;\n\n"

            "10) ACLARACIÓN IMPORTANTE SOBRE EL PID\n"
            "------------------------------------------------------------\n"
            "Las ecuaciones del observador y del servosistema NO cambian por usar PID manual o PID de pidtune.\n"
            "Estas ecuaciones dependen del modelo en espacio de estados y del diseño de K, L y Nbar.\n"
            "Por eso, los datos que debes poner en TIA para el observador y el servosistema son los mostrados aquí.\n"
        )

        self.tia_text.delete("1.0", tk.END)
        self.tia_text.insert(tk.END, texto)


def main():
    root = tk.Tk()
    app = TankApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
