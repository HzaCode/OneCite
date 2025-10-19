#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OneCite MCP Server - Official MCP SDK Implementation
使用官方Python SDK实现的MCP服务器
"""

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from onecite import process_references

# 创建服务器实例
server = Server("onecite")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出可用的工具"""
    return [
        Tool(
            name="cite",
            description="Generate academic citations from DOI, arXiv, titles, or URLs",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source of the literature (DOI, arXiv ID, paper title, or URL)"
                    },
                    "style": {
                        "type": "string",
                        "description": "Citation format",
                        "enum": ["bibtex", "apa", "mla"],
                        "default": "bibtex"
                    }
                },
                "required": ["source"]
            }
        ),
        Tool(
            name="batch_cite",
            description="Generate citations for multiple sources at once",
            inputSchema={
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
                        "enum": ["bibtex", "apa", "mla"],
                        "default": "bibtex"
                    }
                },
                "required": ["sources"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    if name == "cite":
        source = arguments["source"]
        style = arguments.get("style", "bibtex")
        
        # 处理引用
        result = process_references(
            input_content=source,
            input_type="txt",
            template_name="journal_article_full",
            output_format=style,
            interactive_callback=lambda candidates: 0  # 自动选择第一个
        )
        
        if result["results"]:
            return [TextContent(
                type="text",
                text=result["results"][0]
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Failed to generate citation. Error: {result['report']}"
            )]
    
    elif name == "batch_cite":
        sources = arguments["sources"]
        style = arguments.get("style", "bibtex")
        
        # 批量处理
        all_sources = "\n\n".join(sources)
        result = process_references(
            input_content=all_sources,
            input_type="txt",
            template_name="journal_article_full",
            output_format=style,
            interactive_callback=lambda candidates: 0
        )
        
        citations = "\n\n".join(result["results"])
        return [TextContent(
            type="text",
            text=citations
        )]
    
    raise ValueError(f"Unknown tool: {name}")


async def async_main():
    """异步启动服务器"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """命令行入口点"""
    import asyncio
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

