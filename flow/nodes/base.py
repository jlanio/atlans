# flow/nodes/base.py
# Define a classe abstrata que todos os nós devem estender
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseNode(ABC):
    @classmethod
    @abstractmethod
    def description(cls) -> Dict[str, Any]:
        """
        Metadados para descoberta e geração de interface. O contrato completo
        (vocabulários fechados e chaves aceitas) mora em flow/nodes/contrato.py
        e é VALIDADO na importação pelo @register_node — typo aqui morre no CI.

        {
            'name': 'NomeUnico',         # Chave de registro (sem espaços)
            'alias': 'Nome Legível',     # Nome exibido no editor
            'description': '...',        # Descrição do nó
            'type': 'action',            # CATEGORIA: trigger|action|spatial|datasource|output|control
            'properties': [              # Parâmetros configuráveis (widgets do form)
                {
                    'name': 'param1',       # Chave do parâmetro
                    'type': 'string',       # TIPOS_DE_PROPRIEDADE (contrato.py): string|number|
                                            #   integer|boolean|object|select|chips|credential|
                                            #   keyvalue|code|ports|drive|artifact|sql
                    'default': '',          # Valor padrão quando não informado
                    'description': '...',   # Descrição exibida no editor
                    # select exige 'options'; credential exige 'credential_types';
                    # opcionais: label, drive_extensions, visibleWhen, suggest_columns.
                },
            ],
            'outputs': [                 # Campos de SAÍDA — a fonte única, tipada:
                {                        #   as chaves do dict que execute() devolve
                    'name': 'output',
                    'type': 'geodataframe',  # TIPOS_DE_CAMPO: geodataframe|string|number|
                                             #   boolean|object|list|any
                    'description': '...',
                    # 'port': True em campos com ponto de conexão próprio no
                    # canvas (2+ deles = handles nomeados; nenhum = saída anônima).
                },
            ],
            # 'inputs': [{'name': 'layerA'}, ...]  # portas de entrada nomeadas (nós binários: get_pair)
            # 'branches': True       # nó de RAMO: handles true/false roteiam a execução
            # 'dynamic_inputs': True     # entradas vêm da propriedade `ports`
            # 'dynamic_output': True     # saídas vêm da propriedade `output_vars`
            # 'outputs_from_ports': True # saídas vêm da propriedade `ports` (SubWorkflowInput)
            # 'requires_credential': True / 'source_kind': 'wfs'
        }
        """
        raise NotImplementedError("Método description() precisa ser implementado.")

    def __init__(self, node_id: str, parameters: dict):
        """
        Construtor comum a todos os nós.
        :param node_id: identificador único do nó
        :param parameters: dicionário de parâmetros configurados pelo usuário
        """
        self.node_id = node_id
        self.parameters = parameters or {}
        # Injetados pelo executor — permitem publicação de eventos customizados no terminal
        self._publisher = None
        self._task_id: str | None = None
        self._debug_mode: bool = False
        self._workspace_id: str | None = None  # Isolamento multi-tenant
        self._workflow_hash: str | None = None  # Identifica o workflow para state cross-run
        # Context compartilhado com o executor (mesmo dict). Setado pelo
        # WorkflowExecutor no momento da instanciacao. Hoje carrega
        # _subflow_ancestors (usado por SubWorkflowNode para loop detection).
        self.context: Dict[str, Any] = {}

    async def setup(self) -> None:
        """Hook opcional chamado antes de execute(). Útil para preparar recursos."""

    async def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método principal que contém a lógica do nó.
        :param inputs: valores de entrada de nós anteriores mapeados por nome
        :return: valores de saída mapeados por nome

        IMPLEMENTE `execute_sync` SEMPRE QUE O NÓ FOR CPU-BOUND (pandas,
        geopandas, shapely, Jinja linha a linha). Só sobrescreva `execute` quando
        o nó realmente aguarda I/O assíncrono (asyncpg, httpx) — e, mesmo aí,
        mande o pós-processamento pesado para `asyncio.to_thread`.

        O motivo é arquitetural: no executor externo o engine roda no MESMO event
        loop que atende o WebSocket. Enquanto um `execute` bloqueia, heartbeat,
        capacity, node_events, resultados e o `cancel` do usuário deixam de ser
        agendados — passando de 90s o servidor fecha a sessão com 4408 e o run
        inteiro morre, junto com o dos OUTROS jobs do mesmo executor. Por isso o
        default aqui NÃO é "roda no loop": é despachar o corpo síncrono para o
        pool de threads dedicado (executor/main.py o instala como default).
        """
        return await asyncio.to_thread(self.execute_sync, inputs)

    def execute_sync(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Corpo SÍNCRONO do nó, executado numa thread do pool (ver `execute`).

        Pode bloquear à vontade — é justamente para isso que existe. O que não
        pode é tocar o event loop: publicação de evento (`self._publisher`) já é
        thread-safe via `call_soon_threadsafe`, e `self.log` também (logging é
        thread-safe), mas não crie tasks nem use `asyncio.get_running_loop()`
        daqui.
        """
        raise NotImplementedError(
            f"'{type(self).__name__}' precisa implementar 'execute_sync' (nó "
            "CPU-bound) ou sobrescrever 'execute' (nó de I/O assíncrono)."
        )

    async def teardown(self) -> None:
        """Hook opcional chamado após execute() (inclusive em caso de erro). Útil para limpar recursos."""

    # ── Validação de parâmetros ──────────────────────────────────────────────

    def validate(self) -> None:
        """
        Aplica defaults declarados em description()['properties'] aos parâmetros do nó.
        Chame self.validate() no início de execute() para garantir que todos os
        parâmetros obrigatórios têm valores e que os defaults são preenchidos.
        Substitui o padrão: props = self.description()['properties']; self.parameters = validate_node_parameters(...)
        """
        from flow.utils.parameter_validation import validate_node_parameters
        desc = self.description()
        props = desc.get("properties", [])
        self.parameters = validate_node_parameters(
            self.parameters, props, node_name=desc.get("name", type(self).__name__),
        )

    # ── Helpers de parâmetros ────────────────────────────────────────────────

    def get_param(self, name: str, default: Any = None) -> Any:
        """
        Retorna o valor do parâmetro configurado, com fallback para default.
        Substitui o uso direto de self.parameters.get() para evitar confusão
        com self.properties (que não existe nesta classe).
        """
        return self.parameters.get(name, default)

    def get_param_float(self, name: str, default: float = 0.0) -> float:
        """Retorna parâmetro convertido para float."""
        try:
            return float(self.parameters.get(name, default))
        except (TypeError, ValueError):
            raise ValueError(f"Parâmetro '{name}' deve ser numérico. Recebido: {self.parameters.get(name)!r}")

    def get_param_int(self, name: str, default: int = 0) -> int:
        """Retorna parâmetro convertido para int."""
        try:
            return int(float(self.parameters.get(name, default)))
        except (TypeError, ValueError):
            raise ValueError(f"Parâmetro '{name}' deve ser inteiro. Recebido: {self.parameters.get(name)!r}")

    def get_retry_params(self) -> tuple[int, float]:
        """Retorna (retry_count, retry_delay_s) configurados no nó (padrão: 0 retries, 5s de espera)."""
        return self.get_param_int("retry_count", 0), self.get_param_float("retry_delay_s", 5.0)

    def get_param_bool(self, name: str, default: bool = False) -> bool:
        """Retorna parâmetro convertido para bool (aceita True/False/'true'/'false')."""
        value = self.parameters.get(name, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "sim")
        return bool(value)

    # ── Helpers de inputs ────────────────────────────────────────────────────

    def get_input_gdf(self, inputs: Dict[str, Any], key: str):
        """
        Busca e valida um GeoDataFrame nos inputs.
        Lança ValueError com mensagem clara se não encontrado, não for GDF ou estiver vazio.
        """
        import geopandas as gpd
        value = inputs.get(key)
        if value is None:
            raise ValueError(f"Input '{key}' não encontrado. Inputs disponíveis: {list(inputs.keys())}")
        if not isinstance(value, gpd.GeoDataFrame):
            raise TypeError(f"Input '{key}' não é um GeoDataFrame (recebido: {type(value).__name__}).")
        if value.empty:
            raise ValueError(f"GeoDataFrame '{key}' está vazio.")
        return value

    def get_first_gdf(self, inputs: Dict[str, Any]):
        """
        Retorna o primeiro GeoDataFrame encontrado nos inputs.
        Útil quando o nó não exige uma chave específica.

        Havendo mais de um candidato a escolha é AMBÍGUA e depende da ordem das
        arestas na definition. O nó avisa no painel em vez de processar um e
        ignorar o outro em silêncio — o sintoma clássico é um filtro espacial
        que "funciona" com metade dos dados porque dois pais entregaram camadas
        e só a primeira foi lida.
        """
        import geopandas as gpd
        candidatos = [
            k for k, v in inputs.items()
            if isinstance(v, gpd.GeoDataFrame) and not v.empty
        ]
        # Duas chaves apontando para o MESMO objeto não são ambiguidade: é o que
        # os nós de bifurcação produzem, expondo o dado que passou por eles em
        # `result` além da chave que veio do pai. Comparar por identidade evita
        # o aviso alarmante sobre uma escolha que não existe — qualquer das duas
        # chaves devolve exatamente o mesmo GeoDataFrame.
        distintos = {id(inputs[k]) for k in candidatos}
        if len(distintos) > 1:
            self.log(
                f"Mais de uma camada chegou a este nó ({candidatos}); usando '{candidatos[0]}' "
                f"e ignorando as demais. Use as portas nomeadas do nó de origem para escolher."
            )
        if candidatos:
            return inputs[candidatos[0]]

        # A mensagem precisa dizer O QUE chegou. Nós como SaveToPostGIS aceitam
        # apenas GeoDataFrame, enquanto DataInput entrega GeoDataFrame, DataFrame,
        # dict, list ou bytes conforme a extensao do arquivo — sem o diagnostico
        # abaixo, ligar um CSV no PostGIS falhava com um texto que nao ajudava a
        # descobrir nem a chave nem o tipo recebido.
        recebido = {k: type(v).__name__ for k, v in inputs.items()}
        vazios = [
            k for k, v in inputs.items()
            if isinstance(v, gpd.GeoDataFrame) and v.empty
        ]
        detalhe = f" GeoDataFrame(s) vazio(s): {vazios}." if vazios else ""
        raise ValueError(
            f"Nenhum GeoDataFrame encontrado nos inputs. Recebido: {recebido}.{detalhe}"
        )

    def get_pair(
        self,
        inputs: Dict[str, Any],
        chave_a: str = "layerA",
        chave_b: str = "layerB",
        *,
        operacao: str = "operação",
        crs: str | None = "exigir_igual",
        tipos_suportados: bool = False,
        nomes: tuple[str, str] | None = None,
    ):
        """
        Busca as duas camadas de um nó binário (A, B) e aplica a política de CRS
        do nó. Devolve `(a, b)`. Antes cada nó reescrevia a busca e a checagem.

        crs:
          'exigir_igual' → recusa camadas com CRS diferentes; quem monta o fluxo
                           padroniza antes com um nó de reprojeção.
          'alinhar'      → exige CRS nas duas camadas. Quem reprojeta B para o CRS
                           de A é o nó, com `align_crs`, DENTRO da thread de
                           trabalho: to_crs é O(n) e não roda no event loop.
          None           → sem checagem: o nó trata o CRS por conta própria
                           (ex.: `para_crs_metrico`).
        tipos_suportados: recusa GeometryCollection/geometria nula nas duas.
        nomes: como cada camada aparece nas mensagens de CRS ausente
               (padrão: "camada '<chave>'").
        operacao: como a operação aparece nas mensagens de recusa.
        """
        from flow.utils.geo_helpers import (
            reject_unsupported_geom_types,
            require_crs,
            require_same_crs,
        )
        a = self.get_input_gdf(inputs, chave_a)
        b = self.get_input_gdf(inputs, chave_b)
        if crs == "exigir_igual":
            require_same_crs(a, b, operation=operacao)
        elif crs == "alinhar":
            nome_a, nome_b = nomes or (f"camada '{chave_a}'", f"camada '{chave_b}'")
            require_crs(a, name=nome_a)
            require_crs(b, name=nome_b)
        elif crs is not None:
            # Um typo aqui desligaria a checagem em silêncio.
            raise ValueError(f"Política de CRS desconhecida: {crs!r}.")
        if tipos_suportados:
            reject_unsupported_geom_types(a, b, operation=operacao)
        return a, b

    # ── Helpers de contexto de execução ─────────────────────────────────────

    def require_execution_context(self) -> tuple[str, str]:
        """
        Garante que o executor injetou `_workspace_id` e `_task_id`.
        Retorna `(workspace_id, task_id)`. Útil para nodes output que
        precisam isolar artefatos por workspace/run.
        """
        workspace_id = getattr(self, "_workspace_id", None)
        task_id = getattr(self, "_task_id", None)
        if not workspace_id:
            raise RuntimeError("workspace_id nao injetado pelo executor.")
        if not task_id:
            raise RuntimeError("task_id nao injetado pelo executor.")
        return workspace_id, task_id

    def derive_label(self, label_param: str, output_path_param: str = "") -> str:
        """
        Resolve o `label` do nó. Prioridade:
          1. label_param (se preenchido).
          2. basename do output_path sem extensão.
          3. ValueError se ambos vazios.
        Reduz o boilerplate repetido em nodes output (save_geojson, save_to_s3, etc).
        """
        import os
        label = (label_param or "").strip()
        if label:
            return label
        path = (output_path_param or "").strip()
        if path:
            return os.path.splitext(os.path.basename(path))[0]
        raise ValueError(
            "Parametro 'label' e obrigatorio quando 'output_path' nao esta preenchido."
        )

    # ── Helper de log ────────────────────────────────────────────────────────

    def log(self, message: str) -> None:
        """
        Loga uma mensagem informativa no contexto do nó.
        Conveniente para nós que não querem importar get_logger diretamente.
        """
        from flow.utils.logger import get_logger
        get_logger(f"node.{self.node_id}").info(message)

    # ── Proteção contra typo self.properties ────────────────────────────────

    @property
    def properties(self):
        raise AttributeError(
            f"'{type(self).__name__}' não possui 'properties'. "
            "Use 'self.parameters' ou 'self.get_param()' para acessar parâmetros configurados."
        )
