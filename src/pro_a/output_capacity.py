"""Application output capacity; independent of provider maximums."""
OPERATION_OUTPUT_BUDGET_POLICY_VERSION = "operation-output-budget-v2"
SEGMENT_OUTPUT_CEILING = 24000
SERIES_OUTPUT_LIABILITY_CEILING = 384000
# Frozen v1 identities retain their original request and accounting ceiling.
LEGACY_SEGMENT_OUTPUT_CEILING = 12000
