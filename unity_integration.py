import socket
import json
import time

# Dicionário para armazenar os carros spawnados
spawned_cars = {}

def send_command(command, car_id=None, action=None, duration=None):
    cmd_data = {
        "command": command
    }

    if command == "spawn_car":
        cmd_data.update({
            "position": {"x": 0, "y": 0, "z": 0},
            "color": "blue",
            "type": "player",
            "speed": 10,
            "player_name": car_id  # Aqui car_id é o nome do jogador
        })
    elif command == "move" and car_id and action and duration:
        cmd_data.update({
            "car_id": car_id,
            "action": action,  # Agora usa o parâmetro action
            "duration": duration
        })

    print('Enviando:', cmd_data)  # Debug

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 65432))
            s.sendall(json.dumps(cmd_data).encode('utf-8'))
            response = s.recv(1024)
            print("Resposta do Unity:", response.decode())
            
            if command == "spawn_car":
                spawned_cars[response.decode()] = car_id
    except Exception as e:
        print(f"Erro ao conectar com o Unity: {e}")

def spawn_car(player_name):
    send_command("spawn_car", car_id=player_name)  # Envia no formato original

def move_car(car_id, direction, duration):
    send_command("move", car_id=car_id, action=direction, duration=duration)

# Exemplos de uso
# if __name__ == "__main__":
#     # Spawna um carro
#     spawn_car("Player1")
    
#     # Aguarda 1 segundo para garantir que o carro foi criado
#     time.sleep(1)
    
#     # Movimenta o carro (assumindo que sabemos o ID)
#     if spawned_cars:
#         car_id = next(iter(spawned_cars))  # Pega o primeiro carro spawnado
#         move_car(car_id, "forward", 5)  # Move para frente por 5 segundos
#         time.sleep(6)  # Aguarda a movimentação terminar
#         move_car(car_id, "right", 3)  # Vira à direita por 3 segundos