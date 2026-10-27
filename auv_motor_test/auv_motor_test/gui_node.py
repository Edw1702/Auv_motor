import threading
import tkinter as tk
from tkinter import ttk
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from std_msgs.msg import Int32MultiArray
from auv_interfaces.action import TestMotor, TestAllMotors


class MotorTestGUI(Node):
    def __init__(self, root: tk.Tk):
        super().__init__('motor_gui_node')
        self.root = root
        self.root.title('Sistema de Teste dos Motores do AUV')
        self.root.geometry('580x520')

        # Clientes de Action
        self._client_single = ActionClient(self, TestMotor, 'test_motor')
        self._client_all = ActionClient(self, TestAllMotors, 'test_all_motors')

        # Subscritor para visualizar o tópico /motors em tempo real
        self._sub_motors = self.create_subscription(
            Int32MultiArray,
            '/motors',
            self.motors_topic_callback,
            10
        )

        self._build_ui()

    def _build_ui(self):
        # Secção de Configuração de Força
        frame_force = ttk.LabelFrame(self.root, text='Configuração de Acionamento', padding=10)
        frame_force.pack(fill='x', padx=10, pady=5)

        ttk.Label(frame_force, text='Força desejada (-10 N a +10 N):').pack(side='left', padx=5)
        self.force_var = tk.DoubleVar(value=5.0)
        spin_force = ttk.Spinbox(frame_force, from_=-10.0, to=10.0, increment=1.0, textvariable=self.force_var, width=8)
        spin_force.pack(side='left', padx=5)
        ttk.Label(frame_force, text='(1000 = -10N | 1500 = 0N | 2000 = +10N)').pack(side='left', padx=5)

        # Secção de Teste Individual
        frame_single = ttk.LabelFrame(self.root, text='Teste Individual', padding=10)
        frame_single.pack(fill='x', padx=10, pady=5)

        self.motor_status_labels = []
        self.motor_pwm_labels = []

        for i in range(7):
            row_frame = ttk.Frame(frame_single)
            row_frame.pack(fill='x', pady=2)

            btn = ttk.Button(
                row_frame,
                text=f'Testar Motor {i + 1}',
                width=16,
                command=lambda m=i: self.start_single_test(m)
            )
            btn.pack(side='left', padx=5)

            lbl_pwm = ttk.Label(row_frame, text='PWM: 1500', width=12)
            lbl_pwm.pack(side='left', padx=5)
            self.motor_pwm_labels.append(lbl_pwm)

            lbl_status = ttk.Label(row_frame, text='Estado: A aguardar', width=35)
            lbl_status.pack(side='left', padx=5)
            self.motor_status_labels.append(lbl_status)

        # Secção de Teste Completo
        frame_all = ttk.LabelFrame(self.root, text='Teste Completo', padding=10)
        frame_all.pack(fill='both', expand=True, padx=10, pady=5)

        btn_all = ttk.Button(frame_all, text='Iniciar Teste Completo', command=self.start_all_test)
        btn_all.pack(pady=5)

        self.lbl_all_status = ttk.Label(frame_all, text='Estado: A aguardar')
        self.lbl_all_status.pack(pady=2)

        self.lbl_all_tested = ttk.Label(frame_all, text='Motores já testados: Nenhum')
        self.lbl_all_tested.pack(pady=2)

        self.progress_bar = ttk.Progressbar(frame_all, orient='horizontal', length=400, mode='determinate')
        self.progress_bar.pack(pady=5)

    def motors_topic_callback(self, msg: Int32MultiArray):
        """Atualiza na interface o valor de PWM publicado no tópico /motors."""
        for i, pwm in enumerate(msg.data[:7]):
            self.root.after(0, self.motor_pwm_labels[i].config, {'text': f'PWM: {pwm}'})

    # --- Lógica do Teste Individual ---
    def start_single_test(self, motor_id: int):
        if not self._client_single.wait_for_server(timeout_sec=1.0):
            self.motor_status_labels[motor_id].config(text='Estado: Servidor indisponível!', foreground='red')
            return

        goal_msg = TestMotor.Goal()
        goal_msg.motor_id = motor_id
        goal_msg.force = float(self.force_var.get())

        self.motor_status_labels[motor_id].config(text='Estado: A enviar pedido...', foreground='blue')
        send_goal_future = self._client_single.send_goal_async(
            goal_msg,
            feedback_callback=lambda fb, m=motor_id: self.single_feedback_cb(fb, m)
        )
        send_goal_future.add_done_callback(lambda fut, m=motor_id: self.single_goal_response_cb(fut, m))

    def single_goal_response_cb(self, future, motor_id: int):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.root.after(0, lambda: self.motor_status_labels[motor_id].config(
                text='Estado: Falha (Recusado - outro teste ativo)', foreground='red'
            ))
            return

        self.root.after(0, lambda: self.motor_status_labels[motor_id].config(
            text='Estado: A testar motor...', foreground='orange'
        ))
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(lambda fut, m=motor_id: self.single_result_cb(fut, m))

    def single_feedback_cb(self, feedback_msg, motor_id: int):
        active = feedback_msg.feedback.active_motor
        self.root.after(0, lambda: self.motor_status_labels[motor_id].config(
            text=f'Estado: Em teste (Motor {active + 1} ativo)', foreground='orange'
        ))

    def single_result_cb(self, future, motor_id: int):
        result = future.result().result
        color = 'green' if result.success else 'red'
        status_txt = 'Concluído' if result.success else 'Falha'
        self.root.after(0, lambda: self.motor_status_labels[motor_id].config(
            text=f'Estado: {status_txt}', foreground=color
        ))

    # --- Lógica do Teste Completo ---
    def start_all_test(self):
        if not self._client_all.wait_for_server(timeout_sec=1.0):
            self.lbl_all_status.config(text='Estado: Servidor indisponível!', foreground='red')
            return

        goal_msg = TestAllMotors.Goal()
        goal_msg.force = float(self.force_var.get())

        self.progress_bar['value'] = 0
        self.lbl_all_status.config(text='Estado: A enviar pedido...', foreground='blue')
        self.lbl_all_tested.config(text='Motores já testados: Nenhum')

        send_goal_future = self._client_all.send_goal_async(
            goal_msg,
            feedback_callback=self.all_feedback_cb
        )
        send_goal_future.add_done_callback(self.all_goal_response_cb)

    def all_goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.root.after(0, lambda: self.lbl_all_status.config(
                text='Estado: Falha (Teste recusado - outro teste em execução)', foreground='red'
            ))
            return

        self.root.after(0, lambda: self.lbl_all_status.config(
            text='Estado: Teste completo em execução...', foreground='orange'
        ))
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.all_result_cb)

    def all_feedback_cb(self, feedback_msg):
        fb = feedback_msg.feedback
        active_str = ', '.join(str(m + 1) for m in fb.active_motors)
        tested_str = ', '.join(f'M{m + 1}' for m in fb.tested_motors) if fb.tested_motors else 'Nenhum'

        def update_ui():
            self.lbl_all_status.config(
                text=f'Estado: A testar Motor(es) [{active_str}] ({fb.progress:.0f}%)',
                foreground='orange'
            )
            self.lbl_all_tested.config(text=f'Motores já testados: {tested_str}')
            self.progress_bar['value'] = fb.progress

        self.root.after(0, update_ui)

    def all_result_cb(self, future):
        result = future.result().result
        color = 'green' if result.success else 'red'

        def update_ui():
            self.lbl_all_status.config(text=f'Estado: {result.message}', foreground=color)
            if result.success:
                self.lbl_all_tested.config(text='Motores já testados: M1, M2, M3, M4, M5, M6, M7 (Todos)')
                self.progress_bar['value'] = 100

        self.root.after(0, update_ui)


def main(args=None):
    rclpy.init(args=args)
    root = tk.Tk()
    gui_node = MotorTestGUI(root)

    # Executa o rclpy.spin numa thread secundária para não bloquear a janela do Tkinter
    spin_thread = threading.Thread(target=rclpy.spin, args=(gui_node,), daemon=True)
    spin_thread.start()

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        gui_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()