# flow/utils/json_saida.py
"""The `default` of the JSON the executor sends to the server.

One function for the two places that need it: the WebSocket serializer
(`executor/connection.py`), which carries every result to the server, and
the pin (`flow/executor/pin.py`), which converts the values of
`__pin_extra__` itself so that the ref it builds is the one the next pinned
run receives. Two copies would drift, and then a pinned run would deliver,
for a date or a numpy number, something other than what the run delivered.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional, Set


def json_default(obj: Any, como_texto: Optional[Set[str]] = None) -> Any:
    """JSON form of what the standard `json` does not know.

    Dates become ISO text, numpy numbers and arrays become Python ones, `pd.NA`
    becomes null. What has no JSON form becomes text — a DataFrame only as its
    shape, never in full — and, when `como_texto` is given, its type name goes
    into it, so the caller can say which values lost their type.
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    try:
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
    except ImportError:
        pass
    try:
        import pandas as pd
        # pandas.Timestamp, in case it is not a datetime subclass here.
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        if isinstance(obj, pd.NA.__class__):
            return None
    except ImportError:
        pd = None
    # From here on there is no JSON form: whoever reads it gets text.
    if como_texto is not None:
        como_texto.add(type(obj).__name__)
    if pd is not None and isinstance(obj, pd.DataFrame):
        return f"<DataFrame {obj.shape[0]}x{obj.shape[1]}>"
    # Caps long text so one value does not become a giant payload.
    texto = str(obj)
    if len(texto) > 500:
        return texto[:500] + "...[truncated]"
    return texto
