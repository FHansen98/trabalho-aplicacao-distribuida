Executar o build dos dockers e pods:

`rebuild_and_deploy.sh`

Encerrar todos os pods e containers:

`kubectl delete all --all`

Executar comunicação entre server e pods do mpi:

`python3 client_mpi_test.py`

Executar comunicação entre server e pods do spark:

`python3 client_spark_test.py`


KIBANA

Para subir o Docker do Kibana basta fazer:

`docker build -t USER/kibana:latest . `

Aplicar o kibana no cluste:

`kubectl apply -f kibana-deployment.yaml --namespace NOME-DO-CLUSTER`

Verifique se deu certo:

` kubectl get pods --namespace NOME-DO-CLUSTER`


verificar se o serviço tá rodando no pod: 

`kubectl get svc --namespace NOME-DO-CLUSTER`