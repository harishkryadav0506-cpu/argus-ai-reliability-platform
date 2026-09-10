"""
ARGUS MCP Server & Tool Registry (Phase 6 - Section 12)

Provides unified discovery and execution for all Model Context Protocol (MCP) tools:
- READ Tools: Telemetry, health, logs, deployment history, and runbooks.
- ACTION Tools: Rollback, restarts, model switches, vector reindexing, and incident lifecycle.
"""
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from app.mcp import metrics_tools, logs_tools, deployment_tools, incident_tools
from app.logging_config import log_structured_event

logger = logging.getLogger(__name__)


class ToolDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        tool_type: str,  # "READ" | "ACTION"
        risk_level: str,  # "low" | "medium" | "high"
        func: Callable[..., Any],
        parameters_schema: Dict[str, Any],
    ):
        self.name = name
        self.description = description
        self.tool_type = tool_type
        self.risk_level = risk_level
        self.func = func
        self.parameters_schema = parameters_schema

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "type": self.tool_type,
            "risk_level": self.risk_level,
            "inputSchema": self.parameters_schema,
        }


class MCPServer:
    """
    Central MCP Server managing tool registry, security policy enforcement, and execution.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_all_tools()

    def _register_tool(
        self,
        name: str,
        description: str,
        tool_type: str,
        risk_level: str,
        func: Callable[..., Any],
        parameters_schema: Dict[str, Any],
    ):
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            tool_type=tool_type,
            risk_level=risk_level,
            func=func,
            parameters_schema=parameters_schema,
        )

    def _register_all_tools(self):
        # 1. READ Tools
        self._register_tool(
            name="get_system_metrics",
            description="Returns current system metrics and historical window summary.",
            tool_type="READ",
            risk_level="low",
            func=metrics_tools.get_system_metrics,
            parameters_schema={
                "type": "object",
                "properties": {"window_minutes": {"type": "integer", "default": 15}},
            },
        )
        self._register_tool(
            name="get_service_health",
            description="Queries health and availability status of system components.",
            tool_type="READ",
            risk_level="low",
            func=metrics_tools.get_service_health,
            parameters_schema={
                "type": "object",
                "properties": {"service_name": {"type": "string"}},
            },
        )
        self._register_tool(
            name="get_recent_logs",
            description="Returns recent structured log entries filtered by service and level.",
            tool_type="READ",
            risk_level="low",
            func=logs_tools.get_recent_logs,
            parameters_schema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                    "level": {"type": "string"},
                },
            },
        )
        self._register_tool(
            name="get_incident_history",
            description="Queries past incidents and resolutions.",
            tool_type="READ",
            risk_level="low",
            func=logs_tools.get_incident_history,
            parameters_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10},
                    "status": {"type": "string"},
                },
            },
        )
        self._register_tool(
            name="get_deployment_history",
            description="Returns recent deployment revisions and build tags.",
            tool_type="READ",
            risk_level="low",
            func=logs_tools.get_deployment_history,
            parameters_schema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        )
        self._register_tool(
            name="search_runbooks",
            description="Semantic search over the operational runbook knowledge base.",
            tool_type="READ",
            risk_level="low",
            func=logs_tools.search_runbooks,
            parameters_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "default": 3},
                    "failure_type": {"type": "string"},
                },
                "required": ["query"],
            },
        )

        # 2. ACTION Tools
        self._register_tool(
            name="simulate_rollback",
            description="Simulates counterfactual outcome and recovery probability of rolling back a service.",
            tool_type="ACTION",
            risk_level="low",
            func=deployment_tools.simulate_rollback,
            parameters_schema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "target_revision": {"type": "string"},
                    "incident_id": {"type": "string"},
                },
                "required": ["service_name", "target_revision"],
            },
        )
        self._register_tool(
            name="execute_rollback",
            description="Rolls back a service to a previous stable revision (High Risk - Requires approved=True).",
            tool_type="ACTION",
            risk_level="high",
            func=deployment_tools.execute_rollback,
            parameters_schema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "target_revision": {"type": "string"},
                    "approved": {"type": "boolean", "default": False},
                    "incident_id": {"type": "string"},
                },
                "required": ["service_name", "target_revision"],
            },
        )
        self._register_tool(
            name="restart_service",
            description="Restarts a service and re-establishes connection pools (High Risk - Requires approved=True).",
            tool_type="ACTION",
            risk_level="high",
            func=deployment_tools.restart_service,
            parameters_schema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string"},
                    "approved": {"type": "boolean", "default": False},
                    "incident_id": {"type": "string"},
                },
                "required": ["service_name"],
            },
        )
        self._register_tool(
            name="switch_model",
            description="Switches the active LLM provider model to a fallback deployment.",
            tool_type="ACTION",
            risk_level="medium",
            func=deployment_tools.switch_model,
            parameters_schema={
                "type": "object",
                "properties": {
                    "target_provider": {"type": "string", "default": "gemini"},
                    "model": {"type": "string", "default": "gemini-2.0-flash"},
                    "fallback": {"type": "boolean", "default": True},
                    "approved": {"type": "boolean", "default": True},
                    "incident_id": {"type": "string"},
                },
            },
        )
        self._register_tool(
            name="reindex_vector_store",
            description="Rebuilds the vector database collection from source knowledge base.",
            tool_type="ACTION",
            risk_level="medium",
            func=deployment_tools.reindex_vector_store,
            parameters_schema={
                "type": "object",
                "properties": {
                    "collection": {"type": "string", "default": "runbooks"},
                    "force_clean": {"type": "boolean", "default": True},
                    "approved": {"type": "boolean", "default": True},
                    "incident_id": {"type": "string"},
                },
            },
        )
        self._register_tool(
            name="create_incident",
            description="Creates a new incident record in the system.",
            tool_type="ACTION",
            risk_level="low",
            func=incident_tools.create_incident,
            parameters_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "severity": {"type": "string", "default": "medium"},
                    "failure_type": {"type": "string", "default": "UNKNOWN"},
                    "description": {"type": "string"},
                    "incident_id": {"type": "string"},
                },
                "required": ["title"],
            },
        )
        self._register_tool(
            name="update_incident",
            description="Updates an incident's status and resolution details.",
            tool_type="ACTION",
            risk_level="low",
            func=incident_tools.update_incident,
            parameters_schema={
                "type": "object",
                "properties": {
                    "incident_id": {"type": "string"},
                    "status": {"type": "string"},
                    "resolution_notes": {"type": "string"},
                },
                "required": ["incident_id"],
            },
        )

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Returns all registered tools in MCP standard format.
        """
        return [t.to_dict() for t in self._tools.values()]

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a registered tool with argument binding and security enforcement.
        """
        arguments = arguments or {}
        tool_def = self.get_tool(name)
        if not tool_def:
            return {
                "tool": name,
                "type": "UNKNOWN",
                "risk_level": "low",
                "status": "error",
                "error": f"Tool '{name}' not found. Available tools: {list(self._tools.keys())}",
            }

        t0 = time.time()
        try:
            # Check function signature and pass supported arguments
            sig = inspect.signature(tool_def.func)
            kwargs = {}
            for param_name, param in sig.parameters.items():
                if param_name in arguments:
                    kwargs[param_name] = arguments[param_name]
                elif param.default is not inspect.Parameter.empty:
                    kwargs[param_name] = param.default

            # If raise_on_blocked is accepted by the action tool, specify False for unified MCP JSON response
            if "raise_on_blocked" in sig.parameters:
                kwargs["raise_on_blocked"] = False

            result = tool_def.func(**kwargs)
            duration = time.time() - t0
            inc_id = arguments.get("incident_id")
            log_structured_event(
                logger,
                f"MCP tool '{name}' executed successfully",
                agent="mcp_server",
                action=name,
                status="success",
                incident_id=inc_id,
                duration=duration,
            )
            return result
        except PermissionError as pe:
            duration = time.time() - t0
            inc_id = arguments.get("incident_id")
            log_structured_event(
                logger,
                f"MCP tool '{name}' execution blocked by policy: {pe}",
                agent="mcp_server",
                action=name,
                status="blocked",
                incident_id=inc_id,
                duration=duration,
                level=logging.WARNING,
            )
            return {
                "tool": name,
                "type": tool_def.tool_type,
                "risk_level": tool_def.risk_level,
                "status": "blocked",
                "error": str(pe),
            }
        except Exception as exc:
            duration = time.time() - t0
            inc_id = arguments.get("incident_id")
            log_structured_event(
                logger,
                f"Error executing MCP tool '{name}': {exc}",
                agent="mcp_server",
                action=name,
                status="error",
                incident_id=inc_id,
                duration=duration,
                level=logging.ERROR,
            )
            return {
                "tool": name,
                "type": tool_def.tool_type,
                "risk_level": tool_def.risk_level,
                "status": "error",
                "error": str(exc),
            }


# Singleton server instance
_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
    return _mcp_server


def call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return get_mcp_server().call_tool(name, arguments)


def list_tools() -> List[Dict[str, Any]]:
    return get_mcp_server().list_tools()
