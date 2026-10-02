# flow/utils/jinja_seguro.py
# Ambiente Jinja sandboxado e ENDURECIDO, compartilhado por todos os pontos que
# renderizam expressao vinda do usuario (expression_service, jinja_branch,
# field_transformer).
#
# O SandboxedEnvironment do Jinja bloqueia atributos com sublinhado e chamaveis
# marcados como `unsafe`/`alters_data`, mas deixa passar QUALQUER metodo publico
# dos objetos do contexto. Os outputs dos nos anteriores entram no contexto como
# GeoDataFrame/DataFrame/ndarray vivos, e esses expoem metodos de I/O que gravam
# arquivo — `to_file`, `to_csv(path)`, `to_parquet`, `tofile`, etc. Escrita
# arbitraria no processo do executor (que guarda o cert mTLS da maquina e as
# credenciais ja descriptografadas) e precursor de execucao de codigo.
#
# Este modulo fecha isso em duas frentes:
#   1) is_safe_attribute recusa o ACESSO a um conjunto de nomes que ou gravam
#      arquivo por natureza, ou sao handle de modulo/chamavel perigoso.
#   2) call() recusa a CHAMADA dos escritores que so gravam quando recebem um
#      destino (to_csv/to_json/...): sem argumento devolvem string (uso legitimo);
#      com um caminho/buffer, gravam — e ai a chamada e barrada.

import os as _os
from jinja2.sandbox import SandboxedEnvironment, SecurityError

# Gravam arquivo/estado por natureza, ou dao acesso a modulo/execucao. O acesso
# ao proprio atributo ja e negado — nem chega a ser chamado.
_ATRIB_SEMPRE_BLOQUEADOS = frozenset({
    # pandas/geopandas/numpy/xarray: escrita em disco/banco
    "to_file", "to_pickle", "to_parquet", "to_feather", "to_hdf", "to_excel",
    "to_orc", "to_stata", "to_sql", "to_gbq", "to_netcdf", "to_zarr", "tofile",
    "savefig", "save", "savez", "savez_compressed", "savetxt", "dump",
    "write", "writelines", "writerow", "writerows",
    # handles de modulo e chamaveis perigosos (mesma classe do code_sandbox)
    "os", "sys", "subprocess", "importlib", "socket", "ssl", "ctypes",
    "system", "popen", "environ", "getattr", "setattr", "delattr",
    "open", "fdopen", "remove", "unlink", "rmdir", "mkdir", "makedirs",
    "rename", "replace", "chmod", "chown", "spawn", "fork",
    "check_output", "check_call", "getoutput", "Popen", "run", "call",
    "eval", "exec", "compile", "import_module", "load_module",
})

# Devolvem string quando chamados sem destino; gravam quando recebem um caminho
# ou buffer. So a chamada COM destino e bloqueada.
_ESCRITORES_COM_DESTINO = frozenset({
    "to_csv", "to_json", "to_html", "to_xml", "to_string", "to_markdown",
    "to_latex",
})
# Nomes de argumento que designam o destino de escrita nesses metodos.
_KWARGS_DE_DESTINO = (
    "path_or_buf", "buf", "path", "fname", "excel_writer",
    "filepath_or_buffer", "filename",
)


def _designa_destino(args, kwargs) -> bool:
    """True se a chamada aponta um caminho/buffer de escrita."""
    alvo = args[0] if args else None
    for k in _KWARGS_DE_DESTINO:
        if kwargs.get(k) is not None:
            alvo = kwargs[k]
            break
    if alvo is None:
        return False
    return isinstance(alvo, (str, bytes, _os.PathLike)) or hasattr(alvo, "write")


class _AmbienteSandboxEndurecido(SandboxedEnvironment):
    def is_safe_attribute(self, obj, attr, value):
        if attr in _ATRIB_SEMPRE_BLOQUEADOS:
            return False
        return super().is_safe_attribute(obj, attr, value)

    def call(__self, __context, __obj, *args, **kwargs):  # noqa: N805
        nome = getattr(__obj, "__name__", "")
        if nome in _ATRIB_SEMPRE_BLOQUEADOS:
            raise SecurityError(f"chamada a '{nome}' nao e permitida no sandbox")
        if nome in _ESCRITORES_COM_DESTINO and _designa_destino(args, kwargs):
            raise SecurityError(
                f"'{nome}' com destino de arquivo nao e permitido no sandbox"
            )
        return super().call(__context, __obj, *args, **kwargs)


def criar_ambiente_sandbox(**kwargs) -> SandboxedEnvironment:
    """Cria o ambiente Jinja sandboxado e endurecido do GISFlow.

    Aceita os mesmos kwargs de `SandboxedEnvironment` (ex.: `undefined`).
    """
    return _AmbienteSandboxEndurecido(**kwargs)
