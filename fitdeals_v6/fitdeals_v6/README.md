# FitDeals V6

Versão voltada a corrigir o problema em que o OAuth aparece conectado, mas a coleta de ofertas não retorna produtos.

## O que mudou

1. A conexão é validada de verdade usando `GET /users/me` com o access token.
2. A busca usa `GET /sites/MLB/search` para encontrar candidatos.
3. Para descobrir o preço atual do anúncio, a aplicação tenta primeiro `GET /items/{ITEM_ID}/sale_price?context=channel_marketplace`, que é o endpoint atual para identificar o preço vencedor de venda e o `regular_amount` quando existe promoção.
4. Se `sale_price` falhar, tenta `GET /items/{ITEM_ID}/prices`.
5. Se os endpoints de preço falharem, usa os campos do resultado da busca somente como fallback.
6. O painel agora mostra quantos itens foram encontrados, quantas consultas de preço foram feitas e os erros reais.
7. Existe `GET /api/test-search?q=creatina` para separar problema de busca de problema de preço/OAuth.
8. OAuth usa PKCE por padrão e guarda o estado no SQLite.
9. O refresh token é preservado quando a resposta de renovação não o devolve explicitamente.
10. Não inventa cupom nem transforma automaticamente o link normal em link de afiliado.

## Render

Build:
`pip install -r requirements.txt`

Start:
`python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Root Directory: vazio, se os arquivos estiverem na raiz do repositório.

## Variáveis principais

- `ML_CLIENT_ID`: Client ID do aplicativo no Mercado Livre.
- `ML_CLIENT_SECRET`: Secret Key do aplicativo.
- `ML_REDIRECT_URI`: exatamente `https://SEU_DOMINIO.onrender.com/auth/mercadolivre/callback`.
- `ADMIN_PASSWORD`: senha do painel.
- `MAX_PRICE`: preço máximo.
- `MIN_DISCOUNT`: desconto mínimo em porcentagem.
- `REQUIRE_DISCOUNT`: `true` para salvar somente produtos com desconto detectado.

Para o primeiro teste, recomenda-se:

`MAX_PRICE=500`
`MIN_DISCOUNT=0`
`REQUIRE_DISCOUNT=false`

Assim o objetivo inicial é comprovar que a busca e os preços estão chegando. Depois, pode subir `MIN_DISCOUNT` e ativar `REQUIRE_DISCOUNT`.

## Fluxo de teste

1. Faça o deploy.
2. Abra o painel.
3. Entre com `ADMIN_PASSWORD`.
4. Verifique se aparece `Conectado como ...`.
5. Clique em `Testar busca` com `creatina`. O retorno deve mostrar `count` e itens.
6. Clique em `Buscar ofertas agora`.
7. O bloco de diagnóstico mostra `search_candidates`, `unique_candidates`, `price_calls` e os erros por consulta.

## Observação sobre preços

A documentação atual do Mercado Livre recomenda os endpoints de preços para consultar o valor atual, e mostra `sale_price` com `amount` e `regular_amount`. Também orienta enviar o access token no header das chamadas autenticadas.
