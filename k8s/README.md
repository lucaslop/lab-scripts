# k8s/ — exercício avulso, não é o deploy

A implantação real deste laboratório **não usa mais manifestos YAML soltos
aplicados com `kubectl apply -f`**: ela usa o Helm chart do repositório
irmão, `lab-folio-helm/chart/`, do mesmo jeito que o Senado separa
`rvbi-scripts` (código, este repositório) de `helm-rvbi-scripts`
(implantação). Veja o PDF do laboratório, Parte 2, para o passo a passo
com o Helm.

O único arquivo que sobrou aqui, `secrets-formas-de-uso.yaml`, é um
exercício isolado e intencional: três `Job`s que mostram, lado a lado, as
três formas de um container consumir um `Secret` do Kubernetes (variável de
ambiente em bloco, variável única renomeada, e arquivo montado). Ele não
faz parte do fluxo de implantação — é só para rodar uma vez, comparar as
três saídas e entender a diferença antes de ver `envFrom` sendo usado "sem
explicação" dentro do chart.

    kubectl apply -f k8s/secrets-formas-de-uso.yaml
    kubectl -n adm-lab-folio logs job/secret-forma-1
    kubectl -n adm-lab-folio logs job/secret-forma-2
    kubectl -n adm-lab-folio logs job/secret-forma-3
    kubectl delete -f k8s/secrets-formas-de-uso.yaml   # limpa depois de comparar
