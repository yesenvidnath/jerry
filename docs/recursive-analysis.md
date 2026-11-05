# Recursive analysis path

The RLM-style workflow is routed by the supervisor and implemented as separate graph nodes: `plan_analysis`, `retrieve_analysis_documents`, `analyze_batches`, and `aggregate_analysis`. The plan limits the scope to incident reports, applies a department filter when the request names payments, handles explicit date ranges, uses batches of 3, and caps work at 4 batches (12 retrieved passages maximum).

`tools/analysis.py` contains the deterministic Python batch analysis and aggregation helpers. Each batch reports the documents examined, extracted cause signals, and citations. The aggregate answer includes source document IDs and a transparent note that cause labels are text-pattern indicators. This simplified RLM path is designed to be inspectable and bounded; it does not recursively call a model agent.
