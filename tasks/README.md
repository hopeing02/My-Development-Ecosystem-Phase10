# MDE Task Queue

- `pending`: tasks submitted from mobile/GitHub and waiting for execution
- `processing`: tasks claimed by the PC Agent
- `completed`: successfully completed task YAML and result YAML files
- `failed`: failed or recovered task YAML and result YAML files

Task files use the Phase 3 YAML schema implemented by `mde.task.loader`.
