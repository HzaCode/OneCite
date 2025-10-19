#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
OneCite MCP Server
MCP server for integration with MCP clients like editor client/MCP client
"""

import json
import sys
import asyncio
from typing import Any, Dict, List, Optional
import logging

from onecite import process_references, PipelineController
from onecite.exceptions import OneCiteError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OneCiteMCPServer:
    """OneCite MCP server implementation"""
    
    def __init__(self):
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, Any]:
        """Register available tools"""
        return {
            "cite": {
                "description": "Generate academic citations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source": {
                            "type": "string",
                            "description": "Source of the literature (DOI, URL, title, etc.)"
                        },
                        "style": {
                            "type": "string",
                            "description": "Citation format (APA, MLA, Chicago, etc.)",
                            "default": "APA"
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format (text, bibtex, json)",
                            "default": "text"
                        }
                    },
                    "required": ["source"]
                }
            },
            "batch_cite": {
                "description": "Batch generate citations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of literature sources"
                        },
                        "style": {
                            "type": "string",
                            "description": "Citation format",
                            "default": "APA"
                        }
                    },
                    "required": ["sources"]
                }
            },
            "search": {
                "description": "Search academic literature",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search keywords"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Result count limit",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls"""
        try:
            if tool_name == "cite":
                result = await self._cite(
                    arguments["source"],
                    arguments.get("style", "APA"),
                    arguments.get("format", "text")
                )
            elif tool_name == "batch_cite":
                result = await self._batch_cite(
                    arguments["sources"],
                    arguments.get("style", "APA")
                )
            elif tool_name == "search":
                result = await self._search(
                    arguments["query"],
                    arguments.get("limit", 10)
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _cite(self, source: str, style: str, format: str) -> Any:
        """Generate a single citation"""
        try:
            # Use process_references function to handle citation
            result = process_references(
                input_content=source,
                input_type="txt",
                output_format=style.lower() if style.lower() in ["apa", "mla", "bibtex"] else "bibtex",
                template_name="journal_article_full",
                interactive_callback=lambda candidates: 0  # Choose the first candidate
            )
            
            if result["results"]:
                return {
                    "citation": result["results"][0] if result["results"] else "",
                    "format": format,
                    "success": True,
                    "report": result["report"]
                }
            else:
                return {
                    "citation": "",
                    "format": format,
                    "success": False,
                    "error": "No entries processed",
                    "report": result["report"]
                }
        except Exception as e:
            return {
                "citation": "",
                "format": format,
                "success": False,
                "error": str(e)
            }
    
    async def _batch_cite(self, sources: List[str], style: str) -> List[Any]:
        """Batch generate citations"""
        results = []
        for source in sources:
            citation = await self._cite(source, style, "text")
            results.append(citation)
        return results
    
    async def _search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search literature"""
        # Simplified example
        return [
            {
                "title": f"Example Literature {i+1}",
                "authors": ["Author 1", "Author 2"],
                "year": 2024,
                "doi": f"10.1234/example.{i+1}"
            }
            for i in range(min(limit, 5))
        ]
    
    async def start(self):
        """Start MCP server"""
        logger.info("OneCite MCP server started")
        
        # Send server information
        server_info = {
            "type": "server_info",
            "name": "onecite-mcp",
            "version": "0.0.4",
            "tools": list(self.tools.keys())
        }
        print(json.dumps(server_info))
        sys.stdout.flush()
        
        # Main loop to handle requests
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
                if not line:
                    break
                
                request = json.loads(line.strip())
                
                if request.get("type") == "tool_call":
                    tool_name = request.get("tool")
                    arguments = request.get("arguments", {})
                    
                    result = await self.handle_tool_call(tool_name, arguments)
                    
                    response = {
                        "type": "tool_response",
                        "request_id": request.get("id"),
                        "result": result
                    }
                    print(json.dumps(response))
                    sys.stdout.flush()
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                error_response = {
                    "type": "error",
                    "error": str(e)
                }
                print(json.dumps(error_response))
                sys.stdout.flush()


def main():
    """Main entry point"""
    server = OneCiteMCPServer()
    
    try:
        if sys.platform == "win32":
            # Special handling for Windows platform
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
