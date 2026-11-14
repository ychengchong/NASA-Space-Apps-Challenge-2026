# Contract changes and test migration

This branch implements the review fixes authorized by the team. Draft 2 tests
that assert the retired correction, silent clamping, lossy coordinates, unsupported
intervals or free-running chat are not acceptance requirements for Draft 3.
Arithmetic/reference coverage is retained; assertions change to the explicit new
contracts. No test is marked skipped or expected-failure to conceal a defect.

The unsafe free-running assistant and its two provider-loop test modules are
removed as a feature replacement, not treated as passing checks. Their replacement
is the bounded structured planner: tests cover local/hosted fake transports,
disabled defaults, schema/type failures, input limits, timeouts/cancellation,
confirmation-only output, model identity, ambiguity and atomic budget reservations.
The old HTTP path remains a tested refusal and cannot execute a model or tool.

User research and real-model semantic accuracy are separate evidence. Neither
fake-provider tests nor valid JSON establish a 90% semantic success rate. AI remains
off until an owner supplies the exact model, records evaluation and enables it.
