from typing import Sequence, List, Optional, Dict, Any
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.shared.exceptions import McpError

from pydantic import BaseModel

import requests

class ScalewayTools(str):
    LIST_INSTANCES = "list_instances"
    GET_INSTANCE = "get_instance"
    PERFORM_ACTION = "perform_action"


class Instance(BaseModel):
    id: str
    name: str
    state: str
    commercial_type: str
    private_ip: Optional[str] = None
    zone: str
    tags: List[str] = []


class ListInstancesResponse(BaseModel):
    instances: List[Instance]
    total_count: int


class InstanceDetailResponse(BaseModel):
    instance: Instance


class Task(BaseModel):
    id: str
    description: str
    progress: int
    started_at: Optional[str] = None
    terminated_at: Optional[str] = None
    status: str
    href_from: Optional[str] = None
    href_result: Optional[str] = None
    zone: str


class ActionResponse(BaseModel):
    task: Task


class ScalewayServer:
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.base_url = "https://api.scaleway.com"
        self.headers = {
            "X-Auth-Token": auth_token,
            "Content-Type": "application/json"
        }

    def list_instances(self, zone: str, per_page: int = 50, page: int = 1, 
                      project: Optional[str] = None, state: str = "running") -> ListInstancesResponse:
        """List instances in a specific availability zone"""
        url = f"{self.base_url}/instance/v1/zones/{zone}/servers"
        
        params = {
            "per_page": per_page,
            "page": page,
            "state": state
        }
        
        if project:
            params["project"] = project
            
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        instances = []
        
        for server in data.get("servers", []):
            instances.append(Instance(
                id=server.get("id", ""),
                name=server.get("name", ""),
                state=server.get("state", ""),
                commercial_type=server.get("commercial_type", ""),
                private_ip=server.get("private_ip"),
                zone=server.get("zone", ""),
                tags=server.get("tags", [])
            ))
            
        return ListInstancesResponse(
            instances=instances,
            total_count=len(instances)
        )

    def get_instance(self, zone: str, server_id: str) -> InstanceDetailResponse:
        """Get details of a specific instance"""
        url = f"{self.base_url}/instance/v1/zones/{zone}/servers/{server_id}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        data = response.json()
        server = data.get("server", {})
        
        instance = Instance(
            id=server.get("id", ""),
            name=server.get("name", ""),
            state=server.get("state", ""),
            commercial_type=server.get("commercial_type", ""),
            private_ip=server.get("private_ip"),
            zone=server.get("zone", ""),
            tags=server.get("tags", [])
        )
            
        return InstanceDetailResponse(instance=instance)

    def perform_action(self, zone: str, server_id: str, action: str, 
                      name: Optional[str] = None, volumes: Optional[Dict[str, Any]] = None,
                      disable_ipv6: Optional[bool] = None) -> ActionResponse:
        """Perform an action on a specific instance"""
        url = f"{self.base_url}/instance/v1/zones/{zone}/servers/{server_id}/action"
        
        payload = {"action": action}
        
        # Add optional parameters if provided
        if name is not None and action == "backup":
            payload["name"] = name
            
        if volumes is not None and action == "backup":
            payload["volumes"] = volumes
            
        if disable_ipv6 is not None and action == "enable_routed_ip":
            payload["disable_ipv6"] = disable_ipv6
            
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        task_data = data.get("task", {})
        
        task = Task(
            id=task_data.get("id", ""),
            description=task_data.get("description", ""),
            progress=task_data.get("progress", 0),
            started_at=task_data.get("started_at"),
            terminated_at=task_data.get("terminated_at"),
            status=task_data.get("status", ""),
            href_from=task_data.get("href_from"),
            href_result=task_data.get("href_result"),
            zone=task_data.get("zone", "")
        )
            
        return ActionResponse(task=task)


