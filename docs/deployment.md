# Deployment guide

Status: prepared on 15 November 2026. Nobody has deployed the app yet, so no step on a
public host has been tried. The container steps below were checked locally on an arm64
Mac (see [verification](verification.md#draft-5-stage-7-container-and-browser-checks)). The
guide is generic: any container host that gives a public HTTPS address and a persistent
volume will do. Hosts named below are examples only, not recommendations.

The app is one container. It serves the web app, the API, `/mcp`, `/healthz` and `/readyz`
on one port. All mutable state lives under `/app/state`, which must be a persistent volume
([spec 11](technical-spec.md#11-stack-structure-and-deployment)).

## 1. Prerequisites

- A container host that can run a Linux image, give it an HTTPS address and mount a
  persistent volume at `/app/state`. Examples: a virtual machine with Docker Compose behind a
  reverse proxy such as Caddy or nginx, or a platform service with persistent disks.
- Docker with BuildKit on the machine that builds the image.
- The source revision you intend to submit, committed. Build the image from a clean checkout
  of that commit (section 2), not from a working tree with uncommitted or untracked files.
- Outbound HTTPS from the container to `power.larc.nasa.gov`. If you later turn AI on, it also
  needs `api.openai.com` for the OpenAI provider or `api.anthropic.com` for the Anthropic
  provider. The browser loads map tiles from `tiles.openfreemap.org`.
- Secrets are set in the host's secret or environment settings. Never put them in the image,
  the repository or a chat message.

## 2. Build the image

`docker build .` sends the whole directory, including uncommitted changes and untracked
files, because `.dockerignore` does not exclude them. Build from a separate, clean checkout of
the commit instead:

```sh
git worktree add ../td-<revision> <revision>
cd ../td-<revision>
git status --porcelain    # must print nothing
docker build -t trend-detective:<revision> .
```

A fresh clone checked out at `<revision>` works as well. Remove the worktree afterwards with
`git worktree remove ../td-<revision>`.

Most container hosts run x86_64. If your build machine is an arm64 machine (such as an Apple
silicon Mac) and the host is x86_64, build for the host:

```sh
docker build --platform linux/amd64 -t trend-detective:<revision> .
```

Tag each image with the commit it was built from, so you can roll back (section 9). The image
contains the built frontend, the backend, the committed `backend/data/cache.sqlite` and the
reviewed corpus. It contains no `.env` file, tests or scripts.

The amd64 image builds, but it has not yet been run on a real x86_64 machine. Under emulation
on an arm64 Mac its server did not start (section 10). Run the checks in section 8 on the
host before you call the deployment working.

## 3. Environment variables

Start from [.env.example](../.env.example). Set these in the host's configuration, not in a
file inside the image.

Required for a public deployment:

| Variable | Value |
| --- | --- |
| `PUBLIC_BASE_URL` | The public HTTPS origin, for example `https://trend-detective.example.org`, with no trailing slash. Links the app builds and the hosts `/mcp` accepts come from it. |
| `FORWARDED_ALLOW_IPS` | The address or address range of the host's HTTPS proxy. Only requests from these addresses may set the visitor address through `X-Forwarded-For`. The image default, `127.0.0.1`, trusts only loopback. If it is wrong, every visitor shares the proxy's address and one rate limit. Do not use `*` unless the container can be reached only through the proxy. See the note below the table for a proxy on the same virtual machine. |
| `AI_ENABLED` | `false` (section 6) |
| `AI_PROVIDER` | `disabled` |
| `RAG_ENABLED` | `false` |

With a reverse proxy on the same virtual machine and the container published on
`127.0.0.1:8000` (section 4), the container probably does not see the proxy as `127.0.0.1`.
Docker forwards the connection through its own proxy process, so it most likely arrives from
the gateway of the container's network, for example `172.17.0.1` on the default bridge. This
follows from Docker's default networking and has not been tested. Find the gateway with
`docker network inspect bridge` (or the network the container is on) and set
`FORWARDED_ALLOW_IPS` to it. Then confirm in section 8, check 10, that two clients get separate
rate limits.

Optional:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8000` | The port uvicorn listens on. Many hosts set it for you. |
| `RATE_LIMIT_PER_MINUTE` | `120` | Requests per visitor address per minute. Over the limit the API answers 429 `rate_limited`. |
| `CACHE_PATH` | `/app/state/power.sqlite` | The NASA response cache. On first start it is seeded from the image's `cache.sqlite`. |
| `OPERATIONAL_DB_PATH` | `/app/state/operations.sqlite` | Counters, AI budget reservations and the investigation record. |
| `SNAPSHOT_PATH` | `/app/state/snapshots` | Content-addressed evidence that pinned links depend on. |

Leave the three paths unset unless the host forces another mount point. If you change them,
keep all three on the persistent volume.

AI settings, used only when the owner turns AI on (section 6): `AI_EVALUATED`, `AI_MODEL`,
`AI_DAILY_TURNS`, `AI_RATE_PER_MINUTE`, `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`, or the
Ollama settings `OLLAMA_URL` and `OLLAMA_MODEL_DIGEST`), `AI_DAILY_BUDGET_MICROUSD`,
`AI_INPUT_MICROUSD_PER_MILLION`, `AI_OUTPUT_MICROUSD_PER_MILLION`, `AI_BUDGET_DURABLE`,
`RAG_VECTOR_STORE_ID`, `RAG_CORPUS_VERSION`, `RAG_SEARCH_MICROUSD_PER_CALL`,
`RAG_EVALUATED` and `DISCOVERY_EVALUATED`. Their meanings are in `.env.example` and spec 8.

## 4. Mount the state volume

Mount one persistent volume at `/app/state`. The app writes `power.sqlite`,
`operations.sqlite` and `snapshots/` there. Without it, every container replacement loses the
evidence behind pinned links and resets the AI budget.

With Docker or Compose on a virtual machine, use a named volume:

```sh
docker volume create trend-state
docker run -d --name trend-detective -p 127.0.0.1:8000:8000 \
  --env-file <path to the host's env file> \
  -v trend-state:/app/state --restart unless-stopped \
  trend-detective:<revision>
```

[compose.yaml](../compose.yaml) uses the same named volume `trend-state`, but it differs in
two ways. It publishes port 8000 on every interface (`"8000:8000"`), so on a public virtual
machine plain HTTP on port 8000 is reachable from the internet and visitors can bypass the
HTTPS proxy. Behind a reverse proxy, either change the mapping to `"127.0.0.1:8000:8000"` (a
team decision, because `compose.yaml` is shared) or block port 8000 in the firewall. It also
reads its environment from `./.env` in the directory you run it from, not from a separate
host env file. The command in
the Dockerfile header, `docker run --rm ... trend-detective`, mounts
no volume. Its state goes to an anonymous volume that `--rm` deletes, so do not use it for a
deployment.

The container runs as the system user `app`. Its uid is given when the image is built (999 in
the checked build) and is not fixed in the Dockerfile. Check it for your image:

```sh
docker run --rm --entrypoint id trend-detective:<revision>
```

A new, empty Docker named volume takes its owner from the image, so it works as it is. A
platform disk that already holds files, or is owned by root, must be made writable by that uid
first. Otherwise the app stops at startup with `PermissionError` (observed: exit code 3).

Back up the volume before every new image and include it in regular backups.

## 5. Health and capability checks

After the container starts, check from outside the host:

```sh
curl -fsS https://<public host>/healthz          # {"status":"ok"}
curl -fsS https://<public host>/readyz           # {"status":"ready"}
curl -fsS https://<public host>/api/capabilities
curl -fsS https://<public host>/api/examples
```

With AI off, `/api/capabilities` reports `ai_planner_available`, `ai_discovery_available` and
`ai_explanation_available` all `false`. `/api/examples` lists four examples. Neither health
route calls NASA or spends AI credit. Use `/healthz` as the host's liveness check.

The server log holds the method, path, status and duration of each request, with no query
string or client address. Check it for `Traceback` or `ERROR` lines after the checks.

## 6. Turning the AI on or off

Discovery and explanations are on by default (`RAG_ENABLED`, `DISCOVERY_EVALUATED` and
`RAG_EVALUATED` default to `true`, the owner's decision of 15 November 2026), but nothing
AI runs until the planner, the key and the corpus below are configured. To run with no AI at
all, deploy with `AI_ENABLED=false`, `AI_PROVIDER=disabled` and no API key. The
manual settings, the keyword question bar, examples, comparisons and exports all work this
way.

Each AI path has its own switch. The code turns a path on only when all of its conditions
hold, so a key alone never turns AI on:

- Planner (`/api/plan`): `AI_ENABLED=true`, `AI_EVALUATED=true`, an exact `AI_MODEL` and an
  `AI_PROVIDER`. A hosted provider (`openai` or `anthropic`) also needs its key
  (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`), `AI_BUDGET_DURABLE=true` and positive
  `AI_DAILY_BUDGET_MICROUSD`, `AI_INPUT_MICROUSD_PER_MILLION` and
  `AI_OUTPUT_MICROUSD_PER_MILLION`. `ollama` needs no key and has no budget gate; it needs
  `OLLAMA_MODEL_DIGEST` and an `OLLAMA_URL` the container can reach. The default,
  `http://127.0.0.1:11434`, points at the container itself.
- Discovery (`/api/discover`): the planner on OpenAI, retrieval set up (`RAG_ENABLED=true`, a
  `vs_...` store ID, a positive `RAG_SEARCH_MICROUSD_PER_CALL` and a `RAG_CORPUS_VERSION` equal
  to `corpus_version` in `backend/data/corpus/manifest.json` of the image), and
  `DISCOVERY_EVALUATED=true`.
- Explanation (`/api/explain`): the same as discovery, with `RAG_EVALUATED=true` in place of
  `DISCOVERY_EVALUATED`.

The owner has read the [evaluation results](evaluation-results.md) and chosen to keep
discovery and explanations on although their gates were not met; set `DISCOVERY_EVALUATED` or
`RAG_EVALUATED` to `false` to turn one off. Set
`AI_BUDGET_DURABLE=true` only when `/app/state` is the persistent volume of section 4, because
the budget reservations live in `operations.sqlite`.

The container reads its environment only when it is created. `docker restart` keeps the old
values, so after any change, recreate the container:

- Docker: `docker rm -f trend-detective`, then the same `docker run` as in section 4 with the
  edited env file.
- Compose: `docker compose up -d`, which recreates the container when its environment changed.
- A platform service: redeploy.

Then check `/api/capabilities` again.

To turn AI off quickly, set `AI_ENABLED=false` and recreate the container as above. The rest of
the app is not affected.

## 7. Rotate or delete the OpenAI vector store and files

Only the owner does this, because uploads and storage are paid. The upload runs on the
owner's machine, not in the container:

```sh
cd backend
uv run --env-file ../.env python -m scripts.upload_corpus --max-bytes <cap>
```

It prints `RAG_VECTOR_STORE_ID` and `RAG_CORPUS_VERSION`, and records the store ID and every
file ID in `state/corpus-files.json` at the repository root (local state, not committed).

To rotate to a new corpus:

1. Rebuild the corpus and commit it, so the manifest in the new image has the new
   `corpus_version`.
2. Upload it with the command above.
3. Build and deploy the new image with the new `RAG_VECTOR_STORE_ID` and
   `RAG_CORPUS_VERSION`. If the two versions differ, discovery and explanation stay off and
   the planner is unaffected.
4. Check `/api/capabilities`.
5. Delete the old store and its files (below).

To delete a store and its files, take the IDs for that corpus version, or for a superseded
attempt, from `state/corpus-files.json`, then delete:

- the vector store: `DELETE https://api.openai.com/v1/vector_stores/{vector_store_id}`
- each file: `DELETE https://api.openai.com/v1/files/{file_id}`

Use the provider's own dashboard or its API with the key from the environment. Do not paste
the key into a command line that is logged or shared. A store that nobody uses expires after
30 days, but its files do not, so delete the files as well. Before deleting the store a
deployment uses, turn RAG off there (`RAG_ENABLED=false`) and recreate the container or
redeploy (section 6).

## 8. Verify the deployment

Run these checks on the public HTTPS address and record each result, with the date, image tag
and commit, in [verification](verification.md). This is the deployment list of
[spec 12](technical-spec.md#12-build-plan-and-submission).

1. **HTTPS journey.** In a real browser, open the public address and check that the browser
   shows a valid certificate. Open each of the four examples, then run a manual case and
   check the verdict, the chart and the four tabs (Answer, Explore, Evidence, Learn).
2. **Pinned link in a fresh session.** Copy a case link with "Copy link". Open it in a
   private window or another browser, and check that the verdict and numbers are the same.
3. **Exports.** Download the yearly and monthly CSV, the evidence JSON and the chart PNG from
   the public address.
4. **Phone and keyboard.** Open the app on a real phone, check that the page does not scroll
   sideways, and open a case. On a computer, use only the keyboard: from the question bar,
   run a case, move through the tabs with the arrow keys and reach the footer.
5. **WebGL fallback.** Open the app in a browser with WebGL turned off (for example Chrome
   started with `--disable-webgl`). The globe area shows a message, and cases still answer.
6. **Tile outage.** Block `tiles.openfreemap.org` in the browser's developer tools. Cases and
   pinned links still work, without a basemap.
7. **NASA outage.** On a copy of the deployment (not the public one), point `HTTPS_PROXY` at
   an address that refuses connections, and open a case that is not cached. It should answer
   502 `source_unavailable` with the spec 10 error shape, and the page shows "Try again".
   Cached cases still answer.
8. **OpenAI outage.** Only when an AI path is on: on a copy, make `api.openai.com`
   unreachable. Manual results still show and the AI path reports that it is unavailable.
9. **Cancellation.** Open an uncached case and, before it loads, open another case. The
   second case shows, and the first never replaces it.
10. **Rate and budget exhaustion.** On a copy with a low `RATE_LIMIT_PER_MINUTE` (for example
    5), send more requests than the limit; the API answers 429 `rate_limited` and the page
    says so. Only when AI is on: with a low `AI_DAILY_TURNS` or budget, the AI path answers
    429 and manual cases keep working.
11. **Linux container on the host's architecture.** Check that the image that is running was
    built for the host's architecture and that `/readyz` answers.
12. **Volume replacement.** Open a new, uncached case and copy its pinned link. Remove the
    container and create a new one from the same image on the same volume (`docker rm -f`,
    then `docker run` as in section 4, or a redeploy on a platform service). A restart keeps
    the same container and does not test this. Open the pinned link again; it gives the same verdict without a new NASA call.

## 9. Rollback

1. Keep the previous image tag and the volume backup from section 4.
2. To undo an AI change, set `AI_ENABLED=false` and recreate the container or redeploy
   (section 6).
3. To undo an image change, deploy the previous tag on the same volume and run the checks in
   section 5. An older image reading state written by a newer one has not been tested.
4. If the older image fails on that state, restore the volume backup taken before the
   upgrade. Pinned links made after the backup then stop working, with an explicit error.

## 10. Known limits of this guide

- No step has been run on a public host. HTTPS, the host's proxy and `FORWARDED_ALLOW_IPS`
  are untested.
- The amd64 image builds but has not been run on x86_64. Under Rosetta emulation on an arm64
  Mac, the server stayed at full CPU for 306 s without finishing startup; the stall was traced
  to `import scipy.stats`. It may be an emulation problem, but that is not confirmed.
- The uid of the `app` user is not fixed (section 4).
- Spec 10 says an unavailable snapshot or analysis version answers 409. The code answers 502
  for an unknown snapshot and 400 for an unknown analysis version. The team has to decide
  which one changes.
