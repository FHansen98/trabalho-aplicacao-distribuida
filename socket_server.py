import socket
import threading
import json
import time
import requests  # para fazer chamada HTTP para os engines

HOST = '0.0.0.0'
PORT = 5000

# Endereços internos dos pods dos engines no cluster Kubernetes
ENGINE_ENDPOINTS = {
    "spark": "http://engine-spark.default.svc.cluster.local:6500/compute",
    "mpi":   "http://engine-mpi.default.svc.cluster.local:6600/compute"
}

def handle_client(conn, addr):
    print(f"[SocketServer] Conexão recebida de {addr}")
    try:
        data = conn.recv(1024).decode()
        if not data:
            print(f"[SocketServer] Conexão com {addr} fechada sem dados.")
            return

        print(f"[SocketServer] Dados recebidos de {addr}: {data}")
        request = json.loads(data)
        engine = request.get("engine")

        if engine == "mpi":
            tamanho = request.get("tamanho", 10)
            geracoes = request.get("geracoes", 10)
            url = ENGINE_ENDPOINTS["mpi"]
            payload = {"tamanho": tamanho, "geracoes": geracoes}
            
            print(f"[SocketServer] Encaminhando para a engine MPI em {url} com payload: {payload}")
            try:
                print(f"[SocketServer] Tentando conectar ao MPI em {url}...")
                start_time = time.time()
                # Adicionado timeout de 5 minutos (300s) para o cálculo MPI
                response = requests.post(url, json=payload, timeout=300)
                duration = time.time() - start_time

                print(f"[SocketServer] Conexão bem-sucedida com MPI. Status da resposta: {response.status_code}")
                
                result = response.json()
                result["duration"] = duration
                final_response = json.dumps(result).encode()
                
                print(f"[SocketServer] Enviando resposta final para o cliente: {final_response.decode()}")
                conn.sendall(final_response)

            except requests.exceptions.RequestException as e:
                print(f"[SocketServer] Erro detalhado na conexão com MPI: {str(e)}")
                conn.sendall(json.dumps({"error": "falha ao contatar a engine mpi", "details": str(e)}).encode())
        
        elif engine in ENGINE_ENDPOINTS:
            powmin = request.get("powmin")
            powmax = request.get("powmax")
            print(f"[SocketServer] Encaminhando para a engine {engine} com powmin={powmin}, powmax={powmax}")
            start_time = time.time()
            response = requests.post(ENGINE_ENDPOINTS[engine], json={
                "powmin": powmin,
                "powmax": powmax
            })
            duration = time.time() - start_time
            result = response.json()
            result["duration"] = duration
            conn.sendall(json.dumps(result).encode())
        else:
            print(f"[SocketServer] Engine inválida solicitada: {engine}")
            conn.sendall(b'{"error": "engine invalido"}')

    except json.JSONDecodeError:
        print(f"[SocketServer] Erro de JSON de {addr}: {data}")
        conn.sendall(b'{"error": "json invalido"}')
    except Exception as e:
        print(f"[SocketServer] Erro inesperado com {addr}: {e}")
        conn.sendall(json.dumps({"error": str(e)}).encode())
    finally:
        conn.close()
        print(f"[SocketServer] Conexão com {addr} encerrada.")

def start_server():
    print(f"[~] Servidor escutando em {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
            print(f"[=] Número de conexões ativas: {threading.active_count() - 1}")

if __name__ == "__main__":
    start_server()