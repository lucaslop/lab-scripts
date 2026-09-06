# -*- coding: utf-8 -*-
"""
Busca no acervo do BIBLION por CQL, com parâmetros de linha de comando.

Cada execução é uma pergunta diferente — por isso, ao contrário dos outros
dois scripts, este não faz sentido agendar. No Kubernetes ele vira um
CronJob suspenso (cadastrado, mas que nunca dispara sozinho), usado como
molde para disparos manuais com argumentos variados.

Uso:
    python scripts/buscar_no_acervo.py --titulo web
    python scripts/buscar_no_acervo.py --titulo europe --csv
    python scripts/buscar_no_acervo.py --cql 'title all "primer"' --limite 5
    python scripts/buscar_no_acervo.py --tipo exemplares --limite 10 --csv
    python scripts/buscar_no_acervo.py --tipo usuarios --limite 20
"""
import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.folio import FolioClient, FolioError, BASE_URL, TENANT

DIR_SAIDA = Path("./dados")

ENDPOINTS = {
    "instancias": ("/instance-storage/instances", "instances",
                   ["hrid", "title", "source"]),
    "exemplares": ("/item-storage/items", "items",
                   ["hrid", "barcode", "status.name"]),
    "usuarios": ("/users", "users",
                 ["username", "active", "personal.lastName"]),
}


def valor_aninhado(registro, caminho):
    """Lê um campo tipo 'status.name' de dentro de um dict aninhado."""
    atual = registro
    for parte in caminho.split("."):
        if not isinstance(atual, dict):
            return ""
        atual = atual.get(parte, "")
    return atual


def montar_query(args):
    if args.cql:
        return args.cql
    if args.titulo:
        return f'title all "{args.titulo}"'
    return "cql.allRecords=1"


def main() -> int:
    p = argparse.ArgumentParser(description="Busca no acervo do BIBLION por CQL.")
    p.add_argument("--tipo", choices=list(ENDPOINTS), default="instancias",
                    help="o que buscar (padrão: instancias)")
    p.add_argument("--titulo", help="atalho: busca por título contendo o termo")
    p.add_argument("--cql", help="expressão CQL completa (sobrepõe --titulo)")
    p.add_argument("--limite", type=int, default=20, help="máximo de registros (padrão: 20)")
    p.add_argument("--csv", action="store_true", help="também exporta o resultado em CSV")
    args = p.parse_args()

    caminho, chave, colunas = ENDPOINTS[args.tipo]
    query = montar_query(args)

    print("=" * 70)
    print(f"  BUSCA NO ACERVO — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  Ambiente : {BASE_URL} (tenant {TENANT})")
    print(f"  Buscando : {args.tipo}")
    print(f"  CQL      : {query}")
    print("=" * 70)
    print()

    try:
        cliente = FolioClient()
        cliente.login()
        dados, tempo = cliente.get(caminho, {"query": query, "limit": args.limite})
    except FolioError as e:
        print(f"[ERRO] Busca falhou: {e}")
        return 1

    registros = dados.get(chave, [])
    total = dados.get("totalRecords", len(registros))
    print(f"  {total} registro(s) encontrado(s) — exibindo {len(registros)} "
          f"(resposta em {tempo:.2f}s)")
    print()

    cabecalho = " | ".join(f"{c:<20}" for c in colunas)
    print(f"  {cabecalho}")
    print("  " + "-" * len(cabecalho))
    for r in registros:
        linha = " | ".join(f"{str(valor_aninhado(r, c))[:20]:<20}" for c in colunas)
        print(f"  {linha}")
    print()

    if args.csv:
        DIR_SAIDA.mkdir(parents=True, exist_ok=True)
        carimbo = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        arquivo = DIR_SAIDA / f"busca_{args.tipo}_{carimbo}.csv"
        with arquivo.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(colunas)
            for r in registros:
                w.writerow([valor_aninhado(r, c) for c in colunas])
        print(f"[OK] CSV exportado: {arquivo.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
