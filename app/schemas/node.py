from pydantic import BaseModel, Field
from typing import Any, List, Optional


class NodePort(BaseModel):
    """A node's named input port. `type` is the data type it accepts
    (TIPOS_DE_CAMPO from the contract) — connection validation in the canvas
    gesture compares it with the type emitted by the source."""
    name: str
    type: Optional[str] = None
    description: Optional[str] = None


class NodeOutputField(BaseModel):
    """Output field declared in `outputs` — the single, typed source of a node's
    output contract. `port=True` marks the fields that have their own
    connection point on the canvas (2+ of them ⇒ named handles)."""
    name: str
    type: Optional[str] = None
    description: Optional[str] = None
    port: bool = False


class SelectOption(BaseModel):
    """Option for properties of type 'select'."""
    value: str
    label: str


class NodeProperty(BaseModel):
    """
    Represents a configurable property of a node,
    extracted from the class's description() method.
    """
    name: str
    label: Optional[str] = None
    type: Optional[str] = None
    default: Optional[Any] = None
    description: Optional[str] = None
    # Filters compatible credentials when type == "credential"
    credential_types: Optional[List[str]] = None
    # Extensions accepted when type == "drive"
    drive_extensions: Optional[List[str]] = None
    # Field that expects a COLUMN NAME of the incoming data. The editor suggests
    # the names seen in the last run — without this, the only way to find out
    # the column is to run the workflow and look at the result.
    # Value: name of the input port the data comes from, or "*" for all.
    suggest_columns: Optional[str] = None
    # Options for type == "select"
    options: Optional[List[SelectOption]] = None
    # Declarative conditional visibility: a {field, in:[...]} rule or a list (AND).
    # Passed opaquely to the frontend (node-config-form evaluates it). Any avoids
    # modeling the `in` key (a reserved word in Python).
    visibleWhen: Optional[Any] = None
    # execute() refuses the empty field — the form marks the label (asterisk).
    # The HARD validation stays in the backend: this is signaling, not blocking.
    required: bool = False
    # Example of the expected format, shown in the empty input.
    placeholder: Optional[str] = None


class NodeDefinition(BaseModel):
    """
    Represents a node registered in NODE_REGISTRY,
    including name, alias, description, type, list of properties and output structure.
    """
    name: str
    alias: Optional[str] = Field(None, description="Nome alternativo do nó")
    description: Optional[str] = Field(None, description="Descrição do nó")
    type: Optional[str] = Field(None, description="Categoria ou grupo do nó")
    properties: List[NodeProperty] = []
    outputs: Optional[List[NodeOutputField]] = None
    inputs: Optional[List[NodePort]] = None
    # The inputs are declared by the USER, in the `ports` property, and not
    # fixed here. The editor derives the connection points from that list
    # instead of `inputs` — see `portasDeEntrada` in
    # web/app/components/workflow/index.tsx.
    dynamic_inputs: bool = Field(False, description="As entradas vêm da propriedade `ports` do nó")
    # The outputs come from `output_vars`, not from `outputs`. Without this the
    # editor always showed the output declared in the catalog — "result" for
    # the Python Script — even after the user had renamed the variables.
    dynamic_output: bool = Field(False, description="As saídas vêm da propriedade `output_vars` do nó")
    # The OUTPUTS come from the `ports` property — each port is its own output
    # connection point (SubWorkflowInput exposes the sub-workflow's input keys).
    # Without passing this flag through the catalog, the editor does not derive
    # per-port outputs, the key selector on the edge disappears and the trigger
    # falls back to spreading — see `portasDeSaida` / `getCandidateKeys` in
    # web/app/components/workflow.
    outputs_from_ports: bool = Field(False, description="As saídas vêm da propriedade `ports` do nó")
    requires_credential: bool = Field(False, description="Se True, o nó exige uma credencial para executar")
    # The kind of external source the node reads (today only "wfs"). It is what
    # links the node to the source catalog: `search_sources(kind=...)`, the
    # validation's `unknown_source` warning and the `describe_node` hint.
    # Nothing changes in the editor.
    source_kind: Optional[str] = Field(None, description="Tipo de fonte externa que o nó lê (ex.: wfs)")
    # BRANCH node (Conditional, JinjaBranch, ChangeDetector): the canvas output
    # points are true/false — they route execution — not the fields above.
    branches: bool = Field(False, description="O nó roteia por ramos true/false")
