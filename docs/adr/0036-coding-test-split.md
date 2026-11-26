# Coding test split: limited visible samples, hidden generalization tests

Two or three visible tests cover the statement examples and basic edge cases. Hidden tests cover edge cases, invalid input and scale. Practice may expose a broader visible set; formal assessments stay limited.

**Status:** accepted — visible/hidden split and test categories. Harness and per-language adapters remain open.

## Consequences

- Visible tests are part of the task contract and must be consistent across languages.
- Hidden tests must not duplicate visible tests exactly; they measure generalization.
- Practice may reveal more tests as coaching, but must not reuse formal hidden fixtures.
- Test authoring needs review for ambiguity, flakiness and language-specific behavior.
- The report states hidden tests ran at submission, without exposing cases.
- Scale tests must respect execution time and memory limits.
