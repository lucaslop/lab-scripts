# -*- coding: utf-8 -*-
"""
Relatório diário do acervo do BIBLION.

Conta instâncias, holdings, exemplares, empréstimos e usuários; detalha
exemplares por tipo de material e por status. Acumula uma linha por dia
num histórico CSV. Somente LEITURA: não altera nenhum dado do catálogo.

Usa contagem por API (limit=0) sempre que possível — não baixa os
registros inteiros só para contar, o que evita minutos de tráfego
desnecessário num acervo grande.

Uso:
    python scripts/relatorio_diario_acervo.py
"""
import csv
import logging
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.folio import FolioClient, FolioError, BASE_URL, TENANT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DIR_SAIDA = Path(os.getenv("DIR_SAIDA", "./dados"))


def mapa_tipos_material(cliente):
    """id -> nome, para traduzir materialTypeId dos exemplares."""
    tipos = cliente.get_todos("/material-types", "mtypes", pagina=200)
    return {t["id"]: t.get("name", "?") for t in tipos}


def contagem_por_tipo_material(cliente, mapa_tipos):
    """
    Os exemplares não trazem o nome do tipo de material embutido, só o id
    (materialTypeId) — por isso é preciso baixar os exemplares (não dá para
    usar limit=0 aqui) e agrupar localmente.
    """
    exemplares = cliente.get_todos("/item-storage/items", "items", pagina=200)
    contagem = Counter(mapa_tipos.get(i.get("materialTypeId"), "desconhecido") for i in exemplares)
    return contagem, len(exemplares)


def contagem_por_status(exemplares_ja_baixados=None, cliente=None):
    if exemplares_ja_baixados is None:
        exemplares_ja_baixados = cliente.get_todos("/item-storage/items", "items", pagina=200)
    return Counter(i.get("status", {}).get("name", "?") for i in exemplares_ja_baixados)


def main() -> int:
    agora = datetime.now()
    carimbo = agora.strftime("%d/%m/%Y %H:%M:%S")

    try:
        cliente = FolioClient()
        cliente.login()

        totais = {}
        totais["instâncias"] = cliente.contar("/instance-storage/instances")
        totais["holdings"] = cliente.contar("/holdings-storage/holdings")
        totais["empréstimos"] = cliente.contar("/circulation/loans")
        totais["usuários"] = cliente.contar("/users")

        mapa_tipos = mapa_tipos_material(cliente)
        por_tipo, total_exemplares = contagem_por_tipo_material(cliente, mapa_tipos)
        totais["exemplares"] = total_exemplares
        por_status = contagem_por_status(cliente=cliente)  # recalcula: consulta independente

    except FolioError as e:
        print(f"[ERRO] Não consegui gerar o relatório: {e}")
        return 1

    print("=" * 60)
    print(f"  RELATÓRIO DIÁRIO DO ACERVO — {carimbo}")
    print(f"  Ambiente: {BASE_URL}  |  tenant: {TENANT}")
    print("=" * 60)
    print()
    print("  TOTAIS")
    for rotulo, valor in totais.items():
        print(f"    {rotulo:.<20} {valor:>6}")
    print()
    print("  EXEMPLARES POR TIPO DE MATERIAL")
    for tipo, qtd in por_tipo.most_common():
        print(f"    {tipo:.<24} {qtd:>6}")
    print()
    print("  EXEMPLARES POR STATUS")
    for status, qtd in por_status.most_common():
        print(f"    {status:.<24} {qtd:>6}")
    print()

    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    arquivo = DIR_SAIDA / f"acervo_{agora.strftime('%d-%m-%Y-%H-%M-%S')}.csv"
    novo = not arquivo.exists()
    with arquivo.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["data_hora", "instancias", "holdings", "exemplares",
                        "emprestimos", "usuarios"])
        w.writerow([carimbo, totais["instâncias"], totais["holdings"],
                    totais["exemplares"], totais["empréstimos"], totais["usuários"]])

    print(f"[OK] Histórico atualizado: {arquivo.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
