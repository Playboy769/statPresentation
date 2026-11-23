# return-distribution-check: skilltest_duplicates.csv

exit code: **2**

## Integrity gates

| check | value |
|---|---|
| rows | 2432 |
| bad_dates | 0 |
| missing_close | 0 |
| nonpositive_close | 0 |
| duplicate_dates | 3 |

**STOPPED:** 3 duplicate dates - would create spurious returns and inflate any date join; fix the source, do not auto-drop

No statistics were computed.
