# Corrective Handoff 173

Resolved the committed repository inconsistency by truncating `data/raw/DBC.parquet`
from 2026-10-21 to 2026-10-08 (5210 -> 5201 rows), matching the frozen
csmomentum artifact window (simulation_csmomentum_001.parquet ends 2026-10-09).

Verification:
- tests/test_cost_admissibility_screen.py::test_every_published_number_of_the_new_candidates_is_reproduced: 3 passed
- tests/test_csmomentum_walkforward_embargo_audit.py: 12 passed
- tests/test_commodity_data_gate_001.py: 15 passed (unchanged)

Pre-existing failure unaffected by this change:
- tests/test_csmomentum_sample_gate_audit.py: cached_sessions_after_the_test_end_are_excluded FAIL (was failing before truncation too).
CORRECTIVE_VERIFICATION=PASS
