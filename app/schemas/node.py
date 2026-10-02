from pydantic import BaseModel, Field
from typing import Any, List, Optional


class NodePort(BaseModel):
    """Porta de entrada nomeada de um nó. `type` é o tipo de dado que ela
    aceita (TIPOS_DE_CAMPO do contrato) — a validação de conexão no gesto do
    canvas compara com o tipo emitido pela origem."""
    name: str
    type: Optional[str] = None
    description: Optional[str] = None


class NodeOutputField(BaseModel):
    """Campo de saída declarado em `outputs` — a fonte única, tipada, do
    contrato de saída de um nó. `port=True` marca os campos que têm ponto de
    conexão próprio no canvas (2+ deles ⇒ handles nomeados)."""
    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    port: bool = False


class SelectOption(BaseModel):
    """Opção para propriedades do tipo 'select'."""
    value: str
    label: str


class NodeProperty(BaseModel):
    """
    Representa uma propriedade configurável de um node,
    extraída do método description() da classe.
    """
    name: str
    label: Optional[str] = None
    type: Optional[str] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    # Filtra credenciais compatíveis quando type == "credential"
    credential_types: Optional[List[str]] = None
    # Extensões aceitas quando type == "drive"
    drive_extensions: Optional[List[str]] = None
    # Campo que espera NOME DE COLUNA do dado que chega. O editor sugere os
    # nomes vistos na ultima execucao — sem isto, a unica forma de descobrir a
    # coluna e executar o fluxo e olhar o resultado.
    # Valor: nome da porta de entrada de onde vem o dado, ou "*" para todas.
    suggest_columns: Optional[str] = None
    # Opções para type == "select"
    options: Optional[List[SelectOption]] = None
    # Visibilidade condicional declarativa: regra {field, in:[...]} ou lista (AND).
    # Passa opaca para o frontend (node-config-form avalia). Any evita modelar a
    # chave `in` (palavra reservada em Python).
    visibleWhen: Optional[Any] = None
    # O execute() recusa o campo vazio — o form marca o rótulo (asterisco).
    # A validação DURA continua no backend: aqui é sinalização, não bloqueio.
    required: bool = False
    # Exemplo do formato esperado, exibido no input vazio.
    placeholder: Optional[str] = None


class NodeDefinition(BaseModel):
    """
    Representa um node registrado no NODE_REGISTRY,
    incluindo nome, alias, descrição, tipo, lista de properties e estrutura de saída.
    """
    name: str
    alias: Optional[str] = Field(None, description="Nome alternativo do nó")
    description: Optional[str] = Field(None, description="Descrição do nó")
    type: Optional[str] = Field(None, description="Categoria ou grupo do nó")
    properties: List[NodeProperty] = []
    outputs: Optional[List[NodeOutputField]] = None
    inputs: Optional[List[NodePort]] = None
    # As entradas são declaradas pelo USUÁRIO, na propriedade `ports`, e não
    # fixas aqui. O editor deriva os pontos de conexão dessa lista em vez de
    # `inputs` — ver `portasDeEntrada` em web/app/components/workflow/index.tsx.
    dynamic_inputs: bool = Field(False, description="As entradas vêm da propriedade `ports` do nó")
    # As saídas vêm de `output_vars`, e não de `outputs`. Sem isto o editor
    # mostrava sempre a saída declarada no catálogo — "result" para o Script
    # Python — mesmo depois de o usuário ter renomeado as variáveis.
    dynamic_output: bool = Field(False, description="As saídas vêm da propriedade `output_vars` do nó")
    # As SAÍDAS vêm da propriedade `ports` — cada porta é um ponto de conexão de
    # saída próprio (o SubWorkflowInput expõe as chaves de entrada do sub-fluxo).
    # Sem passar esta flag pelo catálogo, o editor não deriva as saídas por porta,
    # o seletor de chave na aresta some e o trigger volta ao espalhamento — ver
    # `portasDeSaida` / `getCandidateKeys` em web/app/components/workflow.
    outputs_from_ports: bool = Field(False, description="As saídas vêm da propriedade `ports` do nó")
    requires_credential: bool = Field(False, description="Se True, o nó exige uma credencial para executar")
    # O tipo de fonte externa que o nó lê (hoje só "wfs"). É o que liga o nó ao
    # catálogo de fontes: `search_sources(kind=...)`, o aviso `unknown_source` da
    # validação e a dica de `describe_node`. Nada muda no editor.
    source_kind: Optional[str] = Field(None, description="Tipo de fonte externa que o nó lê (ex.: wfs)")
    # Nó de RAMO (Conditional, JinjaBranch, ChangeDetector): os pontos de saída
    # do canvas são true/false — roteiam a execução — e não os campos acima.
    branches: bool = Field(False, description="O nó roteia por ramos true/false")
