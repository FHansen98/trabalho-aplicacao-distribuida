#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <mpi.h>
#include <omp.h>

#define ind2d(i,j) (i)*(tam+2)+j
#define POWMIN 3
#define POWMAX 10

double wall_time(void) {
  struct timeval tv;
  struct timezone tz;

  gettimeofday(&tv, &tz);
  return(tv.tv_sec + tv.tv_usec/1000000.0);
}

void UmaVida(int* tabulIn, int* tabulOut, int tam, int inicio_linha, int fim_linha) {
  int i, j, vizviv;

  #pragma omp parallel for private(j, vizviv)
  for (i = inicio_linha; i <= fim_linha; i++) {
    for (j = 1; j <= tam; j++) {
      vizviv =  tabulIn[ind2d(i-1,j-1)] + tabulIn[ind2d(i-1,j  )] +
                tabulIn[ind2d(i-1,j+1)] + tabulIn[ind2d(i  ,j-1)] +
                tabulIn[ind2d(i  ,j+1)] + tabulIn[ind2d(i+1,j-1)] +
                tabulIn[ind2d(i+1,j  )] + tabulIn[ind2d(i+1,j+1)];
      if (tabulIn[ind2d(i,j)] && vizviv < 2)
        tabulOut[ind2d(i,j)] = 0;
      else if (tabulIn[ind2d(i,j)] && vizviv > 3)
        tabulOut[ind2d(i,j)] = 0;
      else if (!tabulIn[ind2d(i,j)] && vizviv == 3)
        tabulOut[ind2d(i,j)] = 1;
      else
        tabulOut[ind2d(i,j)] = tabulIn[ind2d(i,j)];
    }
  }
}

void InitTabul(int* tabulIn, int* tabulOut, int tam){
  int ij;

  for (ij=0; ij<(tam+2)*(tam+2); ij++) {
    tabulIn[ij] = 0;
    tabulOut[ij] = 0;
  }

  tabulIn[ind2d(1,2)] = 1;
  tabulIn[ind2d(2,3)] = 1;
  tabulIn[ind2d(3,1)] = 1;
  tabulIn[ind2d(3,2)] = 1;
  tabulIn[ind2d(3,3)] = 1;
}

int Correto(int* tabul, int tam){
  int ij, cnt;

  cnt = 0;
  for (ij=0; ij<(tam+2)*(tam+2); ij++)
    cnt = cnt + tabul[ij];
  return (cnt == 5 && tabul[ind2d(tam-2,tam-1)] &&
      tabul[ind2d(tam-1,tam  )] && tabul[ind2d(tam  ,tam-2)] &&
      tabul[ind2d(tam  ,tam-1)] && tabul[ind2d(tam  ,tam  )]);
}

int main(int argc, char **argv) {
  int pow, rank, size;
  int i, tam, *tabulIn, *tabulOut;
  double t0, t1, t2, t3;

  MPI_Init(&argc, &argv);
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  for (pow = POWMIN; pow <= POWMAX; pow++) {
    tam = 1 << pow;

    t0 = wall_time();
    tabulIn  = (int *) malloc ((tam+2)*(tam+2)*sizeof(int));
    tabulOut = (int *) malloc ((tam+2)*(tam+2)*sizeof(int));

    for (int ij = 0; ij < (tam + 2) * (tam + 2); ij++) {
        tabulIn[ij] = 0;
        tabulOut[ij] = 0;
    }

    if (rank == 0) {
      InitTabul(tabulIn, tabulOut, tam);
    }

    MPI_Bcast(tabulIn, (tam+2)*(tam+2), MPI_INT, 0, MPI_COMM_WORLD);
    
    t1 = wall_time();

    int linhas_por_proc = tam / size;
    int resto = tam % size;

    int inicio_linha, fim_linha;
    if (rank < resto) {
        inicio_linha = 1 + rank * (linhas_por_proc + 1);
        fim_linha = inicio_linha + linhas_por_proc;
    } else {
        inicio_linha = 1 + resto * (linhas_por_proc + 1) + (rank - resto) * linhas_por_proc;
        fim_linha = inicio_linha + linhas_por_proc - 1;
    }
    
    if (fim_linha > tam) fim_linha = tam;
    
    int sendcount = (fim_linha - inicio_linha + 1) * (tam + 2);
    
    int *recvcounts = (int *) malloc(size * sizeof(int));
    int *displs = (int *) malloc(size * sizeof(int));
    
    for (int p = 0; p < size; p++) {
        int p_inicio, p_fim;
        if (p < resto) {
            p_inicio = 1 + p * (linhas_por_proc + 1);
            p_fim = p_inicio + linhas_por_proc;
        } else {
            p_inicio = 1 + resto * (linhas_por_proc + 1) + (p - resto) * linhas_por_proc;
            p_fim = p_inicio + linhas_por_proc - 1;
        }
        if (p_fim > tam) p_fim = tam;
        
        recvcounts[p] = (p_fim - p_inicio + 1) * (tam + 2);
        displs[p] = ind2d(p_inicio, 0);
    }

    int *board_in = tabulIn;
    int *board_out = tabulOut;

    for (i = 0; i < 4 * (tam - 3); i++) {
        UmaVida(board_in, board_out, tam, inicio_linha, fim_linha);

        MPI_Gatherv(
            &board_out[ind2d(inicio_linha, 0)],
            sendcount,
            MPI_INT,
            board_out,
            recvcounts,
            displs,
            MPI_INT,
            0, 
            MPI_COMM_WORLD
        );

        MPI_Bcast(board_out, (tam+2)*(tam+2), MPI_INT, 0, MPI_COMM_WORLD);

        int *temp = board_in;
        board_in = board_out;
        board_out = temp;
    }

    t2 = wall_time();
    
    if (rank == 0) {
      if (Correto(tabulIn, tam))
        printf("**RESULTADO CORRETO**\n");
      else
        printf("**RESULTADO ERRADO**\n");

      t3 = wall_time();
      printf("tam=%d; tempos: init=%7.7f, comp=%7.7f, fim=%7.7f, tot=%7.7f \n",
             tam, t1-t0, t2-t1, t3-t2, t3-t0);

    }
    free(recvcounts);
    free(displs);
    free(tabulIn);
    free(tabulOut);
  } /* fim-for tam */
  MPI_Finalize();
  return 0;
}