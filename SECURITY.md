# Segurança

## Como reportar uma vulnerabilidade

Não abra uma issue pública. Use o reporte privado do GitHub: na aba
**Security** do repositório oficial, **Report a vulnerability**. Só os
mantenedores leem.

Se o botão não aparecer (o reporte privado está desligado), abra uma issue
pedindo um contato privado para um problema de segurança, sem nenhum detalhe
dele. A resposta traz o canal.

Ajuda muito trazer:

- o que a falha permite (ler dados de outra conta, executar código no
  servidor ou no executor, derrubar o serviço…);
- como reproduzir, com a versão ou o commit;
- se ela depende de alguma configuração (variáveis do `.env`, um executor
  matriculado, um nó específico).

A resposta chega pelo mesmo canal. Depois da correção publicada, o aviso de
segurança do repositório conta o que foi e dá o crédito a quem reportou, se a
pessoa quiser.

## Versões cobertas

Só a versão mais recente (a última tag `vX.Y.Z` do repositório oficial)
recebe correção de segurança. Numa versão anterior, a correção é atualizar.

## O que cada instalação cuida

O Atlans é instalado por quem o usa. A correção chega pelo repositório; aplicá-la
é de cada instalação: atualizar o código e as imagens, e rodar as migrações
quando houver ([docs/operations.md](docs/operations.md)).
