# Hidden tests run only at final submission

Formal coding assessments expose visible sample tests during the session. Hidden tests run only at final submission and are never iterable.

**Status:** accepted — hidden-test timing and visible/hidden split. Harness and retry policy remain open.

## Consequences

- The execution API must distinguish visible-sample runs from the final hidden run.
- Hidden test cases, inputs and per-case outputs are never returned during the session.
- The final submission triggers one hidden evaluation; re-running it requires an explicit retry policy.
- Practice may expose more tests but must not reuse formal hidden fixtures.
- The report states that hidden tests were evaluated once at submission.
- A failed submission must not leak hidden cases through logs or error messages.
