import asyncio
import logging
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Required for DB context
from app.db.prisma_client import prisma

async def main():
    await prisma.connect()
    try:
        from app.services.agent.tools_registry import research_tool
        
        logging.basicConfig(level=logging.INFO)
        print("Running research_tool...")
        
        result = await research_tool(
            query="Deep learning transformers architecture overview",
            user_id="test_user",
            notebook_id="test_notebook",
            material_ids=[]
        )
        
        print("\n--- TOOL RESULT OUTPUT ---")
        print(result["output"])
        print("--------------------------")
        
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