async def serve(auth_token: str) -> None:
    server = Server("mcp-scaleway")
    scaleway_server = ScalewayServer(auth_token)



    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Scaleway tools."""
        return [
            Tool(
                name=ScalewayTools.LIST_INSTANCES,
                description="List instances in a specific Scaleway availability zone",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "zone": {
                            "type": "string",
                            "description": "Availability zone (e.g., fr-par-1, fr-par-2, fr-par-3, nl-ams-1, pl-waw-1, ...)",
                            "enum": ["fr-par-1", "fr-par-2", "fr-par-3", "nl-ams-1", "nl-ams-2", "nl-ams-3", "pl-waw-1", "pl-waw-2", "pl-waw-3"]
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Number of items per page (max 100)",
                            "default": 50
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number",
                            "default": 1
                        },
                        "project": {
                            "type": "string",
                            "description": "Filter by project ID (optional)"
                        },
                        "state": {
                            "type": "string",
                            "description": "Instance state filter",
                            "default": "running",
                            "enum": ["running", "stopped", "stopped in place"]
                        }
                    },
                    "required": ["zone"],
                },
            ),
            Tool(
                name=ScalewayTools.GET_INSTANCE,
                description="Get details of a specific Scaleway instance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "zone": {
                            "type": "string",
                            "description": "Availability zone (e.g., fr-par-1, fr-par-2, fr-par-3, nl-ams-1, pl-waw-1, ...)",
                            "enum": ["fr-par-1", "fr-par-2", "fr-par-3", "nl-ams-1", "nl-ams-2", "nl-ams-3", "pl-waw-1", "pl-waw-2", "pl-waw-3"]
                        },
                        "server_id": {
                            "type": "string",
                            "description": "UUID of the instance you want to get details for",
                        }
                    },
                    "required": ["zone", "server_id"],
                },
            ),
            Tool(
                name=ScalewayTools.PERFORM_ACTION,
                description="Perform an action on a Scaleway instance (poweron, poweroff, reboot, etc.)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "zone": {
                            "type": "string",
                            "description": "Availability zone (e.g., fr-par-1, fr-par-2, fr-par-3, nl-ams-1, pl-waw-1, ...)",
                            "enum": ["fr-par-1", "fr-par-2", "fr-par-3", "nl-ams-1", "nl-ams-2", "nl-ams-3", "pl-waw-1", "pl-waw-2", "pl-waw-3"]
                        },
                        "server_id": {
                            "type": "string",
                            "description": "UUID of the instance you want to perform an action on",
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to perform on the instance (e.g. poweron, poweroff, reboot, ...)",
                            "default": "poweron",
                            "enum": ["poweron", "poweroff", "stop_in_place", "reboot", "backup", "terminate", "enable_routed_ip"]
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the backup (only for backup action)"
                        },
                        "volumes": {
                            "type": "object",
                            "description": "For each volume UUID, the snapshot parameters (only for backup action)",
                            "additionalProperties": {}
                        },
                        "disable_ipv6": {
                            "type": "boolean",
                            "description": "Disable IPv6 on the instance (only for enable_routed_ip action)",
                        }
                    },
                    "required": ["zone", "server_id", "action"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for Scaleway API operations."""

        print (name, arguments)
        try:
            match name:
                case ScalewayTools.LIST_INSTANCES:
                    if "zone" not in arguments:
                        raise ValueError("Missing required argument: zone")

                    zone = arguments["zone"]
                    per_page = arguments.get("per_page", 50)
                    page = arguments.get("page", 1)
                    project = arguments.get("project")
                    state = arguments.get("state", "running")
                    
                    result = scaleway_server.list_instances(
                        zone=zone,
                        per_page=per_page,
                        page=page,
                        project=project,
                        state=state
                    )

                case ScalewayTools.GET_INSTANCE:
                    if not all(k in arguments for k in ["zone", "server_id"]):
                        raise ValueError("Missing required arguments: zone and/or server_id")

                    zone = arguments["zone"]
                    server_id = arguments["server_id"]
                    
                    result = scaleway_server.get_instance(
                        zone=zone,
                        server_id=server_id
                    )
                    
                case ScalewayTools.PERFORM_ACTION:
                    if not all(k in arguments for k in ["zone", "server_id", "action"]):
                        raise ValueError("Missing required arguments: zone, server_id, and/or action")

                    zone = arguments["zone"]
                    server_id = arguments["server_id"]
                    action = arguments["action"]
                    name = arguments.get("name")
                    volumes = arguments.get("volumes")
                    disable_ipv6 = arguments.get("disable_ipv6")
                    
                    result = scaleway_server.perform_action(
                        zone=zone,
                        server_id=server_id,
                        action=action,
                        name=name,
                        volumes=volumes,
                        disable_ipv6=disable_ipv6
                    )
                    
                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [
                TextContent(type="text", text=json.dumps(result.model_dump(), indent=2))
            ]

        except requests.exceptions.RequestException as e:
            raise McpError(f"API request error: {str(e)}")
        except Exception as e:
            raise McpError(f"Error processing Scaleway operation: {str(e)}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    import os
    import asyncio
    from dotenv import load_dotenv

    load_dotenv()
    
    auth_token = os.getenv("SCW_SECRET_KEY") 
    if not auth_token:
        print("Error: SCW_SECRET_KEY environment variable is required")
        exit(1)
        
    asyncio.run(serve(auth_token))