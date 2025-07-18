Executar o build dos dockers e pods:

`rebuild_and_deploy.sh`

Encerrar todos os pods e containers:

`kubectl delete all --all`

Executar comunicação entre server e pods do mpi:

`python3 client_mpi_test.py`

Executar comunicação entre server e pods do spark:

`python3 client_spark_test.py`