import socket
import json

def spawn_car(name):
    car_data = {
        "command": "spawn_car",
        "position": {"x": 0, "y": 0, "z": 0},
        "color": "blue",
        "type": "player",
        "speed": 10
    }

    # Configuração do socket
    host = 'localhost'  # IP do Unity (mesma máquina)
    port = 65432        # Porta que o Unity está ouvindo
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            # Envia os dados do carro como JSON
            s.sendall(json.dumps(car_data).encode('utf-8'))
            response = s.recv(1024)  # Espera resposta do Unity
            print("Resposta do Unity:", response.decode())
    except Exception as e:
        print(f"Erro ao conectar com o Unity: {e}")