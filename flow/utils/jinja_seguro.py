# flow/utils/jinja_seguro.py
# Sandboxed and HARDENED Jinja environment, shared by every place that renders
# user-supplied expressions (expression_service, jinja_branch,
# field_transformer).
#
# Jinja's SandboxedEnvironment blocks underscore attributes and callables
# marked `unsafe`/`alters_data`, but lets through ANY public method of the
# context objects. Previous nodes' outputs enter the context as live
# GeoDataFrame/DataFrame/ndarray objects, and these expose I/O methods that write
# files — `to_file`, `to_csv(path)`, `to_parquet`, `tofile`, etc. Arbitrary
# writes in the executor process (which holds the machine's mTLS cert and the
# already-decrypted credentials) are a precursor to code execution.
#
# This module closes that on two fronts:
#   1) is_safe_attribute refuses ACCESS to a set of names that either write
#      files by nature, or are handles to a module/dangerous callable.
#   2) call() refuses the CALL of writers that only write when given a
#      destination (to_csv/to_json/...): without an argument they return a string
#      (legitimate use); with a path/buffer, they write — and then the call is blocked.

import os as _os
from jinja2.sandbox import SandboxedEnvironment, SecurityError

# Write files/state by nature, or give access to modules/execution. Access to
# the attribute itself is already denied — it never even gets called.
_ALWAYS_BLOCKED_ATTRS = frozenset({
    # pandas/geopandas/numpy/xarray: escrita em disco/banco
    "to_file", "to_pickle", "to_parquet", "to_feather", "to_hdf", "to_excel",
    "to_orc", "to_stata", "to_sql", "to_gbq", "to_netcdf", "to_zarr", "tofile",
    "savefig", "save", "savez", "savez_compressed", "savetxt", "dump",
    "write", "writelines", "writerow", "writerows",
    # module handles and dangerous callables (same class as code_sandbox)
    "os", "sys", "subprocess", "importlib", "socket", "ssl", "ctypes",
    "system", "popen", "environ", "getattr", "setattr", "delattr",
    "open", "fdopen", "remove", "unlink", "rmdir", "mkdir", "makedirs",
    "rename", "replace", "chmod", "chown", "spawn", "fork",
    "check_output", "check_call", "getoutput", "Popen", "run", "call",
    "eval", "exec", "compile", "import_module", "load_module",
})

# Return a string when called without a destination; write when given a path
# or buffer. Only the call WITH a destination is blocked.
_WRITERS_WITH_DESTINATION = frozenset({
    "to_csv", "to_json", "to_html", "to_xml", "to_string", "to_markdown",
    "to_latex",
})
# Argument names that designate the write destination in these methods.
_DESTINATION_KWARGS = (
    "path_or_buf", "buf", "path", "fname", "excel_writer",
    "filepath_or_buffer", "filename",
)


def _names_destination(args, kwargs) -> bool:
    """True if the call targets a write path/buffer."""
    alvo = args[0] if args else None
    for k in _DESTINATION_KWARGS:
        if kwargs.get(k) is not None:
            alvo = kwargs[k]
            break
    if alvo is None:
        return False
    return isinstance(alvo, (str, bytes, _os.PathLike)) or hasattr(alvo, "write")


class _HardenedSandboxEnvironment(SandboxedEnvironment):
    def is_safe_attribute(self, obj, attr, value):
        if attr in _ALWAYS_BLOCKED_ATTRS:
            return False
        return super().is_safe_attribute(obj, attr, value)

    def call(__self, __context, __obj, *args, **kwargs):  # noqa: N805
        nome = getattr(__obj, "__name__", "")
        if nome in _ALWAYS_BLOCKED_ATTRS:
            raise SecurityError(f"chamada a '{nome}' nao e permitida no sandbox")
        if nome in _WRITERS_WITH_DESTINATION and _names_destination(args, kwargs):
            raise SecurityError(
                f"'{nome}' com destino de arquivo nao e permitido no sandbox"
            )
        return super().call(__context, __obj, *args, **kwargs)


def create_sandbox_environment(**kwargs) -> SandboxedEnvironment:
    """Creates GISFlow's sandboxed and hardened Jinja environment.

    Accepts the same kwargs as `SandboxedEnvironment` (e.g. `undefined`).
    """
    return _HardenedSandboxEnvironment(**kwargs)
