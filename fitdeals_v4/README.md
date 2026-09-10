# FitDeals V4

Versão corrigida do FitDeals V3, com foco em uma integração OAuth 2.0 do Mercado Livre mais segura e compatível com a configuração atual do DevCenter.

## O que mudou no V4

- OAuth 2.0 com `state` salvo no SQLite.
- PKCE com `S256` quando `ML_USE_PKCE=true`.
- `code_verifier` armazenado no servidor durante o fluxo OAuth.
- Access token e refresh token armazenados localmente no SQLite.
- Renovação automática do access token quando estiver próximo de expirar.
- `ML_REDIRECT_URI` configurável.
- O código não exige que Client Secret, access token ou refresh token sejam colocados no frontend.
- Consulta de preços usando `/items/{ITEM_ID}/prices`.
- Coleta automática em segundo plano.
- Painel, ranking, histórico e geração de mensagem.
- O sistema NÃO inventa cupom e NÃO automatiza WhatsApp Web.

## 1. Instalação no Windows

Abra o CMD dentro da pasta do projeto:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Edite `.env`.

Depois:

```bat
python -m uvicorn app.main:app --reload
```

Abra:

```text
http://127.0.0.1:8000
```

## 2. Configuração do Mercado Livre

No DevCenter, crie sua aplicação e copie o Client ID e Client Secret para o `.env`.

ATENÇÃO: a documentação atual do Mercado Livre exige HTTPS no Redirect URI da aplicação. Portanto, para rodar o FitDeals localmente e ainda assim fazer OAuth, use um túnel HTTPS ou hospede o FitDeals em um domínio HTTPS.

Exemplo:

```env
ML_CLIENT_ID=SEU_CLIENT_ID
ML_CLIENT_SECRET=SEU_CLIENT_SECRET
ML_REDIRECT_URI=https://SEU-ENDERECO-HTTPS/auth/mercadolivre/callback
ML_USE_PKCE=true
```

O valor de `ML_REDIRECT_URI` precisa ser exatamente o mesmo que estiver cadastrado no DevCenter.

## 3. Opção simples para testar localmente

Você pode usar um túnel HTTPS, como Cloudflare Tunnel ou ngrok, apontando para:

```text
http://127.0.0.1:8000
```

Se o túnel fornecer, por exemplo:

```text
https://abc123.exemplo-tunel.com
```

cadastre no Mercado Livre:

```text
https://abc123.exemplo-tunel.com
```

e coloque no `.env`:

```env
ML_REDIRECT_URI=https://abc123.exemplo-tunel.com/auth/mercadolivre/callback
```

Não acrescente parâmetros como `?teste=1`.

## 4. PKCE

Se você marcar PKCE no DevCenter, mantenha:

```env
ML_USE_PKCE=true
```

O V4 envia `code_challenge` no início e `code_verifier` na troca do código pelo token.

Se a aplicação não tiver PKCE habilitado, use:

```env
ML_USE_PKCE=false
```

## 5. Chave do painel

No `.env`:

```env
ADMIN_PASSWORD=uma-senha-sua
```

Na tela inicial do FitDeals, digite exatamente essa senha.

## 6. Afiliados

O V4 separa `permalink` da `affiliate_url`.

Ele NÃO inventa parâmetros de afiliado. Para usar uma URL de afiliado, alimente `affiliate_url` com uma URL gerada pelo mecanismo oficialmente permitido pelo programa de afiliados que você utiliza.

OAuth da API do Mercado Livre não significa, por si só, que a API vai transformar qualquer permalink em link de afiliado.

## 7. Cupons

O V4 só coloca cupom quando um código real é fornecido. Ele não cria códigos falsos nem tenta adivinhar promoções.

A criação/gestão de campanhas promocionais depende das permissões e do tipo de conta/recurso habilitado no Mercado Livre.

## 8. WhatsApp

Não use automação de WhatsApp Web com sessão pessoal, QR ou scraping.

O V4 gera e copia a mensagem para publicação manual. Uma futura integração automática deve usar um canal oficialmente compatível com o tipo de destinatário desejado e respeitar as políticas da plataforma.

## 9. Segurança

Nunca publique:

- `ML_CLIENT_SECRET`
- `access_token`
- `refresh_token`
- sua senha do painel

O `.env` deve permanecer apenas na sua máquina/servidor.

## 10. Estrutura

```text
fitdeals_v4/
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ db.py
│  ├─ main.py
│  ├─ mercadolivre.py
│  ├─ messages.py
│  ├─ oauth.py
│  └─ scheduler.py
├─ static/
│  └─ index.html
├─ .env.example
├─ README.md
└─ requirements.txt
```
