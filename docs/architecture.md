# Architecture at a glance

Contoso Creative Writer — modernized to the Microsoft Agent Framework and deployed
as a secure Azure Container Apps service that **reuses** an existing Microsoft
Foundry project for all AI, and hosts only the frontends/compute in a new
resource group.

```mermaid
flowchart LR
  user([User / Browser])

  subgraph RG1["RG: Contoso-Creative-Writer · Sweden Central · NEW compute"]
    web["agent-web<br/>Container App · React + nginx"]
    api["agent-api<br/>Container App · FastAPI"]
    env["Container Apps Environment"]
    acr[("Azure Container Registry")]
    obs["Application Insights<br/>+ Log Analytics"]
  end

  subgraph RG2["RG: Contoso-Video-Prod-AI · REUSED shared Foundry"]
    proj["Microsoft Foundry project<br/>con-vid-prod-sweden-project"]
    subgraph agents["Microsoft Agent Framework (multi-agent)"]
      r["Researcher"] --> p["Product Marketing"] --> w["Writer"] --> e["Editor"]
    end
    m1[["gpt-5.6-terra<br/>(agents)"]]
    m2[["gpt-5.6-luna<br/>(judge)"]]
    emb[["text-embedding-3-large"]]
    bing{{"Bing Grounding"}}
    srch[("Azure AI Search<br/>contoso-products index")]
  end

  mi[/"User-assigned Managed Identity<br/>Contoso-Video-Builder-MI"/]

  user -->|HTTPS| web -->|/api proxy| api
  api --> agents
  r -->|web research| bing
  p -->|vector search| srch
  agents --> proj --> m1 & m2 & emb
  api -. OpenTelemetry traces .-> obs
  api ==>|"Entra ID · DefaultAzureCredential<br/>(no keys)"| mi
  mi -. "RBAC: Foundry User · Search Index/Service · AcrPull" .-> proj
  mi -. AcrPull .-> acr
  api -->|image pull| acr

  classDef reuse fill:#eef7ff,stroke:#4488cc;
  classDef new fill:#eefaf0,stroke:#33aa66;
  class proj,agents,r,p,w,e,m1,m2,emb,bing,srch reuse;
  class web,api,env,acr,obs new;
```

## How the request flows
1. The user opens **agent-web** (React) and submits a topic + instructions.
2. **agent-web** proxies to **agent-api** (FastAPI), which runs the multi-agent
   workflow on the **Microsoft Agent Framework**:
   **Researcher** (Bing grounding) → **Product Marketing** (Azure AI Search
   vector retrieval) → **Writer** → **Editor** (with a feedback loop).
3. The agents call the Foundry models (`gpt-5.6-terra`, embeddings
   `text-embedding-3-large`) in the reused project.
4. Traces (agents, tools, model calls) are exported via **OpenTelemetry** to
   **Application Insights** and surface in the Foundry Agent Monitor.

## Security posture
- **Passwordless**: the app authenticates with **Microsoft Entra ID** via
  `DefaultAzureCredential` bound to the shared **user-assigned managed identity** —
  no API keys anywhere.
- **Least-privilege RBAC** on the identity: Foundry User (models + Bing),
  Search Index Data Contributor + Search Service Contributor (product retrieval),
  AcrPull (image pull).
- **HTTPS-only** ingress on both Container Apps; images come from a private ACR
  pulled with the managed identity.
- **CI/CD** (GitHub Actions) uses **OIDC federation** — no stored secrets.
- AI resources are **reused, not duplicated** — one Foundry, one identity.
