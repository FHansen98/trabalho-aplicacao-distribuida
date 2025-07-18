import socket
import json

def main():
    host = '127.0.0.1'
    port = 5001  # A porta NodePort mapeada no kind-config.yaml

    request_data = {
        "engine": "spark",
        "tamanho": 3,
        "geracoes": 1
    }
    
    request_json = json.dumps(request_data)
    print(f"[Cliente Spark] Conectando ao servidor em {host}:{port}...")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            print("[Cliente Spark] Conectado.")
            
            # Envia a solicitação
            print(f"[Cliente Spark] Enviando dados: {request_json}")
            s.sendall(request_json.encode('utf-8'))
            
            print("[Cliente Spark] Solicitação enviada. Aguardando resposta...")
            
            # Aguarda a resposta
            response_data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    print("[Cliente Spark] Conexão fechada pelo servidor.")
                    break
                response_data += chunk
            
            print("\n--- Resposta do Servidor (Spark) ---")
            try:
                response_json = json.loads(response_data.decode('utf-8'))
                print(json.dumps(response_json, indent=2))
            except json.JSONDecodeError:
                print("Não foi possível decodificar a resposta como JSON:")
                print(response_data.decode('utf-8'))
            print("------------------------------------\n")

    except ConnectionRefusedError:
        print(f"Erro: A conexão foi recusada. Verifique se o servidor está rodando e a porta {port} está correta.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()
