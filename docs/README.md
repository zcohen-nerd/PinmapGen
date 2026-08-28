# PinmapGen documentation

Start with the repository [README](../README.md) for installation and the
guided Fusion 360 workflow, or the [USER_GUIDE](../USER_GUIDE.md) for a
role-based tour (designer / firmware / instructor). The guides here go
deeper on one topic each:

| Guide | What it covers |
|-------|----------------|
| [usage.md](usage.md) | Full CLI reference: every option, per-MCU examples, watch mode, CI recipes |
| [workflows.md](workflows.md) | Team workflows: solo, designer+firmware pairs, classrooms, version control |
| [troubleshooting.md](troubleshooting.md) | Symptom → fix, including the exact validation messages the tool prints |
| [faq.md](faq.md) | Short answers: supported MCUs, licensing, when to regenerate |
| [output-formats.md](output-formats.md) | What each generated file contains and how to consume it |
| [extending.md](extending.md) | Adding a new MCU as a TOML profile — no code required |

Fusion 360 specifics (installing and running the ULPs) live next to the
scripts themselves in
[fusion_addin/ULP_GUIDE.md](../fusion_addin/ULP_GUIDE.md).

`internal/` holds historical development documents (milestone logs, the
original success writeup, the manual Fusion test plan). They are kept for
context and are not maintained as user documentation.
