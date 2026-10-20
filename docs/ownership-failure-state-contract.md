# Ownership failure and partial processing contract

The existing `independent-candidate-isolation-v1` policy isolates compiler failure
to the rejected segment. This document makes its observable state contract
explicit; it does not relax ownership or change the v7 extraction stop boundary.

* Attempt: a completed HTTP/tool response can have external outcome SUCCEEDED.
  That records external completion, not semantic acceptance. Its Raw/outcome is
  immutable. INVALID_SEGMENT_RESPONSE produces no Accepted Result for that leaf.
* Segment: compiler ownership rejection records SEGMENT_FAILED and terminal
  FAILED. Ordinary processing never retries this leaf. Other frozen PLANNED
  leaves with disjoint assigned ownership remain eligible work.
* Series: OPEN while such work remains; FAILED when terminal coverage contains
  a failed leaf. Source coverage cannot be COMPLETE with a failed leaf.
* Run: EXTRACTION_PROCESSING/PENDING while independent planned work remains.
  Once that work is exhausted it becomes BLOCKED/FAILED, not Semantic processing.
  Unknown external results require recovery and do not justify another send.

Explicit bounded resume has its separately frozen STOP_ON_FIRST_NEW_FAILURE call
budget contract; it is not permission to retry a compiler-rejected leaf. The
ordinary processing policy can continue unrelated leaves without accepting the
failed response or claiming complete coverage.

The ten old ownership tests asserted immediate whole-Run BLOCKED after the first
of two leaves failed. That assertion omitted the independent pending leaf. The
replacement assertions require the exact intermediate state, failed and pending
segments, disjoint ownership, immutable failed outcome, zero rejected acceptance,
one independent later acceptance, exactly two attempts, final BLOCKED/FAILED and
no Semantic job. They do not accept an arbitrary set of states.
