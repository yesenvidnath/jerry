# Fictional Payments Incident: Duplicate Authorization

Document ID: INC-2025-022
Department: Payments
Type: Incident report
Access: Internal
Created: 2025-05-03

A partner timeout caused clients to retry authorization requests without a stable idempotency key. A small number of customers saw duplicate pending authorizations. The team enabled stricter idempotency validation and coordinated reversal of duplicate holds. Root causes included inconsistent client retry behavior and missing alerting for duplicate request identifiers. Prevention: require idempotency keys on write requests and test retries in the partner certification environment.
