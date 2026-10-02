# How data moves along edges

The executor decides what the child node receives with three cases, in this order:

| Edge | What the child node receives |
|---|---|
| with `from_key` | `{to_key ou from_key: pai["from_key"]}` (ou = or, pai = parent) |
| only `to_key` | `{to_key: primeiro valor do pai}` (the parent's first value) |
| with neither | ALL of the parent's outputs, with their original names |

`from_key` is the parent's OUTPUT key — the names come from the node's declared
ports (`describe_node` lists them in `outputs`). `to_key` is the name under
which the value arrives in the child's `inputs`.

## When to name

If the child accepts several distinct inputs (a `SpatialJoin` with layer A and
layer B, a `SubWorkflowOutput` with several ports), `to_key` is **mandatory**
— without it both edges spread and the second overwrites the first,
silently. If the child consumes only one piece of data, you can leave both blank.

## A nonexistent `from_key` does not bring down the run

In production the executor is tolerant on purpose: a `from_key` with no
match **omits** the port (an optional output or a skipped parent must not
bring down a legitimate workflow). The result is the worst kind of defect — the
workflow finishes green with the wrong data.

That is why the check is STATIC. `validate_workflow` compares each `from_key`
against the source's declared outputs and returns:

- `edge_from_key_unknown` (**error**): the `from_key` is not a declared output of the source
  node. Stale wiring — almost always an old port name.
- `edge_spread_ambiguous` (**warning**): an edge with neither `from_key` nor `to_key`
  leaving a node with several outputs. It works, but what reaches the child
  depends on the order of the parent's keys. Name it.

A source that declares no output at all produces no diagnostic: there is nothing to
compare against.

## Fork

An edge leaving a control node carries `condition: true` or
`condition: false`, and the executor only activates the ones that match the node's `branch`. The
losing branch is marked as skipped and does not execute.

```json
[
  { "source": "cond1", "target": "envia",   "condition": true,  "source_handle": "true"  },
  { "source": "cond1", "target": "arquiva", "condition": false, "source_handle": "false" }
]
```

`source_handle: "true"|"false"` goes along with it, and it is what the editor uses to anchor
the edge visually. Without it the edge disappears from the canvas on reopening — write
both.

Nodes that fork: `Conditional`, `JinjaBranch`, `ChangeDetector`. `Switch`
routes by named port (`from_key: "output_0"`), not by `condition`.

A fork edge does **not** carry `from_key`. The child receives the parent's whole
dict — the data under its original name, plus `branch`, `value` and `result`.

## Loose edge

An edge whose endpoint does not exist among the nodes is ignored by the executor without a
word; validation flags it as an `orphan_edge` warning. A node with no path from
a trigger stays out of the simulation and the run: `unreachable_node`. Both are
warnings, but they almost always mean wiring you thought you had done.
