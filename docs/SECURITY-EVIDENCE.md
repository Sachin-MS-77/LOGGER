# WASM sandbox attack evidence

The projection module is executed by the actual `Sandbox.project` wrapper. Trusted Python still performs structural decoding. These tests establish the listed boundaries, not absence of all vulnerabilities in Wasmtime or the surrounding application. No competitor-exclusivity claim is made.

Run `python -m pytest tests/test_sandbox_adversarial.py -v`.

| Attack | Expected boundary | Reproduce | Result |
|---|---|---|---|
| Infinite loop | 10,000 fuel exhausted; Wasmtime trap | `python -m pytest tests/test_sandbox_adversarial.py -k infinite_loop -v` | Pass |
| Initial memory >64 KiB | Store rejects allocation | `python -m pytest tests/test_sandbox_adversarial.py -k initial_memory -v` | Pass |
| Runtime memory growth | `memory.grow` returns -1; allocation denied | `python -m pytest tests/test_sandbox_adversarial.py -k memory_growth -v` | Pass |
| Filesystem import | All imports rejected before instantiation | `python -m pytest tests/test_sandbox_adversarial.py -k path_open -v` | Pass |
| Network import | All imports rejected | `python -m pytest tests/test_sandbox_adversarial.py -k sock_open -v` | Pass |
| Environment import | All imports rejected | `python -m pytest tests/test_sandbox_adversarial.py -k environ_get -v` | Pass |
| Arbitrary host function | No linked host functions | `python -m pytest tests/test_sandbox_adversarial.py -k system -v` | Pass |
| Out-of-bounds read | Wasmtime memory trap | `python -m pytest tests/test_sandbox_adversarial.py -k out_of_bounds -v` | Pass |
| Malformed module | Compilation rejected | `python -m pytest tests/test_sandbox_adversarial.py -k malformed -v` | Pass |
| Wrong selector ABI | Must export `(i32) -> i32` | `python -m pytest tests/test_sandbox_adversarial.py -k signature -v` | Pass |
| Oversized compiled input | >64 KiB rejected before compilation | `python -m pytest tests/test_sandbox_adversarial.py -k oversize -v` | Pass |

The binary-size cap limits compilation input; fuel limits execution only. Compilation CPU/memory isolation is not equivalent to a separate OS sandbox. Signed bundles and human semantic review remain necessary: a perfectly bounded parser can still map a source IP to the wrong field.
