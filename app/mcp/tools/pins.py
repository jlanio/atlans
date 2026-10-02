# app/mcp/tools/pins.py
"""
Pins: congelar a saída de um nó para a próxima execução reaproveitar.

É o que torna barato iterar num fluxo caro. Ajustar o nó final de um pipeline
que começa com uma consulta de quarenta segundos custa quarenta segundos por
tentativa; com a consulta fixada, custa o nó final. Um agente que edita fluxos
sem esta ferramenta paga o fluxo inteiro a cada rodada.

E, na direção contrária, um pin esquecido faz o fluxo devolver **dado velho sem
avisar ninguém** — a execução termina verde, com o resultado de ontem. Por isso
`list_pins` existe mesmo para quem nunca vai fixar nada: é a única maneira de
um agente descobrir que a resposta que ele está lendo foi congelada.

Três decisões moldam o módulo:

- **`pin_node_output` sempre manda `outputs={}`.** `{}` significa "fixe na
  próxima execução": o nó roda uma vez e o executor grava o cache. A tool não
  tem como fabricar um payload de saída legítimo — ela não viu os dados — e o
  campo é gravado sem filtro do outro lado, então deixá-lo aberto seria deixar
  um agente injetar conteúdo arbitrário no cache de execução de um fluxo de
  produção. O despacho coage qualquer outra coisa a `{}` de qualquer forma
  (`workflow_execution_service._safe_pinned_outputs`).
- **Nó de saída é recusado.** Fixar a saída de um nó que grava arquivo faz o
  executor reaproveitar o valor congelado e PULAR a gravação: o fluxo termina
  com sucesso e o arquivo não aparece. O pin fica lá parecendo estar ajudando.
  A regra vale para os dois transportes — a rota REST passou a recusar no mesmo
  diff, então não há caminho por onde o pin fantasma ainda entre.
- **`expired` é relato, não ação.** Quem honra o TTL é o executor, e ele
  deliberadamente NÃO zera a referência ao expirar (contrato fixado em
  `tests/unit/test_pin_ciclo_de_vida.py`). Uma tool que "limpasse pins
  vencidos" quebraria esse contrato; esta relata e deixa a decisão com quem lê.
"""
from __future__ import annotations

from typing import Any, Optional

from mcp.server.mcpserver import Context

from app.core.authorization.workflow_access import exigir_papel
from app.core.rbac import ROLE_EDITOR, ROLE_VIEWER
from app.mcp import infra
from app.mcp.erros import erro
from app.mcp.escopo import escopo_da_chamada, exigir_escopo
from app.mcp.resolucao import carregar_workflow
from app.mcp.saida import envelope
from app.mcp.tools.base import anotacoes, ferramenta
from app.services import pin_service

_MENSAGEM_PAPEL_LEITURA = "Requer papel 'viewer' ou superior neste workspace."
_MENSAGEM_PAPEL_ESCRITA = "Requer papel 'editor' ou superior neste workspace."


def _ids_dos_nos(definition: Any) -> set[str]:
    """Os `id` dos nós que a definition tem agora."""
    if not isinstance(definition, dict):
        return set()
    nos = definition.get("nodes")
    if not isinstance(nos, list):
        return set()
    return {str(no.get("id")) for no in nos if isinstance(no, dict) and no.get("id")}


# ── Leitura ──────────────────────────────────────────────────────────────────


