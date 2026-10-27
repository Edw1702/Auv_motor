import tkinter as tk
from tkinter import ttk
import threading
import time

class SimuladorLocalGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title('Simulador Local (Sem ROS 2) - Motores do AUV')
        self.root.geometry('580x520')
        self._is_testing = False
        self._build_ui()

    def force_to_pwm(self, force: float) -> int:
        force_clamped = max(-10.0, min(10.0, force))
        return int(round(1500 + (force_clamped * 50.0)))

    def _build_ui(self):
        frame_force = ttk.LabelFrame(self.root, text='Configuração de Acionamento', padding=10)
        frame_force.pack(fill='x', padx=10, pady=5)
        ttk.Label(frame_force, text='Força desejada (-10 N a +10 N):').pack(side='left', padx=5)
        self.force_var = tk.DoubleVar(value=5.0)
        ttk.Spinbox(frame_force, from_=-10.0, to=10.0, increment=1.0, textvariable=self.force_var, width=8).pack(side='left', padx=5)

        frame_single = ttk.LabelFrame(self.root, text='Teste Individual', padding=10)
        frame_single.pack(fill='x', padx=10, pady=5)
        self.motor_status_labels = []
        self.motor_pwm_labels = []

        for i in range(7):
            row = ttk.Frame(frame_single)
            row.pack(fill='x', pady=2)
            ttk.Button(row, text=f'Testar Motor {i + 1}', width=16, command=lambda m=i: self.run_single(m)).pack(side='left', padx=5)
            lbl_pwm = ttk.Label(row, text='PWM: 1500', width=12)
            lbl_pwm.pack(side='left', padx=5)
            self.motor_pwm_labels.append(lbl_pwm)
            lbl_st = ttk.Label(row, text='Estado: A aguardar', width=35)
            lbl_st.pack(side='left', padx=5)
            self.motor_status_labels.append(lbl_st)

        frame_all = ttk.LabelFrame(self.root, text='Teste Completo', padding=10)
        frame_all.pack(fill='both', expand=True, padx=10, pady=5)
        ttk.Button(frame_all, text='Iniciar Teste Completo', command=self.run_all).pack(pady=5)
        self.lbl_all_status = ttk.Label(frame_all, text='Estado: A aguardar')
        self.lbl_all_status.pack(pady=2)
        self.lbl_all_tested = ttk.Label(frame_all, text='Motores já testados: Nenhum')
        self.lbl_all_tested.pack(pady=2)
        self.progress_bar = ttk.Progressbar(frame_all, orient='horizontal', length=400, mode='determinate')
        self.progress_bar.pack(pady=5)

    def update_pwms(self, pwm_list):
        for i, val in enumerate(pwm_list):
            self.root.after(0, self.motor_pwm_labels[i].config, {'text': f'PWM: {val}'})

    def run_single(self, motor_id):
        if self._is_testing:
            self.motor_status_labels[motor_id].config(text='Estado: Falha (Recusado - outro teste ativo)', foreground='red')
            return
        self._is_testing = True
        threading.Thread(target=self._worker_single, args=(motor_id,), daemon=True).start()

    def _worker_single(self, motor_id):
        pwm = self.force_to_pwm(self.force_var.get())
        pwms = [1500] * 7
        pwms[motor_id] = pwm
        self.update_pwms(pwms)
        self.root.after(0, lambda: self.motor_status_labels[motor_id].config(text=f'Estado: Em teste (Motor {motor_id+1} ativo)', foreground='orange'))
        time.sleep(2.0)
        self.update_pwms([1500] * 7)
        self.root.after(0, lambda: self.motor_status_labels[motor_id].config(text='Estado: Concluído', foreground='green'))
        self._is_testing = False

    def run_all(self):
        if self._is_testing:
            self.lbl_all_status.config(text='Estado: Falha (Teste recusado - outro teste em execução)', foreground='red')
            return
        self._is_testing = True
        threading.Thread(target=self._worker_all, daemon=True).start()

    def _worker_all(self):
        pwm = self.force_to_pwm(self.force_var.get())
        tested = []
        for m in range(7):
            pwms = [1500] * 7
            pwms[m] = pwm
            self.update_pwms(pwms)
            self.root.after(0, lambda m=m, t=tested.copy(): (
                self.lbl_all_status.config(text=f'Estado: A testar Motor [{m+1}]', foreground='orange'),
                self.lbl_all_tested.config(text=f"Motores já testados: {', '.join(f'M{x+1}' for x in t) if t else 'Nenhum'}"),
                self.progress_bar.config(value=((m + 0.5) / 8) * 100)
            ))
            time.sleep(2.0)
            tested.append(m)

        self.update_pwms([pwm] * 7)
        self.root.after(0, lambda: (
            self.lbl_all_status.config(text='Estado: A testar Todos os Motores [1..7]', foreground='orange'),
            self.lbl_all_tested.config(text='Motores já testados: M1, M2, M3, M4, M5, M6, M7'),
            self.progress_bar.config(value=90)
        ))
        time.sleep(2.0)
        self.update_pwms([1500] * 7)
        self.root.after(0, lambda: (
            self.lbl_all_status.config(text='Estado: Teste completo concluído com sucesso!', foreground='green'),
            self.progress_bar.config(value=100)
        ))
        self._is_testing = False

if __name__ == '__main__':
    root = tk.Tk()
    app = SimuladorLocalGUI(root)
    root.mainloop()