# Security and guardrails

## Trust boundaries

- The request schema constrains query length; graph validation rejects empty input, control characters, and explicit attempts to override system rules, extract credentials/system prompts, bypass permissions, or execute arbitrary commands.
- Retrieved passages are validated for source IDs, length, and control characters. Instruction override, exfiltration, tool-abuse, and command-execution patterns are rejected before generation or Python analysis. Rejected passages are shown in the retrieval activity summary only as a count.
- LLM prompts label document passages and memory as untrusted context. Memory may resolve references but cannot support factual claims; retrieved evidence remains mandatory.
- Tool arguments are constrained by Pydantic and checked again at execution. Each protected tool checks server-resolved role permissions immediately before work.
- Output is capped, token-like secrets are redacted, and citations are checked against the exact retrieved document IDs. Invalid citations are removed individually; if a grounded response omitted all citations, a cited extractive fallback is used.

## Demonstration limits

The injection detector uses small phrase-pattern rules. It can miss novel or obfuscated attacks and can reject benign passages that contain similar wording. It is one defense layer, not a guarantee. Review logs and rejected passage counts; replace demo tokens and add a production identity provider before deployment. The system does not claim to prevent every prompt injection.