@ferramenta
async def list_pins(ctx: Context, workflow_id: str) -> dict:
    """Os nós deste workflow com a saída congelada.

    Um pin faz a próxima execução reaproveitar a saída gravada em vez de
    recalcular o nó. Chame isto antes de concluir qualquer coisa sobre um
    resultado: se o nó que produziu o dado está pinado, o que a execução
    devolveu pode ser de dias atrás, e nada na resposta da execução diz isso.

    Cada item traz dois estados que não são a mesma coisa:

    - `cached: false` — o pin foi pedido e o cache ainda não existe. A próxima
      execução roda o nó normalmente e grava. É o estado logo depois de
      `pin_node_output`.
    - `cached: true` — o cache existe, e é ele que as execuções estão usando.

    `expired` diz se o prazo passou, e é informativo: o executor **não** apaga
    o cache ao expirar. `expired: null` significa que há uma data gravada e
    ela não pôde ser lida — não confunda com "não expira", que é
    `expires_at: null`.

    Pins de nós que já foram apagados da definition não aparecem aqui.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:read")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_VIEWER, _MENSAGEM_PAPEL_LEITURA)
        pins = pin_service.listar_pins(
            wf.pin_metadata,
            wf.pinned_outputs,
            node_ids_existentes=_ids_dos_nos(wf.definition),
        )
        id_do_fluxo = wf.id_hash

    return envelope({
        "workflow_id": id_do_fluxo,
        "items": pins,
        "total": len(pins),
        "cached_count": sum(1 for p in pins if p["cached"]),
    })


# ── Escrita ──────────────────────────────────────────────────────────────────


@ferramenta
async def pin_node_output(
    ctx: Context, workflow_id: str, node_id: str, ttl_hours: Optional[int] = None
) -> dict:
    """Congela a saída de um nó a partir da próxima execução.

    O nó roda uma vez mais e o resultado dele é gravado; da execução seguinte
    em diante, o fluxo reaproveita esse resultado em vez de recalcular. Serve
    para iterar na parte final de um fluxo caro sem repetir a parte cara.

    `ttl_hours` é de 1 a 8760 (um ano); omitido, o pin não expira. Quando o
    prazo passa o executor **não** apaga o cache sozinho — o prazo serve para
    `list_pins` avisar que aquele dado está velho, e desfixar é decisão de quem
    lê. Não passe `0`: ele é recusado, porque "zero horas de validade" e "sem
    validade" são pedidos opostos.

    Não dá para escolher QUAL valor congelar, de propósito: quem grava é a
    execução. E nós que produzem arquivo (saída, publicação de mapa, e-mail,
    resposta de webhook) são recusados — congelar a saída deles faria o
    executor pular a gravação, e o fluxo terminaria verde sem produzir nada.

    Depois de fixar, rode o fluxo uma vez para o cache existir: até lá
    `list_pins` mostra `cached: false` e nada é reaproveitado.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)
        id_do_fluxo = wf.id_hash
        try:
            resultado = await pin_service.fixar_saida(
                db, wf, node_id,
                # Sempre `{}`: ver o cabeçalho do módulo.
                outputs={},
                ttl_hours=ttl_hours,
                user_id=escopo.user_id,
                exigir_no_existente=True,
            )
        except pin_service.NoInexistenteError as exc:
            raise erro(
                "not_found",
                str(exc),
                "use get_workflow(workflow_id) para ver os ids dos nós",
            )
        except pin_service.PinEmNoDeSaidaError as exc:
            raise erro(
                "validation",
                str(exc),
                "fixe o nó que ALIMENTA a saída, não o de saída em si",
            )
        except ValueError as exc:
            # `_validar_ttl` — faixa ou tipo.
            raise erro("validation", str(exc), "ttl_hours de 1 a 8760, ou omitido")

    return envelope({
        "workflow_id": id_do_fluxo,
        "node_id": node_id,
        "pinned_at": resultado["pinned_at"],
        "expires_at": resultado["expires_at"],
        "ttl_hours": resultado["ttl_hours"],
        "total_pinned": resultado["total_pinned"],
        # O estado logo depois de fixar é SEMPRE este, e dizê-lo evita a
        # conclusão errada de que o pin já está valendo.
        "cached": False,
        "hint": (
            "o cache ainda não existe: rode o fluxo uma vez para o nó gravar a "
            "saída; até lá cada execução recalcula normalmente"
        ),
    })


@ferramenta
async def unpin_node_output(ctx: Context, workflow_id: str, node_id: str) -> dict:
    """Descongela a saída de um nó e apaga o cache dele.

    A partir da próxima execução o nó volta a rodar de verdade. Use isto
    quando o dado congelado ficou velho, quando o fluxo mudou de forma que o
    valor gravado não corresponde mais, ou ao terminar a rodada de edição que
    motivou o pin — deixar um pin para trás faz o fluxo devolver dado antigo
    sem nenhum sinal.

    `outcome` distingue os dois desfechos: `unpinned` (havia pin e ele saiu) e
    `not_pinned` (não havia nada). Nenhum dos dois é erro.

    Se o cache não puder ser apagado do armazenamento, o pin **mesmo assim**
    sai e a resposta traz `storage_warning`: o objeto que sobra é recolhido
    depois, e o que não pode acontecer é o fluxo continuar apontando para um
    cache que não existe mais.
    """
    escopo = escopo_da_chamada(ctx)
    exigir_escopo(escopo, "workflows:write")

    async with infra.sessao() as db:
        wf, papel = await carregar_workflow(db, escopo, workflow_id, decifrar=False)
        exigir_papel(papel, ROLE_EDITOR, _MENSAGEM_PAPEL_ESCRITA)
        id_do_fluxo = wf.id_hash
        resultado = await pin_service.desfixar_saida(db, wf, node_id)

    aviso = resultado.get("storage_warning")
    return envelope({
        "workflow_id": id_do_fluxo,
        "node_id": node_id,
        "outcome": resultado["outcome"],
        "total_pinned": resultado["total_pinned"],
        # `envelope` só omite chave NULA, então a inserção é condicional: um
        # `storage_warning: None` no topo faria o leitor procurar um problema
        # que não houve.
        **({"storage_warning": aviso} if aviso else {}),
    })


def registrar(server) -> None:
    """Registra as tools deste domínio."""
    server.tool(
        name="list_pins",
        title="Saídas congeladas",
        description=(
            "Os nós deste workflow com a saída congelada. Consulte antes de concluir "
            "qualquer coisa sobre um resultado: se o nó que produziu o dado está pinado, "
            "a execução devolveu cache, e nada na resposta dela diz isso."
        ),
        annotations=anotacoes("list_pins"),
    )(list_pins)

    server.tool(
        name="pin_node_output",
        title="Congelar a saída de um nó",
        description=(
            "Faz as próximas execuções reaproveitarem a saída de um nó em vez de "
            "recalculá-la — para iterar no fim de um fluxo caro sem repetir a parte cara. "
            "Nós que gravam arquivo são recusados: congelá-los faria o executor pular a "
            "gravação."
        ),
        annotations=anotacoes("pin_node_output"),
    )(pin_node_output)

    server.tool(
        name="unpin_node_output",
        title="Descongelar a saída de um nó",
        description=(
            "Remove o congelamento e apaga o cache: o nó volta a rodar de verdade na "
            "próxima execução. Responde outcome=not_pinned, sem erro, quando não havia pin."
        ),
        annotations=anotacoes("unpin_node_output"),
    )(unpin_node_output)
