FROM python:3.12-slim

# Fuso de Brasília — sem isto, o container roda em UTC e os agendamentos
# ficam três horas adiantados
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    DIR_SAIDA=/dados

WORKDIR /app

# Dependências antes do código: o cache do Docker só se invalida
# quando requirements.txt muda, então rebuild fica rápido
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lib/ ./lib/
COPY scripts/ ./scripts/

# Usuário sem privilégio — exigência comum de cluster corporativo
RUN useradd --create-home --uid 10001 lab \
    && mkdir -p /dados && chown -R lab:lab /app /dados
USER lab

# Sem comando fixo: cada Job/CronJob escolhe qual script rodar
CMD ["python", "-c", "print('Informe o script a executar. Ex.: python scripts/monitor_disponibilidade.py')"]
