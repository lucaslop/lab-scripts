# lab-folio-scripts

Ambiente de aprendizado com três rotinas reais rodando contra o **FOLIO
de demonstração pública** (`folio-snapshot-okapi.dev.folio.org`, tenant
`diku`) — nada do BIBLION é tocado. Pensado para aprender a stack antes
de levar os scripts do Dimas para o Kubernetes do Senado.

Este é o repositório de **código** — o que vira a imagem Docker. O
repositório irmão, `lab-folio-helm/`, é quem descreve *como implantar*
essa imagem no Kubernetes. A divisão em dois repositórios espelha, de
propósito, a forma real do Senado: `rvbi-scripts` (código) e
`helm-rvbi-scripts` (implantação) são repositórios Gitea separados —
ver a Parte 3 do PDF.

Este README é o resumo rápido. O guia completo, explicado passo a passo,
arquivo a arquivo, linha a linha — incluindo a teoria do padrão do Senado
e o passo a passo real de implantação lá — está no PDF que acompanha este
laboratório.

## Estrutura

    lib/folio.py                    Biblioteca: login, renovação de token, paginação
    scripts/relatorio_diario_acervo.py   Conta o acervo — roda 1x/dia
    scripts/monitor_disponibilidade.py   Mede disponibilidade/tempo — roda 1x/min
    scripts/buscar_no_acervo.py          Busca por CQL — sob demanda
    Dockerfile                      Empacota lib + scripts numa imagem
    jenkins/Dockerfile              Jenkins com Docker CLI, kubectl e helm embutidos
    Jenkinsfile                     Pipeline de BUILD: valida, testa contra o FOLIO, constrói, publica
    k8s/                            Um exercício avulso sobre Secrets (não é o deploy — veja k8s/README.md)
    config/.env.example             Modelo de configuração (copie para config/.env)

Quem implanta a imagem publicada por este repositório é o outro
repositório, `lab-folio-helm/` — veja o README dele.

## Início rápido (sem container)

    python -m venv .venv
    .venv\Scripts\Activate.ps1          # Windows
    pip install -r requirements.txt
    copy config\.env.example config\.env
    python scripts\monitor_disponibilidade.py

Não precisa editar o `.env`: já vem apontando para a demonstração
pública do FOLIO (login `diku_admin` / senha `admin`, públicos).

## Rodar os três

    python scripts\relatorio_diario_acervo.py
    python scripts\monitor_disponibilidade.py
    python scripts\buscar_no_acervo.py --titulo web
    python scripts\buscar_no_acervo.py --tipo exemplares --limite 10 --csv

## Construir e publicar a imagem

    docker run -d -p 5000:5000 --restart=always --name registry registry:2
    docker build -t localhost:5000/lab-folio:1 .
    docker run --rm --env-file config/.env localhost:5000/lab-folio:1 \
        python scripts/monitor_disponibilidade.py
    docker push localhost:5000/lab-folio:1

Depois de publicar, o deploy é feito pelo outro repositório — veja
`lab-folio-helm/README.md`. O PDF (Parte 2) explica cada linha do
Dockerfile e do Jenkinsfile, e cada arquivo de `lib/` e `scripts/`.

## Ordem sugerida de estudo

1. Rodar local com venv (acima)
2. Docker — empacotar e rodar em container
3. GitHub/Gitea — versionar o código (dois repositórios, como no Senado)
4. Kubernetes + Helm — ver `lab-folio-helm/README.md`
5. Jenkins — automatizar build e publicação da imagem (este repositório)
   e, no outro job, o `helm upgrade --install` (`lab-folio-helm`)
6. Rancher Server — operar pela interface web
7. Fluxo integrado — do commit ao CronJob rodando sozinho

## Aviso de segurança

`FOLIO_PASSWORD` neste laboratório é `admin`, senha pública do ambiente
de demonstração — não há segredo real aqui. Ainda assim, `config/.env`
está no `.gitignore` desde o primeiro commit: é o hábito que importa,
porque no Senado essa mesma variável carrega uma senha de verdade.
