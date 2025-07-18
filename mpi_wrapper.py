from flask import Flask, request, jsonify, Response
import subprocess
import json
import traceback
import sys

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    print("[MPI_Wrapper] Requisição recebida em /health")
    return jsonify({"status": "ok", "message": "MPI service is running"})

@app.route('/compute', methods=['POST'])
def compute():
    print("[MPI_Wrapper] Requisição recebida em /compute")
    params = request.get_json()
    if not params:
        print("[MPI_Wrapper] Erro: Corpo da requisição JSON inválido ou vazio")
        return jsonify({"error": "Corpo da requisição JSON inválido ou vazio"}), 400

    tamanho = params.get("tamanho", 128)
    geracoes = params.get("geracoes", 10)
    print(f"[MPI_Wrapper] Parâmetros: tamanho={tamanho}, geracoes={geracoes}")

    # O nome do executável deve corresponder ao que está no Dockerfile.mpi
    cmd = [
        "mpirun", "--allow-run-as-root", "-np", "2",
        "/app/jogodavida_mpi", str(tamanho), str(geracoes)
    ]
    print(f"[MPI_Wrapper] Executando comando: {' '.join(cmd)}")
    print(f"[MPI_Wrapper] Parâmetros passados: tamanho={tamanho}, geracoes={geracoes}")

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=290
        )
        print(f"[MPI_Wrapper] Execução do C finalizada com sucesso.")
        print(f"[MPI_Wrapper] Saída (stdout) do C: {result.stdout.strip()}")
        if result.stdout:
            return jsonify({"status": "ok", "message": result.stdout})

        # try:
        #     # Verificar se a saída é um JSON válido
        #     json.loads(result.stdout)
        #     # A saída JSON do programa C é o corpo da resposta
        #     return Response(result.stdout, mimetype='application/json')
        # except json.JSONDecodeError as e:
        #     print(f"[MPI_Wrapper] ERRO: A saída do programa C não é um JSON válido: {e}")
        #     print(f"[MPI_Wrapper] Saída bruta: {repr(result.stdout)}")
        #     return jsonify({"error": "Saída do programa C não é um JSON válido", "output": result.stdout}), 500

    except subprocess.CalledProcessError as e:
        print(f"[MPI_Wrapper] Erro na execução do MPI (CalledProcessError).")
        # Logar stdout e stderr para depuração
        error_details = {
            "stdout": e.stdout.strip(),
            "stderr": e.stderr.strip()
        }
        print(f"[MPI_Wrapper] STDOUT: {error_details['stdout']}")
        print(f"[MPI_Wrapper] STDERR: {error_details['stderr']}")
        return jsonify({"error": "Erro na execução do MPI", "details": error_details}), 500
    
    except subprocess.TimeoutExpired as e:
        print(f"[MPI_Wrapper] Timeout na execução do MPI.")
        return jsonify({"error": "Timeout na execução do MPI", "stdout": e.stdout, "stderr": e.stderr}), 500

    except Exception as e:
        print(f"[MPI_Wrapper] Erro inesperado: {str(e)}")
        print(f"[MPI_Wrapper] Traceback completo:")
        traceback.print_exc(file=sys.stdout)
        return jsonify({"error": "Erro inesperado no wrapper MPI", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6600)
