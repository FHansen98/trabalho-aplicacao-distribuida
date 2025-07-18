from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum as _sum
from flask import Flask, request, jsonify
import time

# Inicializa o Flask App
app = Flask(__name__)

# Inicializa a SparkSession globalmente para ser reutilizada
spark = SparkSession.builder.appName("GameOfLifeSpark").getOrCreate()
sc = spark.sparkContext

# --- Configurações do Jogo da Vida ---
# Tamanho do tabuleiro (mesmo valor do NGER no .c)
TAM = 2048
# Número de gerações para simular
NGER = 5

def get_neighbors(x, y, max_x, max_y):
    """Gera os 8 vizinhos de uma célula (x, y)."""
    neighbors = []
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                continue
            nx, ny = x + i, y + j
            if 0 <= nx < max_x and 0 <= ny < max_y:
                neighbors.append((nx, ny))
    return neighbors

def game_of_life_step(live_cells_rdd):
    """Executa um passo (uma geração) do Jogo da Vida."""
    # Para cada célula viva, emita seus vizinhos com contagem 1
    # Isso marca cada vizinho como tendo uma célula viva próxima
    neighbor_counts_rdd = live_cells_rdd.flatMap(
        lambda cell: [(neighbor, 1) for neighbor in get_neighbors(cell[0], cell[1], TAM, TAM)]
    ).reduceByKey(lambda a, b: a + b)

    # Junta as células vivas com a contagem de vizinhos
    # Células que não estão em neighbor_counts_rdd mas estão em live_cells_rdd têm 0 vizinhos
    live_cells_with_neighbors = live_cells_rdd.map(lambda cell: (cell, None)).leftOuterJoin(neighbor_counts_rdd)

    # Aplica as regras de sobrevivência
    # Uma célula viva sobrevive se tiver 2 ou 3 vizinhos
    surviving_cells = live_cells_with_neighbors.filter(
        lambda x: x[1][1] is not None and x[1][1] in [2, 3]
    ).map(lambda x: x[0])

    # Junta as contagens de vizinhos com as células vivas para encontrar células mortas que podem nascer
    # Uma célula morta nasce se tiver exatamente 3 vizinhos
    newborn_cells = neighbor_counts_rdd.leftOuterJoin(
        live_cells_rdd.map(lambda cell: (cell, True))
    ).filter(
        lambda x: x[1][1] is None and x[1][0] == 3
    ).map(lambda x: x[0])

    # A nova geração é a união das células que sobreviveram e das que nasceram
    return surviving_cells.union(newborn_cells).distinct()

def initialize_glider(N):
    # Inicializa o tabuleiro com o padrão "glider" (veleiro)
    # O mesmo padrão do código C para validação
    initial_glider = [
        (0, 1), (1, 2), (2, 0), (2, 1), (2, 2)
    ]
    return initial_glider

def next_generation(board_rdd, N):
    # Executa um passo (uma geração) do Jogo da Vida.
    return game_of_life_step(board_rdd)

@app.route('/compute', methods=['POST'])
def compute():
    # Extrai parâmetros da requisição JSON
    params = request.get_json()
    N = params.get("tamanho", 128)  # Tamanho do tabuleiro
    generations = params.get("geracoes", 5) # Número de gerações

    # Inicializa o tabuleiro com o padrão "glider"
    board = initialize_glider(N)

    # Converte a lista de listas para um RDD
    board_rdd = sc.parallelize(board)

    # Executa as gerações
    start_time = time.time()
    for _ in range(generations):
        board_rdd = next_generation(board_rdd, N)
        board_rdd.cache()
        board_rdd.count() # Ação para forçar a computação
    
    computation_time = time.time() - start_time

    # Coleta os resultados e conta as células vivas
    final_board = board_rdd.collect()
    live_cells = len(final_board)

    # Retorna o resultado como JSON
    return jsonify({
        "engine": "spark",
        "tamanho_tabuleiro": N,
        "numero_geracoes": generations,
        "celulas_vivas": live_cells,
        "tempo_computacao_s": computation_time
    })

if __name__ == "__main__":
    # O host '0.0.0.0' torna o servidor acessível externamente (dentro do cluster)
    app.run(host='0.0.0.0', port=6500)
