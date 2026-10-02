# Bootstrap mTLS — step-ca interno

Roteiro one-time para preparar a CA interna (`step-ca`) que assina o cert
TLS do host dos executores (`AGENTS_HOST`, no `.env`) e os certs mTLS dos
executores enrolados.

Aplica-se a um host de produção limpo, ou ao recriar a CA do zero. **Não
rodar contra um cluster com executores já em produção** — apaga a CA antiga e
invalida todos os certs emitidos.

## Caminho rápido (recomendado)

Os passos 1 a 8 deste documento cabem nestes comandos, os de 1, 2 e 4 a 6
nos scripts. Em um host limpo:

```bash
make bootstrap            # cria volume, secrets/, .env
make up-prod              # sobe step-ca + demais serviços
docker compose exec api-prod alembic upgrade head  # o schema, antes de recriar a API
make bootstrap-stepca     # fingerprint, intermediate, prazo dos certs e cert do AGENTS_HOST
docker compose --profile prod up -d api-prod      # recria a API: só assim ela lê o .env novo
docker compose --profile prod restart traefik     # carrega os certificados
make backup-stepca        # backup imediato (faça antes que algo dê errado)
```

Os passos manuais abaixo permanecem como referência para debugging e
para a [recuperação de desastres](#recuperação-de-desastres), que não tem script.

## Pré-requisitos

- Docker com o plugin Compose v2 (`docker compose`) já instalados.
- Acesso ao host (`ssh`) e permissão para criar volumes.
- O DNS do `AGENTS_HOST` apontando **direto** para o IP do host, sem CDN na
  frente (na Cloudflare, *DNS-only*, nunca *proxied*). Um CDN termina o TLS e
  descarta o certificado do cliente, e o mTLS quebra.

## 1. Volume externo da CA

A chave privada da CA mora em `step-ca-data`. O volume é declarado como
`external: true` em [docker-compose.yml](../docker-compose.yml) para
sobreviver a um `docker compose down -v` acidental.

```bash
docker volume create step-ca-data
```

## 2. Senha do provisioner

`step-ca` precisa de uma senha para criptografar a chave privada do
provisioner JWK. Gere e persista uma forte:

```bash
mkdir -p secrets
openssl rand -base64 48 > secrets/stepca_password.txt
chmod 600 secrets/stepca_password.txt
sudo chown 1000:1000 secrets/stepca_password.txt   # o usuário step do container
```

A step-ca roda como o usuário `step` (UID 1000), e o compose monta o arquivo
com o dono e o modo do host: com outro dono e modo 600, ela não o lê e nunca
fica healthy. O `make bootstrap` faz o `chown` quando roda como root, e avisa
quando não pode.

A senha também deve ir no `.env` como `STEPCA_PROVISIONER_PASSWORD` para
o backend conseguir decifrar a chave do provisioner ao gerar OTTs.

## 3. Inicializar step-ca

A imagem `smallstep/step-ca` faz `init` automático na primeira subida,
usando as envs já definidas no compose (`DOCKER_STEPCA_INIT_*`).

```bash
docker compose --profile prod up -d step-ca
docker compose --profile prod logs -f step-ca
```

Aguarde a linha `serving HTTPS on :9000`.

Na primeira subida, a imagem imprime no log a senha administrativa da CA (a
mesma do provisioner). Não compartilhe esse log.

## 4. Capturar fingerprint do root cert

```bash
docker compose --profile prod exec step-ca \
    step certificate fingerprint /home/step/certs/root_ca.crt
```

Cole o valor no `.env` como `STEPCA_ROOT_FINGERPRINT=...`.

`GET /executores/install` injeta esse valor no script servido, como default de
`ATLANS_CA_SHA256`. Ele é verificado em dois momentos distintos:

1. **Na instalação**, pelo próprio `install.sh`: o root cert recém-baixado é
   conferido contra o fingerprint e a instalação **aborta** se não bater. É esta
   a verificação que impede a CA errada de entrar.
2. **A cada boot do executor**, por `executor/_ca_bootstrap.py` — tanto quando
   ele baixa o bundle quanto quando reusa o `atlans-root.crt` que já está no
   volume. Para isso o instalador grava `ATLANS_CA_SHA256` no `executor/.env`,
   de onde o serviço de longa duração o lê.

   A verificação no caminho de *reuso* é o que fecha o buraco de trocar o
   arquivo no volume e reiniciar: sem ela o pin valia uma única vez, no primeiro
   boot que baixou o bundle.

   Em ambos os lados a regra é **todos os certificados do arquivo têm de estar
   entre os pinados** — não basta um deles casar. O arquivo inteiro é
   concatenado às CAs públicas e vira o trust store do processo, então uma CA
   *acrescentada* ao bundle seria tão confiável quanto o root legítimo.

### Rotação de CA

`ATLANS_CA_SHA256` aceita **vários fingerprints separados por vírgula**. É o que
torna a rotação possível sem desligar o pinning: durante a sobreposição o bundle
legitimamente carrega o root antigo e o novo, e ambos precisam estar na lista.

```
ATLANS_CA_SHA256=<fp_antigo>,<fp_novo>
```

Depois que todos os executores estiverem no root novo, remova o antigo da lista.

O container efêmero de *enrollment* é a exceção, e por um motivo concreto: ele
recebe `SSL_CERT_FILE` apontando para o cert já verificado no passo 1, e
`bootstrap_ca()` retorna cedo quando essa variável existe, sem chegar a ler o
pin. Naquele passo a verificação já aconteceu, no shell.

Sem a variável configurada o download do `ca-bundle` continua funcionando, mas
é *trust on first use*: o instalador avisa que não verificou nada. Quem
conseguisse responder no lugar do servidor entregaria a própria CA. Configure
em produção.

O operador pode sobrescrever exportando `ATLANS_CA_SHA256` antes de rodar o
instalador — útil quando o fingerprint é transportado por outro canal.
Aceita hex puro (formato do `step certificate fingerprint`) ou com `:`
(formato do `openssl x509 -fingerprint`), em maiúsculas ou minúsculas.

## 5. Copiar intermediate para o Traefik

O Traefik valida o client cert do executor contra o intermediate da CA
interna. Extraia e coloque no caminho montado no compose (o volume
`traefik/atlans-ca` do serviço `traefik`, no [docker-compose.yml](../docker-compose.yml)):

```bash
mkdir -p traefik/atlans-ca
docker compose --profile prod exec step-ca \
    cat /home/step/certs/intermediate_ca.crt \
    > traefik/atlans-ca/intermediate.crt
chmod 644 traefik/atlans-ca/intermediate.crt
```

## 6. Gerar o cert TLS do host dos executores (`AGENTS_HOST`)

O Traefik **não** tira um cert do Let's Encrypt para o `AGENTS_HOST`: o host
serve o handshake com certificado de cliente e fica fora do CDN. A step-ca
emite o cert dele.

> Este passo é automatizado por `make bootstrap-stepca` (que emite o cert com
> `--provisioner-password-file`/`--force` e apaga a chave do volume depois de
> copiá-la). Os comandos abaixo são a referência manual.

A step-ca nasce com teto de 24 h por certificado, e este pede um ano (as
matrículas dos executores pedem `EXECUTOR_CERT_TTL_DAYS`, 90 dias por padrão).
Antes de emitir, suba o teto do provisioner e reinicie a step-ca, que só lê o
`ca.json` novo ao reiniciar:

```bash
docker compose --profile prod exec step-ca \
    step ca provisioner update atlans-app --x509-max-dur=8760h --x509-default-dur=2160h
docker compose --profile prod restart step-ca
```

Sem isso, a CA recusa: «requested duration of 8760h1m0s is more than the
authorized maximum certificate duration of 24h1m0s».

```bash
AGENTS_HOST=$(grep -E '^AGENTS_HOST=' .env | tail -1 | cut -d= -f2- | tr -d '"')

docker compose --profile prod exec step-ca \
    step ca certificate "$AGENTS_HOST" \
        /home/step/agents.crt \
        /home/step/agents.key \
        --provisioner atlans-app \
        --provisioner-password-file /run/secrets/stepca_password \
        --not-after 8760h \
        --force

docker compose --profile prod exec step-ca \
    cat /home/step/agents.crt > traefik/atlans-ca/agents.crt
docker compose --profile prod exec step-ca \
    cat /home/step/agents.key > traefik/atlans-ca/agents.key
chmod 600 traefik/atlans-ca/agents.key
chmod 644 traefik/atlans-ca/agents.crt

# Apague a chave do volume da step-ca apos copiar (o make bootstrap-stepca ja faz isso):
docker compose --profile prod exec step-ca \
    sh -c 'rm -f /home/step/agents.crt /home/step/agents.key'
```

Renovar em ~11 meses (ou automatizar com `step ca renew --daemon`).

## 7. Recriar a API e reiniciar o Traefik

```bash
docker compose --profile prod up -d api-prod      # o container só lê o .env ao ser criado
docker compose --profile prod restart traefik     # o Traefik só lê os certificados ao subir
```

Smoke test:

```bash
curl --cacert traefik/atlans-ca/intermediate.crt \
     "https://$AGENTS_HOST/executores/ca-bundle"
```

Deve retornar o PEM do root da CA interna.

## 8. Backup periódico do volume

A perda do volume `step-ca-data` é catastrófica — todos os executores
enrolados precisam de novo OTP + enroll.

> Prefira `make backup-stepca`: grava em `backups/step-ca-YYYY-MM-DD-HHMM.tar.gz`
> e mantém os 14 backups mais recentes. O bloco abaixo é o equivalente manual
> (nome sem hora, sem retenção automática) — rode via cron diário:

```bash
docker run --rm \
    -v step-ca-data:/data \
    -v "$(pwd)/backups:/backup" \
    alpine tar czf /backup/step-ca-$(date +%F).tar.gz -C /data .
```

Guarde os tarballs fora do host (S3 com KMS, etc.).

## 9. Onboarding de um novo executor

Após o bootstrap, qualquer admin pode:

1. Criar o executor na UI (gera OTP, single-use, TTL 24h).
2. Compartilhar o comando `curl ... | bash` com o operador via canal
   efêmero.
3. O executor roda `install.sh`, faz `enroll` → step-ca emite cert mTLS →
   executor persiste em `EXECUTOR_CERT_DIR/cert.pem`.

Renovação automática (`executor/renewal.py`) acontece sozinha próximo do
vencimento, atomic swap dos arquivos.

## Recuperação de desastres

Se `step-ca-data` for perdido:

1. Restaurar o backup mais recente, com a step-ca e a API fora do ar (as
   duas montam o volume):
   ```bash
   docker compose --profile prod rm -sf step-ca api-prod
   docker run --rm -v step-ca-data:/data -v "$(pwd)/backups:/backup" \
       alpine tar xzf /backup/step-ca-YYYY-MM-DD.tar.gz -C /data
   ```
2. Subir `step-ca` e `api-prod`, e reiniciar o `traefik`.
3. Confirmar fingerprint não mudou (mesmo backup → mesma CA). Caso
   tenha mudado, atualizar `.env` (`STEPCA_ROOT_FINGERPRINT`) e
   informar a todos os executores para reenrolar (admin gera OTPs novos).
