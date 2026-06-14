from app.agent.base_agent import BaseAgent
from typing import Any
from app.schemas.agent_input import AgentInput
from app.schemas.agent_output import AgentOutput
from app.schemas.model_request import ModelRequest
from app.tools.tool_registry import ToolRegistry
from app.models.base_model import BaseModel
from app.schemas.tool_input import ToolInput
from app.schemas.tool_output import ToolOutput
from app.memory.base_memory import BaseMemory
from datetime import datetime
from app.prompts.prompt_builder import PromptBuilder
from app.prompts.base_prompt import BasePrompt
from app.planners.base_planner import BasePlanner
from app.runtime.runtime_session import RuntimeSession
from app.workflows.agent_executor import AgentExecutor
from app.workflows.workflow_runner_registry import get_workflow_runner
from app.workflows.workflow_steps import flatten_steps_for_trace
from app.runtime.runtime_manager import RuntimeManager
from app.schemas.collaboration import deliverable_dict


class ChatAgent(BaseAgent):
    def __init__(
        self,
        runtime_manager: RuntimeManager,
        model: BaseModel = None,
        tool_registry: ToolRegistry = None,
        memory: BaseMemory | None = None,
        prompt_builder: BasePrompt | None = None,
        planner: BasePlanner | None = None,
        **kwargs,
    ) -> None:
        super().__init__(model = model,**kwargs)
        self._tool_registry = tool_registry
        self._memory = memory
        self._prompt_builder = prompt_builder if prompt_builder is not None else PromptBuilder()
        self._planner = planner
        self._runtime_manager = runtime_manager


    def _add_memory_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        if self._memory is None or not session_id:
            return
        self._memory.add_message(
            session_id,
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def _finalize_model_output(
        self,
        model_output: AgentOutput,
        prompt_text: str | None,
        runtime_session: RuntimeSession,
    ) -> AgentOutput:
        runtime_session.add_model_call(
            prompt=prompt_text or "",
            success=model_output.success,
            output=model_output.content,
            error=model_output.error_message,
        )
        if not model_output.success:
            runtime_session.add_error(
                f"model call error: {model_output.error_message}"
            )
        runtime_session.final_output = model_output.content or ""
        model_output.metadata = self._build_output_metadata(
            model_output.metadata,
            runtime_session,
        )
        return model_output

    def _run_workflow(
        self,
        plan: dict[str, Any],
        runtime_session: RuntimeSession,
    ) -> AgentOutput:
        workflow_runner = get_workflow_runner(plan.get("workflow_kind"))
        agent_executor = AgentExecutor(
            model=self._model,
            tool_registry=self._tool_registry,
        )
        workflow_output = workflow_runner.run(
            steps=plan.get("steps", []),
            executor=agent_executor,
            context=plan.get("context", {}),
        )
        merged_output = dict(workflow_output)
        merged_output["runner_class"] = workflow_runner.__class__.__name__
        runtime_session.workflow_result = merged_output
        workflow_output = merged_output
        results = workflow_output.get("results", [])
        flat_steps = flatten_steps_for_trace(plan.get("steps", []))
        for result in results:
            step_name = result.get("step_name", "unknown")
            for step in flat_steps:
                if step.get("step_name", "unknown") == step_name:
                    action = result.get("action", step.get("action", "unknown"))
                    agent_role = step.get("agent_role")
                    trace_extra: dict[str, Any] | None = None
                    if result.get("parallel_fan_out"):
                        trace_extra = {"parallel_fan_out": True}
                    runtime_session.add_workflow_step_trace(
                        step_name=result.get("step_name", "unknown"),
                        action=action,
                        success=result.get("success", False),
                        output=result.get("output", ""),
                        input_summary=result.get("input_summary", ""),
                        output_summary=result.get("output_summary", ""),
                        error=result.get("error", None),
                        agent_role=agent_role if agent_role else None,
                        extra=trace_extra,
                    )
                    if agent_role:
                        runtime_session.add_collaboration_event(
                            agent_role=str(agent_role),
                            phase=str(step.get("step_name", step_name)),
                            summary=str(
                                result.get("output_summary") or result.get("output") or ""
                            )[:800],
                            step_name=step_name,
                        )
                    if action == "tool":
                        runtime_session.add_tool_call(
                            tool_name=step.get("tool_name", "unknown"),
                            success=result.get("success", False),
                            output=result.get("output", ""),
                            error=result.get("error", None),
                        )
                        step_meta = result.get("metadata") or {}
                        pack = step_meta.get("deliverable")
                        if pack:
                            runtime_session.add_deliverable(pack)
                    elif action == "model":
                        prompt_template = step.get("prompt_template", "")
                        use_step_result = step.get("use_step_result")
                        use_step_result_keys = step.get("use_step_result_keys")
                        finally_prompt = step.get("prompt", "")
                        if (
                            not finally_prompt
                            and use_step_result_keys
                            and prompt_template
                        ):
                            merge_parts: dict[str, Any] = {}
                            keys_list = use_step_result_keys
                            if isinstance(keys_list, list):
                                for kn in keys_list:
                                    ks = str(kn)
                                    for previous_result in results:
                                        if previous_result.get("step_name") == ks:
                                            merge_parts[ks] = previous_result.get(
                                                "output", ""
                                            )
                                            break
                                try:
                                    finally_prompt = prompt_template.format(
                                        **merge_parts
                                    )
                                except KeyError:
                                    finally_prompt = prompt_template
                        elif not finally_prompt and use_step_result:
                            dependency_output = ""
                            for previous_result in results:
                                if previous_result.get("step_name") == use_step_result:
                                    dependency_output = previous_result.get(
                                        "output", ""
                                    )
                                    finally_prompt = prompt_template.replace(
                                        "{step_output}", str(dependency_output)
                                    )
                                    break

                        runtime_session.add_model_call(
                            prompt=finally_prompt or "",
                            success=result.get("success", False),
                            output=result.get("output", ""),
                            error=result.get("error", None),
                        )

        final_step_name = plan.get("final_step_name")
        if final_step_name:
            final_result = {}
            for r in results:
                if r.get("step_name") == final_step_name:
                    final_result = r
                    break
            if not final_result and results:
                final_result = results[-1]
        else:
            final_result = results[-1] if results else {}
        runtime_session.final_output = final_result.get("output", "")
        wf_name = plan.get("workflow_name")
        if workflow_output.get("success") and wf_name == "research_team_workflow":
            summary_text = (runtime_session.final_output or "")[:2000]
            runtime_session.add_deliverable(
                deliverable_dict(
                    "text",
                    title="协作研究报告",
                    summary=summary_text,
                )
            )
        if workflow_output.get("success") and wf_name in (
            "multi_module_parallel_workflow",
            "multi_module_parallel_ffmpeg_workflow",
            "parallel_pillar_workflow",
            "parallel_pillar_ffmpeg_workflow",
        ):
            merge_step = plan.get("final_step_name") or "merge_coordination"
            merged_text = ""
            for r in results:
                if r.get("step_name") == merge_step:
                    merged_text = str(r.get("output") or "")
                    break
            title = (
                "三线并行交付说明"
                if str(wf_name).startswith("parallel_pillar")
                else "多模块并行交付说明"
            )
            runtime_session.add_deliverable(
                deliverable_dict(
                    "text",
                    title=title,
                    summary=merged_text[:2000],
                )
            )
        if workflow_output.get("success") and wf_name == "research_team_ffmpeg_workflow":
            writeup_text = ""
            for r in results:
                if r.get("step_name") == "writeup":
                    writeup_text = str(r.get("output") or "")
                    break
            runtime_session.add_deliverable(
                deliverable_dict(
                    "text",
                    title="协作研究报告",
                    summary=writeup_text[:2000],
                )
            )
        self._add_memory_message(
            runtime_session.session_id,
            "assistant",
            runtime_session.final_output,
        )
        if not workflow_output.get("success", False):
            runtime_session.add_error(workflow_output.get("error", ""))
        if not final_result.get("success", False):
            runtime_session.add_error(final_result.get("error", ""))
        return AgentOutput(
            content=runtime_session.final_output,
            success=workflow_output.get("success", False),
            error_message=workflow_output.get("error", "")
            or final_result.get("error", ""),
            metadata=self._build_output_metadata(
                workflow_output.get("metadata", {}),
                runtime_session,
            ),
        )

    def _build_output_metadata(
        self,
        metadata: dict[str, Any] | None,
        runtime_session: RuntimeSession,
    ) -> dict[str, Any]:
        merged_metadata = dict(metadata or {})
        merged_metadata["runtime_session"] = runtime_session
        return merged_metadata

    def call_tool(self,tool_name:str,tool_input:ToolInput)->ToolOutput:
        if self._tool_registry is None:
            return ToolOutput(content= None,error_message="tool registry is not configured",success=False)
        tool = self._tool_registry.get_tool(tool_name)
        if tool is not None:
            return tool.run(tool_input)
        return ToolOutput(content= None,error_message=f"tool not found: {tool_name}",success=False)

    def call_model(self, input_data: AgentInput) -> tuple[AgentOutput, str | None]:
        if self._memory is not None and input_data.session_id:
            prompt_text = self._prompt_builder.build_prompt(messages=self._memory.get_messages(input_data.session_id))
            model_request = ModelRequest(prompt = prompt_text)
            model_response = self._model.generate(model_request)
            self._add_memory_message(
                input_data.session_id,
                "assistant",
                model_response.content or "",
            )
            return AgentOutput(
                content=model_response.content or "",
                success=model_response.success,
                error_message=model_response.error_message,
                metadata=model_response.metadata,
            ), prompt_text
        else:
            prompt_text = self._prompt_builder.build_prompt(messages=[], current_input=input_data.message)
            model_request = ModelRequest(prompt = prompt_text)
            model_response = self._model.generate(model_request)
            return AgentOutput(
                content=model_response.content or "",
                success=model_response.success,
                error_message=model_response.error_message,
                metadata=model_response.metadata,
            ), prompt_text

    def _record_turn(
        self,
        session_id: str,
        entry_type: str,
        runtime_session: RuntimeSession,
        user_input: str,
        final_output: str,
        success: bool,
    ) -> None:
        self._runtime_manager.ensure_session_exists(session_id)
        self._runtime_manager.append_transcript_entry(
            session_id=session_id,
            transcript_entry=self._runtime_manager.build_transcript_entry(
                type=entry_type,
                runtime_session=runtime_session,
                user_input=user_input,
                final_output=final_output,
                success=success,
            ),
        )

    def act(self, input_data: AgentInput) -> AgentOutput:

        runtime_session = self._runtime_manager.create_runtime_session(
            session_id=input_data.session_id, user_input=input_data.message
        )
        task_id = input_data.metadata.get("task_id")
        if task_id:
            runtime_session.task_id = str(task_id)
        self._add_memory_message(
            input_data.session_id,
            "user",
            input_data.message,
        )
        if self._planner is not None:
            plan = self._planner.plan(input_data)
            runtime_session.planner_result = plan
            runtime_session.add_workflow_step_trace(
                step_name="planner",
                action=plan.get("action", "unknown"),
                success=True,
                output=plan,
                error=None,
                input_summary=input_data.message,
                output_summary=plan.get("reason", ""),
            )
            if plan.get("action") == "workflow":
                agent_output = self._run_workflow(plan, runtime_session)
                self._record_turn(
                    input_data.session_id,
                    entry_type="agent",
                    runtime_session=runtime_session,
                    user_input=input_data.message,
                    final_output=agent_output.content,
                    success=agent_output.success,
                )
                return agent_output
            elif plan.get("action") == "tool":
                tool_name = plan.get("tool_name")
                if tool_name is not None:
                    tool_output = self.call_tool(tool_name, ToolInput(params={}))
                    runtime_session.add_tool_call(
                        tool_name=tool_name,
                        success=tool_output.success,
                        output=tool_output.content,
                        error=tool_output.error_message,
                    )
                    self._add_memory_message(
                        input_data.session_id,
                        "assistant",
                        tool_output.content or "",
                    )
                    runtime_session.final_output = tool_output.content or ""
                    if not tool_output.success:
                        runtime_session.add_error(
                            f"tool call error: {tool_output.error_message}"
                        )

                    agent_output = AgentOutput(
                        content=tool_output.content or "",
                        success=tool_output.success,
                        error_message=tool_output.error_message,
                        metadata=self._build_output_metadata(
                            tool_output.metadata,
                            runtime_session,
                        ),
                    )
                    self._record_turn(
                        input_data.session_id,
                        entry_type="agent",
                        runtime_session=runtime_session,
                        user_input=input_data.message,
                        final_output=agent_output.content,
                        success=agent_output.success,
                    )
                    return agent_output
                else:
                    model_output, prompt_text = self.call_model(input_data)
                    agent_output = self._finalize_model_output(
                        model_output,
                        prompt_text,
                        runtime_session,
                    )
                    self._record_turn(
                        input_data.session_id,
                        entry_type="agent",
                        runtime_session=runtime_session,
                        user_input=input_data.message,
                        final_output=agent_output.content,
                        success=agent_output.success,
                    )
                    return agent_output

            else:
                model_output, prompt_text = self.call_model(input_data)
                agent_output = self._finalize_model_output(
                    model_output,
                    prompt_text,
                    runtime_session,
                )
                self._record_turn(
                    input_data.session_id,
                    entry_type="agent",
                    runtime_session=runtime_session,
                    user_input=input_data.message,
                    final_output=agent_output.content,
                    success=agent_output.success,
                )
                return agent_output
        else:
            model_output, prompt_text = self.call_model(input_data)
            agent_output = self._finalize_model_output(
                model_output,
                prompt_text,
                runtime_session,
            )
            self._record_turn(
                input_data.session_id,
                entry_type="agent",
                runtime_session=runtime_session,
                user_input=input_data.message,
                final_output=agent_output.content,
                success=agent_output.success,
            )
            return agent_output
