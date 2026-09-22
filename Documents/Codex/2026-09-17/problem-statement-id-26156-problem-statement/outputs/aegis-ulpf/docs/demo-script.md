# LOGFLUX: 2-minute presentation

**30 seconds of PPT + 90 seconds of live demo.** Rehearse with a timer and allow the indicated intervals for clicks. Prepare a reviewed parser candidate beforehand; do not wait for model generation during the recording.

| Time | Show / action | Narration |
|---|---|---|
| 0:00–0:15 | PPT: problem and architecture | “Enterprise devices speak different log languages. LOGFLUX converts perimeter logs into consistent, traceable events, while preserving the original bytes. It supports local operation, including air-gapped deployments with dependencies staged beforehand.” |
| 0:15–0:30 | PPT: three differentiators | “Our key features are reviewed parser adaptation, signed evidence checkpoints, and investigation linked to raw records. This is a working single-node prototype. Physical device validation and distributed enterprise scaling remain future validation stages.” |
| 0:30–0:43 | Command Center → Run demo replay | “Here is the actual application. This demonstration uses clearly labeled synthetic replay. Counts, source distribution and activity charts update from records processed by the backend.” |
| 0:43–0:57 | Event Stream → inspect an event | “An event shows the original log beside normalized addresses, ports and actions. Its source, receipt time and byte hash remain available for investigation.” |
| 0:57–1:18 | Parser Lab → prepared candidate → validation / registry | “Unfamiliar formats enter review. Optional local Qwen3 suggests field mappings; the analyst validates their meaning before approval. Approved mapping modules are signed, versioned and run with bounded WASM execution. Replay creates new revisions without replacing raw evidence.” |
| 1:18–1:35 | Evidence Vault → inspect → Verify evidence | “Verification checks the original hash, Merkle inclusion path and quorum signatures. These witnesses are local to this prototype, so independent custody still requires deployment on separate machines.” |
| 1:35–1:50 | Investigation → select IP → timeline / saved case | “We can focus an address, filter observations and follow rule signals into an evidence case. The Fracture gauge is an uncalibrated activity heuristic, not a trained threat score.” |
| 1:50–2:00 | System & Outputs → exports / outbox | “Finally, normalized data can be exported as JSONL, ECS or CSV. HTTP outputs retry delivery, making the evidence available to downstream security tools.” |

## Recording preparation

1. Log in before recording; never capture access tokens or private key files.
2. Use Obsidian theme and a readable desktop viewport.
3. Prepare a candidate and signed checkpoint; verify a proof before recording.
4. Switch from PPT to the dashboard at 0:30.
5. Use a physical firewall feed only after confirming receipt from that device. Otherwise keep replay/lab labels visible.
6. The existing MP4 is a historical 60-second screenshot walkthrough, not this new two-minute recording.

## If judges ask about ML

Qwen3 0.6B assists parser proposals. Drain3 mines templates. Detections use deterministic rules. No trained anomaly classifier, Graph ML or SHAP pipeline is implemented; the Fracture Index uses a documented hand-written count formula.
