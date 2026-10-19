from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from mde.ai.artifacts import ArtifactError, load_manifest, validate_relative_path
from mde.ai.engine import AIEngine
from mde.workflow.models import WorkflowContext, WorkflowStep
from mde.workflow.registry import CommandRegistry


class AIWorkflowPlugin:
    name = "ai"

    def __init__(self, engine: AIEngine | None = None) -> None:
        self.engine = engine or AIEngine()

    @staticmethod
    def _ai_settings(
        context: WorkflowContext, step: WorkflowStep
    ) -> tuple[str | None, dict[str, Any]]:
        inputs = context.data.get("inputs", {})
        ai_input = inputs.get("ai", {}) if isinstance(inputs, dict) else {}
        if not isinstance(ai_input, dict):
            ai_input = {}
        provider = step.args.get("provider") or ai_input.get("provider")
        artifacts: Any = step.args.get("artifacts") or ai_input.get("artifacts")
        if artifacts is None and isinstance(inputs, dict):
            artifacts = inputs.get("artifacts", [])
        return (str(provider) if provider else None, {"artifacts": artifacts or []})

    def _execute_ai(
        self, action: str, context: WorkflowContext, step: WorkflowStep
    ) -> dict[str, Any]:
        provider, provider_context = self._ai_settings(context, step)
        ai_input = context.data.get("inputs", {}).get("ai", {})
        context_files = (
            ai_input.get("context_files", []) if isinstance(ai_input, dict) else []
        )
        if not isinstance(context_files, list) or len(context_files) > 20:
            raise ArtifactError("ai.context_files must be a list of at most 20 paths.")
        provider_context["files"] = []
        total_size = 0
        for raw in context_files:
            relative = validate_relative_path(str(raw))
            source = context.repository_root.joinpath(*relative.parts).resolve()
            if not source.is_relative_to(context.repository_root.resolve()):
                raise ArtifactError("Context file escapes the repository.")
            if not source.is_file() or source.stat().st_size > 65536:
                raise ArtifactError("Context files must exist and be at most 64KiB.")
            total_size += source.stat().st_size
            if total_size > 262144:
                raise ArtifactError("Context files exceed 256KiB.")
            provider_context["files"].append(
                {
                    "path": relative.as_posix(),
                    "content": source.read_text(encoding="utf-8"),
                }
            )
        if action == "fix" and context.data.get("last_test_log_path"):
            log = Path(context.data["last_test_log_path"]).resolve()
            if not log.is_relative_to(
                context.repository_root.resolve() / "logs" / "tests"
            ):
                raise ArtifactError(
                    "Test log must remain inside repository logs/tests."
                )
            with log.open("rb") as stream:
                stream.seek(max(0, log.stat().st_size - 65536))
                provider_context["test_failure_log"] = stream.read().decode(
                    "utf-8", errors="replace"
                )
        if action == "review":
            source_manifest = self._find_manifest(context)
            if source_manifest is None:
                raise ArtifactError("Review requires generated artifacts.")
            provider_context["artifacts"] = []
            for artifact in load_manifest(source_manifest).get("artifacts", []):
                relative = validate_relative_path(artifact["source_path"])
                source = context.repository_root.joinpath(*relative.parts).resolve()
                if not source.is_relative_to(context.repository_root.resolve()):
                    raise ArtifactError("Review artifact escapes the repository.")
                provider_context["artifacts"].append(
                    {
                        "path": artifact["target_path"],
                        "content": source.read_text(encoding="utf-8"),
                    }
                )
        base_prompt = str(
            step.args.get("prompt")
            or context.data.get("description")
            or context.message
            or step.id
        )
        if action == "fix":
            error = str(context.data.get("last_test_error") or "Unknown test failure")
            attempt = int(context.data.get("fix_attempt", 1))
            prompt = f"{base_prompt}\n\nFix attempt: {attempt}\nTest failure:\n{error}"
        else:
            prompt = base_prompt
        run_id = context.task_id or f"workflow-{context.workflow_name}"
        response, manifest_path = self.engine.execute(
            action=action,
            prompt=prompt,
            repository_root=context.repository_root,
            run_id=run_id,
            step_id=step.id,
            provider_name=provider,
            task_id=context.task_id,
            context=provider_context,
        )
        return {
            "message": response.summary,
            "provider": response.provider,
            "artifact_count": len(response.artifacts),
            "manifest_path": str(manifest_path),
            "metadata": dict(response.metadata),
        }

    def generate(self, context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
        return self._execute_ai("generate", context, step)

    def review(self, context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
        result = self._execute_ai("review", context, step)
        approved = result["metadata"].get("approved")
        if type(approved) is not bool:
            raise ArtifactError(
                "AI review requires an explicit boolean approved verdict."
            )
        if not approved:
            raise ArtifactError("AI review rejected generated changes.")
        source_manifest = self._find_manifest(context)
        if source_manifest is not None:
            result["source_manifest_path"] = str(source_manifest)
        result["approved"] = approved
        return result

    def fix(self, context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
        return self._execute_ai("fix", context, step)

    @staticmethod
    def _find_manifest(context: WorkflowContext) -> Path | None:
        for output in reversed(tuple(context.outputs.values())):
            if not isinstance(output, dict):
                continue
            raw = output.get("source_manifest_path") or output.get("manifest_path")
            if raw:
                path = Path(str(raw))
                if path.is_file():
                    return path
        return None

    def apply(self, context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
        manifest_path = self._find_manifest(context)
        if manifest_path is None:
            raise ArtifactError(
                "No generated AI artifact manifest is available to apply."
            )

        manifest = load_manifest(manifest_path)
        changed_files: list[str] = []
        backup_root = (
            context.repository_root
            / ".mde"
            / "backups"
            / (context.task_id or context.workflow_name)
            / step.id
        )

        for item in manifest.get("artifacts", []):
            if not isinstance(item, dict):
                raise ArtifactError(f"Invalid artifact entry in {manifest_path}")
            target_relative = validate_relative_path(str(item.get("target_path", "")))
            source_relative = validate_relative_path(str(item.get("source_path", "")))
            source = context.repository_root.joinpath(*source_relative.parts)
            target = context.repository_root.joinpath(*target_relative.parts)
            if not source.is_file():
                raise ArtifactError(f"Generated artifact file not found: {source}")

            if target.exists():
                backup = backup_root.joinpath(*target_relative.parts)
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            changed_files.append(target_relative.as_posix())

        return {
            "message": f"Applied {len(changed_files)} generated artifact(s).",
            "manifest_path": str(manifest_path),
            "changed_files": changed_files,
        }

    def register(self, registry: CommandRegistry) -> None:
        registry.register("ai.generate", self.generate)
        registry.register("ai.review", self.review)
        registry.register("ai.fix", self.fix)
        registry.register("docs.generate", self.generate)
        registry.register("change.review", self.review)
        registry.register("change.apply", self.apply)
