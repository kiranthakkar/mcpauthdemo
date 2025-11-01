from fastmcp import Client
import asyncio

async def main():
    # The client will automatically handle OCI OAuth flows
    async with Client("http://localhost:8000/mcp/", auth="oauth") as client:
        # First-time connection will open OCI login in your browser
        print("✓ Authenticated with OCI IAM")

        tools = await client.list_tools()
        print(f"🔧 Available tools ({len(tools)}):")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")

        result = await client.call_tool("get_os_namespace", {'region': 'us-sanjose-1'})
        print(f"Oracle Object Storage Namespace: {result}")
        
        result = await client.call_tool("whoami", {})
        print(f"Whoami Tool Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
