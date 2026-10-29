# Fase 0: verificação do motor

Data: 2026-10-29. Máquina: Windows 11 do Silvestre. Motor: `gosom/google-maps-scraper` v1.18.1.

## Decisão

Docker é o caminho principal da v1. O programa direto falhou no Windows e vira pesquisa futura, fora do escopo da v1. O Chromium de 114 MB que o programa direto baixa sozinho não entra na lista de instalação, porque o Docker já traz o navegador dentro da imagem.

## Resultado

| Item | Resultado |
| --- | --- |
| Motor em Docker (`docker compose up -d`) | Sobe e responde em `http://127.0.0.1:8080` |
| Rota `GET /api/v1/jobs` | Responde 200 (lista vazia aparece como `null`) |
| Porta exposta só no próprio computador | Confere: pelo IP da rede a porta não responde. A API não valida o `Host`, então a proteção é a porta presa a `127.0.0.1` |
| Job manual pela API | `POST /api/v1/jobs` devolveu 201 com o `id`. O status foi de `working` para `ok` em cerca de 30 s |
| Download do CSV | `GET /api/v1/jobs/{id}/download` devolveu 16 linhas (`padaria em Sobradinho DF`, `depth` 1) |
| Programa direto (`.exe` v1.18.1) | Não funciona neste Windows. Quatro tentativas, com e sem `-debug`, terminaram com `unexpected page type` e CSV vazio. Causa não investigada. O SHA-256 do `.exe` baixado confere com o publicado |
| Docker Desktop | Instalado (29.7.2). O serviço estava desligado e subiu em 20 s ao abrir o Docker Desktop |

## Parâmetros da API confirmados com execução real

Corpo do `POST /api/v1/jobs` que funcionou:

```json
{"name":"fase0","keywords":["padaria em Sobradinho DF"],"lang":"pt","zoom":15,
 "lat":"-15.65","lon":"-47.79","fast_mode":false,"radius":10000,"depth":1,
 "email":false,"max_time":180}
```

- `lang` aceita código de duas letras. `pt-BR` volta `422 invalid lang`.
- `lat` e `lon` são enviados como texto.
- `max_time` é enviado em segundos e a API devolve em nanossegundos (180 viram `180000000000`).
- O status do job é `working` e depois `ok`. Os outros valores de status (falha, cancelado) ainda não foram observados.
- Sem `email: true` o campo `emails` do CSV vem vazio.

## Colunas reais do CSV (36)

`input_id, link, title, category, address, open_hours, popular_times, website, phone, plus_code, review_count, review_rating, reviews_per_rating, latitude, longitude, cid, status, descriptions, reviews_link, thumbnail, timezone, price_range, data_id, street_view_url, place_id, images, reservations, order_online, menu, owner, complete_address, credit_cards_accepted, about, user_reviews, user_reviews_extended, emails`

Lições para a fase 1:

- Os campos que a nota usa existem: `website`, `phone`, `review_count`, `review_rating`, `order_online`, `reservations`, `emails`.
- `place_id` e `cid` vieram preenchidos em todas as linhas e servem de chave contra duplicados.
- `order_online` e `reservations` trazem JSON, não texto simples.
- `emails` só vem com a opção de e-mail ligada no job.
- Na busca de padarias, parte dos leads veio sem `website` e sem `phone`, então a regra `sem_site` tem material real.

## Ainda falta conferir

- **ARM:** não foi conferido se a imagem roda em computadores com processador ARM (Windows ARM e Macs com chip Apple). O kit de referência de Mahan diz que a imagem publicada é `linux/amd64` e que no chip Apple ela roda por emulação. Até testar, o material de venda só cita Windows x64.
- Os outros valores de `Status` de um job (falha, cancelado) e o que acontece quando o Google bloqueia.
- Comportamento do motor depois de reiniciar o computador (`restart: unless-stopped`).
- Testar em Docker num computador limpo, sem Docker instalado, como a instalação do comprador vai fazer.
- Por que o programa direto falha (pesquisa futura).

## Kit base de Mahan

Clonado em `..\referencia-kit-base`, só para consulta (MIT, © 2026 Mahan). Reaproveitado como ideia, com créditos no `CREDITS.md`: o desenho do `docker-compose.yml` (porta presa a `127.0.0.1`, volumes, imagem fixada), a forma de falar com `/api/v1/jobs` e a busca em grade para passar do limite de resultados por busca. Nada de texto ou documentação dele foi copiado.
