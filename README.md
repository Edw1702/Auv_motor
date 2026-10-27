# Sistema de Teste dos Motores do AUV (ROS 2)

Repositório com a solução para a atividade de acionamento e teste controlado dos sete motores do AUV utilizando ROS 2 e interface gráfica em Tkinter[cite: 1, 2].

## Estrutura do Projeto
* **`auv_interfaces`**: Pacote CMake responsável por gerar as Actions personalizadas (`TestMotor` e `TestAllMotors`)[cite: 2].
* **`auv_motor_test`**: Pacote Python contendo o nó de controle dos motores (`motor_controller`), o nó da interface gráfica (`gui_node`) e o arquivo `launch`[cite: 1].

## Especificações de Acionamento
* **Tópico de comando:** `/motors` (`std_msgs/msg/Int32MultiArray` com 7 elementos)[cite: 1].
* **Conversão Linear Força x PWM:**
  * `-10 N` $\rightarrow$ `1000` PWM[cite: 1]
  * `0 N` (Neutro) $\rightarrow$ `1500` PWM[cite: 1, 3]
  * `+10 N` $\rightarrow$ `2000` PWM[cite: 1]

## Como Compilar e Executar

No seu workspace ROS 2 (`~/ros2_ws`):

```bash
cd ~/ros2_ws
colcon build
source install/setup.bash
ros2 launch auv_motor_test motor_test.launch.py