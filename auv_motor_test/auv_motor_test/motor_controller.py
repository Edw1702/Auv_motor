import time
import threading
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Int32MultiArray
from auv_interfaces.action import TestMotor, TestAllMotors


class MotorControllerNode(Node):
    def __init__(self):
        super().__init__('motor_controller')
        
        # Publicador do tópico /motors
        self.publisher_ = self.create_publisher(Int32MultiArray, '/motors', 10)
        
        # Controlo de concorrência para impedir testes simultâneos
        self._lock = threading.Lock()
        self._is_testing = False
        self._cb_group = ReentrantCallbackGroup()

        # Servidor da Ação 1: Teste Individual (test_motor)
        self._action_test_motor = ActionServer(
            self,
            TestMotor,
            'test_motor',
            execute_callback=self.execute_test_motor,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self._cb_group
        )

        # Servidor da Ação 2: Teste Completo (test_all_motors)
        self._action_test_all = ActionServer(
            self,
            TestAllMotors,
            'test_all_motors',
            execute_callback=self.execute_test_all,
            goal_callback=self.goal_callback,
            cancel_callback=self.cancel_callback,
            callback_group=self._cb_group
        )

        # Inicializa os motores em PWM neutro (1500)
        self.set_motors_neutral()
        self.get_logger().info('Nó de Controlo dos Motores iniciado.')

    def force_to_pwm(self, force: float) -> int:
        """Converte força (-10 N a +10 N) linearmente para PWM (1000 a 2000)."""
        force_clamped = max(-10.0, min(10.0, force))
        return int(round(1500 + (force_clamped * 50.0)))

    def publish_pwm(self, pwm_list: list):
        msg = Int32MultiArray()
        msg.data = pwm_list
        self.publisher_.publish(msg)

    def set_motors_neutral(self):
        """Coloca todos os 7 motores no PWM neutro (1500)."""
        self.publish_pwm([1500] * 7)

    def goal_callback(self, goal_request):
        """Recusa novos testes se já houver um teste em execução."""
        with self._lock:
            if self._is_testing:
                self.get_logger().warn('Teste recusado: já existe outro teste em curso.')
                return GoalResponse.REJECT
            
            # Valida o índice do motor caso seja a ação individual
            if hasattr(goal_request, 'motor_id'):
                if not (0 <= goal_request.motor_id < 7):
                    self.get_logger().warn(f'Motor inválido: {goal_request.motor_id}')
                    return GoalResponse.REJECT

            self._is_testing = True
            return GoalResponse.ACCEPT

    def cancel_callback(self, goal_handle):
        self.get_logger().info('Pedido de cancelamento recebido.')
        return CancelResponse.ACCEPT

    def execute_test_motor(self, goal_handle):
        """Executa o teste individual durante 2 segundos."""
        motor_id = goal_handle.request.motor_id
        force = goal_handle.request.force
        target_pwm = self.force_to_pwm(force)

        self.get_logger().info(f'A iniciar teste do Motor {motor_id + 1} (Força: {force}N -> PWM: {target_pwm})')
        feedback_msg = TestMotor.Feedback()
        result = TestMotor.Result()

        try:
            pwm_values = [1500] * 7
            pwm_values[motor_id] = target_pwm

            # Aciona durante 2 segundos (20 ciclos de 0.1s)
            for _ in range(20):
                if goal_handle.is_cancel_requested:
                    self.set_motors_neutral()
                    goal_handle.canceled()
                    result.success = False
                    result.message = f'Teste do Motor {motor_id + 1} cancelado.'
                    return result

                self.publish_pwm(pwm_values)
                feedback_msg.active_motor = motor_id
                goal_handle.publish_feedback(feedback_msg)
                time.sleep(0.1)

            self.set_motors_neutral()
            goal_handle.succeed()
            result.success = True
            result.message = f'Teste do Motor {motor_id + 1} concluído com sucesso!'
            return result

        except Exception as e:
            self.set_motors_neutral()
            goal_handle.abort()
            result.success = False
            result.message = f'Falha no teste: {str(e)}'
            return result

        finally:
            self.set_motors_neutral()
            with self._lock:
                self._is_testing = False

    def execute_test_all(self, goal_handle):
        """Testa cada motor por 2s e depois todos juntos por 2s."""
        force = goal_handle.request.force
        target_pwm = self.force_to_pwm(force)

        self.get_logger().info(f'A iniciar teste completo (Força: {force}N -> PWM: {target_pwm})')
        feedback_msg = TestAllMotors.Feedback()
        result = TestAllMotors.Result()
        tested_motors = []
        total_steps = 8 * 20  # 7 motores individuais + 1 coletivo (20 ciclos de 0.1s cada)
        current_step = 0

        try:
            # 1. Testes individuais (2 segundos cada)
            for motor_id in range(7):
                pwm_values = [1500] * 7
                pwm_values[motor_id] = target_pwm

                for _ in range(20):
                    if goal_handle.is_cancel_requested:
                        self.set_motors_neutral()
                        goal_handle.canceled()
                        result.success = False
                        result.message = 'Teste completo cancelado.'
                        return result

                    self.publish_pwm(pwm_values)
                    current_step += 1
                    feedback_msg.active_motors = [motor_id]
                    feedback_msg.tested_motors = tested_motors.copy()
                    feedback_msg.progress = (current_step / total_steps) * 100.0
                    goal_handle.publish_feedback(feedback_msg)
                    time.sleep(0.1)

                tested_motors.append(motor_id)

            # 2. Teste coletivo simultâneo (2 segundos)
            pwm_values = [target_pwm] * 7
            for _ in range(20):
                if goal_handle.is_cancel_requested:
                    self.set_motors_neutral()
                    goal_handle.canceled()
                    result.success = False
                    result.message = 'Teste completo cancelado.'
                    return result

                self.publish_pwm(pwm_values)
                current_step += 1
                feedback_msg.active_motors = list(range(7))
                feedback_msg.tested_motors = tested_motors.copy()
                feedback_msg.progress = (current_step / total_steps) * 100.0
                goal_handle.publish_feedback(feedback_msg)
                time.sleep(0.1)

            self.set_motors_neutral()
            goal_handle.succeed()
            result.success = True
            result.message = 'Teste completo concluído com sucesso!'
            return result

        except Exception as e:
            self.set_motors_neutral()
            goal_handle.abort()
            result.success = False
            result.message = f'Falha no teste completo: {str(e)}'
            return result

        finally:
            self.set_motors_neutral()
            with self._lock:
                self._is_testing = False


def main(args=None):
    rclpy.init(args=args)
    node = MotorControllerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.set_motors_neutral()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()