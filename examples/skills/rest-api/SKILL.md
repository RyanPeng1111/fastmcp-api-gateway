---
description: Guidance for using the Spring Boot REST API safely and efficiently.
---

# REST API guidance

- Prefer read-only GET tools before calling tools that change data.
- Use identifiers returned by lookup tools instead of guessing identifiers.
- When the backend returns 401 or 403, do not retry with altered credentials; tell the user that authentication or authorization failed.
- Do not place authentication values inside tool arguments. Authentication is carried in request headers.

