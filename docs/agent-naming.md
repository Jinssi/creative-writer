# Agent naming convention

All agents that belong to the **Creative Writer** workload carry the **`-CW`**
suffix. This makes agents from the same workload instantly identifiable in the
shared Foundry project, in distributed traces (App Insights), and in monitoring —
even though the project is shared with other apps.

## Rule

```
<role>-CW
```

- `<role>` is a short, lowercase, hyphenated description of what the agent does.
- `-CW` is the fixed workload suffix (Creative Writer).

The suffix is applied centrally in [`agent_framework_client.py`](../src/api/agent_framework_client.py):
`build_agent(name, ...)` calls `cw_name(name)`, which appends `-CW` unless it is
already present. Use `cw_name()` for any agent created outside `build_agent`
(e.g. an ephemeral Foundry Agent Service agent).

## Current agents

| Role | Agent name | Purpose |
| --- | --- | --- |
| Researcher | `researcher-CW` | Plans research and calls the web-grounding tool |
| Researcher (grounding) | `researcher-bing-CW` | Ephemeral Foundry agent that runs Bing grounding |
| Product / references | `product-marketing-CW` | Retrieves optional reference material |
| Writer | `writer-CW` | Drafts the article from the brief |
| Editor | `editor-CW` | Reviews the draft and drives the feedback loop |
| Fact-checker | `fact-checker-CW` | Verifies claims against the gathered sources |
| Illustrator | `illustrator-CW` | Crafts an image prompt and renders a hero image |
| Repurposer | `repurposer-CW` | Turns the article into social + newsletter variants |

## Note on message types vs. agent names

The streamed UI message `type` values (`researcher`, `marketing`, `writer`,
`editor`, `designer`, `factchecker`, `repurposer`, …) are **not** agent names —
they are a UI contract consumed by the frontend and must stay stable. Renaming an
agent does not change these message types.
