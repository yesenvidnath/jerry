# Payments Service Operations Runbook

Document ID: RUN-PAY-001
Department: Payments
Type: Runbook
Access: Internal
Created: 2025-01-10

For elevated payment latency, check the service dashboard, queue depth, gateway error rate, and recent deploys. If queue depth is rising, verify worker health and downstream gateway status. Do not repeatedly replay a batch until its idempotency status is confirmed. For a sustained gateway outage, engage the on-call payments lead and follow the incident communication procedure. Record the incident identifier, start time, customer impact, mitigation, and recovery time.
