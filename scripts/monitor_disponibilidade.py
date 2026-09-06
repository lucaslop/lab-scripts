# -*- coding: utf-8 -*-
"""
Monitor de disponibilidade e tempo de resposta do BIBLION.

Implementa a medição independente dos indicadores do Contrato 2024/0057:
  SLU-01  disponibilidade >= 99,5%   (fator FC)
  SLU-02  tempo de resposta <= 2 s   (IDBL <= 1)

Grava cada medição em CSV e recalcula os indicadores sobre todo o histórico.
Somente LEITURA: não altera nenhum dado do catálogo.

Uso:
    python scripts/monitor_disponibilidade.py
"""
import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.folio import FolioClient, FolioError, BASE_URL, TENANT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DIR_SAIDA = Path(os.getenv("DIR_SAIDA", "./dados"))
LIMITE_SEG = float(os.getenv("LIMITE_RESPOSTA_SEG", "2.0"))
META_DISP = float(os.getenv("META_DISPONIBILIDADE", "99.5"))
ENDPOINT = os.getenv("MONITOR_ENDPOINT", "/instance-storage/instances")


def medir():
    """Uma medição. Devolve (disponivel, tempo, detalhe)."""
    try:
        cliente = FolioClient()
        dados, tempo = cliente.get(ENDPOINT, {"limit": 1}, tentativas=1)
        return True, tempo, f"{dados.get('totalRecords', '?')} registros"
    except FolioError as e:
        return False, None, str(e)[:150]
    except Exception as e:
        return False, None, f"{type(e).__name__}: {str(e)[:130]}"


def main() -> int:
    agora = datetime.now()
    carimbo = agora.strftime("%Y-%m-%d %H:%M:%S")
    disponivel, tempo, detalhe = medir()

    if disponivel:
        dentro = tempo <= LIMITE_SEG
        print(f"[{carimbo}] {'OK' if dentro else 'LENTO'}   | {tempo:.3f}s | {detalhe}")
        if not dentro:
            print(f"           ATENCAO: acima do limite de {LIMITE_SEG}s (SLU-02)")
    else:
        print(f"[{carimbo}] INDISPONIVEL | {detalhe}")

    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    arquivo = DIR_SAIDA / f"{agora.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    novo = not arquivo.exists()
    with arquivo.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["data_hora", "ambiente", "disponivel",
                        "tempo_resposta_seg", "detalhe"])
        w.writerow([carimbo, BASE_URL, "sim" if disponivel else "nao",
                    f"{tempo:.3f}" if tempo else "", detalhe])

    with arquivo.open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))

    total = len(linhas)
    sucessos = [l for l in linhas if l["disponivel"] == "sim"]
    tempos = [float(l["tempo_resposta_seg"]) for l in sucessos if l["tempo_resposta_seg"]]

    if total:
        disp = 100.0 * len(sucessos) / total
        situacao = "ATENDE" if disp >= META_DISP else "ABAIXO DA META"
        print(f"           Historico: {total} medicoes | disponibilidade "
              f"{disp:.3f}% ({situacao} {META_DISP}%)")
        if tempos:
            acima = sum(1 for t in tempos if t > LIMITE_SEG)
            print(f"           Tempo medio {sum(tempos)/len(tempos):.3f}s | "
                  f"maximo {max(tempos):.3f}s | {acima} acima de {LIMITE_SEG}s")

    # Sempre 0: a indisponibilidade e o DADO, nao uma falha do script.
    # Retornar 1 faria o Kubernetes reexecutar o monitor a cada queda.
    return 0


if __name__ == "__main__":
    sys.exit(main())
