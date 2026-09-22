<div align="center">

<a href="https://herakles.dev">
<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/masthead-light.svg" />
  <img src="assets/masthead.svg" alt="Michael Piscitelli — herakles.dev" width="100%" />
</picture>
</a>

**Solo builder shipping production AI systems.** I run an agentic development practice at
[**herakles.dev**](https://herakles.dev) and I'm launching [**keymakers.ai**](https://keymakers.ai).

[![herakles.dev](https://img.shields.io/badge/herakles.dev-8E74F2?style=flat-square&logo=firefox&logoColor=white)](https://herakles.dev)
[![keymakers.ai](https://img.shields.io/badge/launching-keymakers.ai-111111?style=flat-square&logo=rocket&logoColor=white)](https://keymakers.ai)
![Chicago](https://img.shields.io/badge/Chicago,%20IL-1F2937?style=flat-square&logo=googlemaps&logoColor=white)
![Claude Code](https://img.shields.io/badge/built%20with-Claude%20Code-D97706?style=flat-square&logo=anthropic&logoColor=white)
![profile views](https://komarev.com/ghpvc/?username=herakles-dev&color=8E74F2&style=flat-square&label=profile+views)

<p>
<a href="https://herakles.dev">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="assets/header-light.svg" />
    <img src="assets/header.svg" alt="terminal: michael@herakles-dev" />
  </picture>
</a>
</p>

<br />

<p align="left">
<!--START_SECTION:contribs-->
1,813 contributions in the last year
<!--END_SECTION:contribs-->
</p>

<p>
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/herakles-dev/herakles-dev/output/pacman-contribution-graph-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/herakles-dev/herakles-dev/output/pacman-contribution-graph.svg" />
  <img alt="Pac-Man eating my contribution graph" src="https://raw.githubusercontent.com/herakles-dev/herakles-dev/output/pacman-contribution-graph.svg" />
</picture>
</p>

</div>

I'm Michael — Herakles. Fiber-optic network designer by day, and since mid-2025 a self-taught AI-agentic
engineer by night — building my own orchestration engine one 3am session at a time. The
engineering mindset stuck. The credential didn't.

The origin story is dumb and true: I automated my telecom crew's grunt work so well that we
out-earned the managers. So the company cut our per-foot rate and kept the difference. That's
the whole reason I do this now — I'd rather build the leverage and own it.

So I do. Everything here is self-hosted, runs in production, and the claims check out. I lead the
agents, review the diffs, and steer the system — more conductor than typist, though I still write
plenty of code by hand. I don't ship demos.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-01-light.svg" />
  <img src="assets/section-01.svg" alt="Live right now" width="100%" />
</picture>

- **[fine-print.org](https://fine-print.org)** — paste a Terms of Service, get back what you're
  actually agreeing to. Runs on my own multi-provider LLM gateway, not a single rented API.
- **[subfold.pro](https://subfold.pro)** — a music-reactive visual instrument: real-time 3D
  fractals that fold to the beat.
- **[nightjar](https://github.com/herakles-dev/nightjar)** — an offline Android app that hides data in
  sound and images, and ships the detectors that catch it. Open source, MIT.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-02-light.svg" />
  <img src="assets/section-02.svg" alt="Merged into the wild" width="100%" />
</picture>

<sub><i>Auto-updated weekly by a GitHub Action I own — external PRs that maintainers merged, newest first. No hand-editing.</i></sub>

<!--START_SECTION:merges-->
- **[google-deepmind/formal-conjectures#5481](https://github.com/google-deepmind/formal-conjectures/pull/5481)** &nbsp;`⭐ 1.3k` — feat(ErdosProblems/672): link an external Lean proof of erdos_672.variants.euler · `2026-09-18`
- **[google-deepmind/formal-conjectures#5425](https://github.com/google-deepmind/formal-conjectures/pull/5425)** &nbsp;`⭐ 1.3k` — feat(ErdosProblems/399): prove erdos_399.variants.cambie · `2026-09-18`
- **[affaan-m/ECC#1036](https://github.com/affaan-m/ECC/pull/1036)** &nbsp;`⭐ 265k` — feat(agents,skills): add opensource-pipeline — 3-agent workflow for safe public releases · `2026-03-31`
<!--END_SECTION:merges-->

Two of those are original Lean 4 proofs closing Erdős problems in Google DeepMind's
`formal-conjectures` — one of them fills a real gap in Mathlib. The third put a Claude Code
workflow of mine into a 265k-star repository.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-03-light.svg" />
  <img src="assets/section-03.svg" alt="What I'm building" width="100%" />
</picture>

Bare-metal infrastructure, agent orchestration, whitehat security research, formal math, GPU
visuals, a production SaaS with a real customer. Not a one-trick stack. Each card below sits on its own
clock — the description swaps in on a loop, staggered per card, no two flipping in sync.

<div align="center">

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/project-cards-light.svg" />
  <img src="assets/project-cards.svg" alt="nine self-animating project cards" />
</picture>

</div>

[v11](https://github.com/herakles-dev/v11),
[typesafe-claude-kit](https://github.com/herakles-dev/typesafe-claude-kit) and
[nightjar](https://github.com/herakles-dev/nightjar) are public,
[subfold.pro](https://subfold.pro) is live, and `math-proof` lives at
[erdos672-four-squares-lean](https://github.com/herakles-dev/erdos672-four-squares-lean). The
rest are private or local — ask if you want a look.

<details>
<summary><b>How v11 actually enforces itself</b> — task-as-truth, write-gate hooks, adversarial review pairing, autonomy</summary>

A raw write from an agent doesn't just land — it has to clear a gate first, and every gate outcome feeds back into how much autonomy that agent earns next time.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'primaryColor': '#1f1f25',
  'primaryTextColor': '#e4e4e7',
  'primaryBorderColor': '#8E74F2',
  'lineColor': '#8E74F2',
  'secondaryColor': '#17171b',
  'tertiaryColor': '#17171b',
  'background': '#17171b',
  'mainBkg': '#1f1f25',
  'nodeBorder': '#8E74F2',
  'clusterBkg': '#17171b',
  'edgeLabelBackground': '#17171b',
  'fontFamily': 'JetBrains Mono, ui-monospace, monospace'
}}}%%
flowchart LR
    T[Task created] --> W{Write-gate hook}
    W -->|blocks until reviewed| I[Agent implements]
    I --> R[Adversarial review pairing]
    R -->|FAIL| I
    R -->|PASS| C[Task marked complete]
    C --> A[Autonomy tracking]
    A -.->|earns trust over time| W
```

Four moving parts, each worth its own look:

<details>
<summary>Task-as-truth</summary>

Tasks are the single source of truth for what's actually done — not a status the agent reports about itself. If it's not marked complete in the task system, it didn't happen, no matter what the agent's own summary claims.

</details>

<details>
<summary>Write-gate hooks</summary>

The mechanism that makes task-as-truth real, not just a stated policy: a hook intercepts every write before it lands and blocks anything that hasn't gone through review. An agent can't just skip the gate by not mentioning it.

</details>

<details>
<summary>Adversarial review pairing</summary>

Every non-trivial task gets paired with an independent review pass before it's allowed to complete — a second look built into the pipeline itself, not something that has to be remembered or requested.

</details>

<details>
<summary>Autonomy tracking</summary>

Earned, not granted up front. A project starts at the most-supervised level and only escalates to less oversight after an actual track record — the system has to watch itself work before it's trusted to work less-watched.

</details>

</details>

<details>
<summary><b>Hekaton</b> — the vLLM upgrade that taught me to always ship a rollback plan</summary>

Hekaton is my autonomous coding harness: a customized [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) running my V11 hooks unmodified, driving a tiered ensemble of Qwen coder models. It's portable now — no fixed box. It rents a cloud GPU (H100 or GH200), runs a mission, and tears itself down, with every dollar logged. Latest result: a best-of-3 fan-out took a 12-task polyglot suite from 6/12 to 10/12 for about $4.

Back when it ran on a single rented GH200, I bumped vLLM by one version with no rollback path. It broke multi-model serving on the GH200 mid-session, and I had no fast way back to the last-known-good state — just a slow rebuild. Every dependency bump now ships with a tested rollback plan before it goes anywhere near rented hardware. Expensive lesson, cheap fix.

</details>

<details>
<summary><b>math-proof</b> — 48 machine-checked Lean proofs in 8 days, two closing real Erdős problems</summary>

Formal math was new territory for me going in. `math-proof` produced 48 Lean 4 proofs with zero `sorry`s — every one machine-verified, not just "looks right." Two of them closed actual open problems in Google DeepMind's `formal-conjectures` repo: [erdos_399.variants.cambie](https://github.com/google-deepmind/formal-conjectures/pull/5425) (an elementary mod-8 argument) and [erdos_672.variants.euler](https://github.com/google-deepmind/formal-conjectures/pull/5481), which links out to a standalone proof repo, [erdos672-four-squares-lean](https://github.com/herakles-dev/erdos672-four-squares-lean). Both merged.

</details>

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-04-light.svg" />
  <img src="assets/section-04.svg" alt="Zeus Terminal — how all of this gets built" width="100%" />
</picture>

I'm talking to Claude through it right now. Zeus Terminal is a self-hosted, mobile-first web
terminal I built to replace Termux: tmux persistence, WebSocket transport, 804 tests, continue a
session from my phone to my laptop without losing state. It's a
session multiplexer — every project gets its own window, several Claude Code agents run in
parallel, and a `/handoff` command lets me spin up a fresh session mid-task without losing
context. My daily driver, not a side project.

<p align="center">
  <img src="assets/zeus-terminal-b0c22c3.webp" alt="Zeus Terminal: three live Claude Code sessions side by side, with the task sidebar" width="100%" />
</p>

<sub><i>This README, the Actions that keep it updated, and everything else on this page were
built from inside it.</i></sub>

And the box underneath all of it — plus what it's actually doing right now, live,
recomputed on every fetch, straight off the same machine (no repo commit involved,
unlike everything else on this page):

<p align="center">
  <img src="assets/neofetch.svg" alt="neofetch: the box this all runs on" style="vertical-align:top" />
  <img src="https://opus.herakles.dev/api/readme/hercules-status.svg" alt="live Hercules platform activity" style="vertical-align:top" />
</p>

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-05-light.svg" />
  <img src="assets/section-05.svg" alt="A few things that don't fit on a résumé" width="100%" />
</picture>

- Built a **Pac-Man ghost AI** that lives on my Android homescreen and chases my taps around —
  28KB APK, runs at 2-3% CPU, entirely pointless and I love it.
- My grocery price tracker **bypasses Cloudflare** to watch 900+ items at the store down the
  street, because I got tired of guessing what's actually on sale.
- A phone-to-phone **[acoustic covert data channel](https://github.com/herakles-dev/nightjar)**, with its own on-device detector, because I
  wondered if two phones could talk without a network.
- My login page has **custom GLSL liquid shaders** for no reason other than it looked cool at
  2am and I didn't undo it.

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-06-light.svg" />
  <img src="assets/section-06.svg" alt="Stack" width="100%" />
</picture>

<p align="center">
<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/stack-light.svg" />
  <img src="assets/stack.svg" alt="Python, TypeScript, Rust, Lean 4, Bash, Docker, PostgreSQL, FastAPI, Next.js, CUDA, Kotlin, Linux" width="100%" />
</picture>
</p>

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-07-light.svg" />
  <img src="assets/section-07.svg" alt="By the numbers" width="100%" />
</picture>

<div align="center">

<sub><i>All three cards below are generated by my own script, not a third-party render
service — <a href="scripts/update_readme.py">source</a>. The last one that wasn't broke
the week I rebuilt this page. Zero left now.</i></sub>

<img src="assets/stats.svg" alt="stats" />
<img src="assets/langs.svg" alt="top languages" />
<img src="assets/streak.svg" alt="contribution streak" />

</div>

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/section-08-light.svg" />
  <img src="assets/section-08.svg" alt="Latest pushes" width="100%" />
</picture>

<sub><i>Auto-updated — my own repos, most recently pushed.</i></sub>

<!--START_SECTION:building-->
- **[nightjar](https://github.com/herakles-dev/nightjar)** — Offline Android app demonstrating covert data transmission (hiding data in sound and images) and the detection techniques that can catch it. Acoustic data-over-sound modem, image/audio steganography, passive detector.
- **[typesafe-claude-kit](https://github.com/herakles-dev/typesafe-claude-kit)** `⭐ 1` — Claude Code kit for TypeSafe (Jev): agents, skill, client, calibration tools
- **[herakles-daimon](https://github.com/herakles-dev/herakles-daimon)** — AI-curated, mood-responsive media platform built with the Gemini Live API
- **[opensource-pipeline](https://github.com/herakles-dev/opensource-pipeline)** `⭐ 2` — Safely open-source any project with Claude Code. 3-agent pipeline that strips secrets, verifies sanitization, and generates professional docs. Just say /opensource fork my-project.
- **[v11](https://github.com/herakles-dev/v11)** `⭐ 1` — Spec-driven orchestration protocol for reliable multi-agent Claude Code development — task-as-truth, write-gate hooks, adversarial review pairing, autonomy tracking. Installable.
<!--END_SECTION:building-->

<p align="center">
<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/divider-light.svg" />
  <img src="assets/divider.svg" alt="" width="100%" />
</picture>
</p>

One more thing — Claude left a review.

<div align="center">

<img src="assets/review.svg" alt="A Google-style review of working with me, written by Claude" />

</div>

<p align="center">
<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/coda-light.svg" />
  <img src="assets/coda.svg" alt="" width="100%" />
</picture>
</p>

<div align="center">

Still up late most nights. Still shipping (just watch) If you've made it this far, FOLLOW ME!

**[herakles.dev](https://herakles.dev)** · **[keymakers.ai](https://keymakers.ai)** · [hello@herakles.dev](mailto:hello@herakles.dev)

</div>
