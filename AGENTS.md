# Work model routing

For this project, Codex may plan, implement, run local tools, write reports, and perform Git operations directly in the current chat. Do not route general work through `online/work_api.py` or require API-generated instructions. This is the user's persistent preference from 2026-11-03 and applies to future project work without asking again.

The evaluation judge may continue to use its configured API. Keep its protected credential, locked route, model, and streaming safeguards. Real pre/test cases still use their business endpoints and authenticated internal Trace; a text completion is not evidence of a business test. Never put credentials, tokens, OTPs, or raw authentication material in prompts, command output, reports, or Git. Report only operations supported by actual tool results.

Persistent pre-login safety requirements remain in `.cursor/rules/pre-login-policy.mdc`.
