# Fictional Payments Incident: Delayed Settlement

Document ID: INC-2025-014
Department: Payments
Type: Incident report
Access: Internal
Created: 2025-02-14

On 2025-02-14, card settlement batches were delayed for 38 minutes after the settlement queue exceeded its configured worker capacity. The primary cause was a retry storm from a downstream bank gateway following intermittent timeouts. Operations increased worker capacity, paused automatic retries, and drained the queue. Follow-up actions: add exponential backoff with jitter, alert at 70% queue utilization, and review gateway timeout thresholds.
