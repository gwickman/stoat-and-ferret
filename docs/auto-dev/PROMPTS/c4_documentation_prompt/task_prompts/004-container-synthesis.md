# Task 004: Container Synthesis

Read AGENTS.md first and follow all instructions there.

## Objective

Map components to deployment containers. Analyze infrastructure definitions (Dockerfiles, K8s manifests, cloud configs) alongside component documentation to create container-level architecture. Generate OpenAPI specifications for container APIs.

## Context

C4 architecture documentation generation for `${PROJECT}` version `${VERSION}`.
- Component documentation is complete in `docs/C4-Documentation/c4-component*.md`
- This task maps logical components to physical deployment units

## Tasks

### 1. Read Component Documentation

Read `docs/C4-Documentation/c4-component.md` (master index) and all `c4-component-*.md` files.

### 2. Discover Infrastructure Definitions

Search the project for deployment and infrastructure files:

```
Dockerfiles, docker-compose.yml/yaml
kubernetes/ or k8s/ directories (deployments, services, ingress)
terraform/ or .tf files
serverless.yml, SAM templates
CI/CD pipeline definitions (.github/workflows/, .gitlab-ci.yml, Jenkinsfile)
Procfile, app.yaml (PaaS configs)
package.json scripts (if they define service start commands)
pyproject.toml / setup.py (entry points)
```

### 3. Identify Containers

A container is **something that needs to be running** for the system to work:
- Web applications (frontend SPAs, server-rendered apps)
- API servers (REST, GraphQL, gRPC)
- Background workers / job processors
- Databases (PostgreSQL, MongoDB, Redis, etc.)
- Message queues (RabbitMQ, Kafka, SQS)
- File storage systems
- Reverse proxies / API gateways

Development tools and test runners (Jest, pytest, cargo test, etc.) are **NOT** containers. They run inside development environments and CI pipelines, not as independently deployable units. Only include them if they are separately deployed services (e.g., a dedicated test environment with its own infrastructure).

**If no explicit infrastructure definitions exist:**
- Infer containers from the codebase structure (entry points, main files, service definitions)
- Document inferred containers clearly as "inferred from code structure"

### 4. Map Components to Containers

Each component belongs to exactly one container. Create the mapping:

| Container | Components | Rationale |
|-----------|-----------|-----------|
| API Server | AuthComponent, UserComponent | Co-deployed in same process |
| Database | DataModels | PostgreSQL backing store |

### 5. Document Container APIs

For each container that exposes an API:
- Extract endpoints from component interfaces and route definitions
- Create an OpenAPI 3.1 specification
- Save as `docs/C4-Documentation/apis/[container-name]-api.yaml`

### 6. Create Container Documentation

Create `docs/C4-Documentation/c4-container.md`:

```markdown
# C4 Container Level: System Deployment

## Container Diagram

C4Container
    title Container Diagram for [System Name]
    Person(user, "User", "Description")
    System_Boundary(system, "[System Name]") {
        Container(api, "API Server", "Technology", "Description")
        ContainerDb(db, "Database", "Technology", "Description")
    }
    System_Ext(ext, "External System", "Description")
    Rel(user, api, "Uses", "HTTPS")
    Rel(api, db, "Reads/writes", "SQL")

## Containers

### [Container Name]

- **Name**: [Name]
- **Description**: [What it does and how it's deployed]
- **Type**: [Web Application / API / Database / Queue / Worker / etc.]
- **Technology**: [Runtime, framework, language]
- **Deployment**: [Docker / K8s / Cloud service / etc.]

#### Purpose
[Detailed description]

#### Components Deployed
- [Component Name] — [link to component doc]

#### Interfaces
- **[API Name]**: [Protocol] — [OpenAPI spec link]
  - `GET /endpoint` — [Description]
  - `POST /endpoint` — [Description]

#### Dependencies
- [Other Container]: [Protocol, description]
- [External System]: [Integration type]

#### Build Output
- **Build Command**: [e.g., `npm run build`, `cargo build --release`]
- **Output Directory**: [e.g., `dist/`, `target/release/`]
- **Key Artifacts**: [List of output files — compiled JS, declaration files, binaries, etc.]
- **Module Format**: [e.g., ESM, CJS, UMD]
- **Declaration Files**: [e.g., `.d.ts` files for TypeScript libraries]

#### Infrastructure
- **Config**: [Link to Dockerfile/manifest]
- **Scaling**: [Strategy]
- **Resources**: [Requirements if known]

## External Systems
- [System Name]: [Type, purpose, integration method]

## Container-Component Mapping

| Container | Components |
|-----------|-----------|
| ... | ... |
```

## Output Requirements

Save outputs to `comms/outbox/exploration/c4-${VERSION}-004-containers/`:

### README.md (required)

First paragraph: Summary — container count, key deployment patterns found.

Then:
- **Containers Identified:** count with list
- **Infrastructure Files Found:** what deployment configs exist
- **API Specifications Generated:** list of OpenAPI files
- **Inferred vs Explicit:** which containers were inferred vs found in infra configs
- **External Systems:** list of external dependencies

### Container files

- `docs/C4-Documentation/c4-container.md` — main container doc
- `docs/C4-Documentation/apis/*.yaml` — OpenAPI specs (create `apis/` directory only if network APIs exist)

**Library projects without network APIs:** If the system has no network APIs (e.g., it is a library consumed via imports, not a running service), do NOT create an `apis/` directory. Instead, note in the container doc: "No API specifications — this system is a library consumed via direct imports."

## Allowed MCP Tools

- `read_document` (file creation uses Claude Code's native file system capabilities)

## Guidelines

- **Ground in reality** — containers should reflect actual deployment, not ideal architecture
- **Technology details belong here** — C4 container level is where you show tech choices
- **OpenAPI specs should be valid** — include realistic schemas, not just endpoint stubs
- **If no infrastructure exists** — document what containers would be needed and mark as "inferred"
- **Show communication protocols** — HTTP, gRPC, SQL, AMQP, etc. on all relationship arrows
- **Keep under 300 lines** — split into separate files if the system has 5+ containers
- Do NOT document personas or user journeys — that's Task 005's job
- Do NOT commit — the master prompt handles commits
