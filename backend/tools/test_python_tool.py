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
        from app.services.agent.tools_registry import python_tool
        
        # Test directly with mocked material_ids = []
        # We will mock get_material_for_user and get_material_text to return fake data
        import app.services.agent.tools_registry as tr
        
        async def mock_get_material_for_user(m_id, u_id):
            class MockMaterial:
                filename = "sales_data.csv"
            return MockMaterial()
            
        async def mock_get_material_text(m_id, u_id):
            return "Month,Sales\nJan,100\nFeb,150\nMar,200\nApr,180\n"
            
        tr.get_material_for_user = mock_get_material_for_user
        tr.get_material_text = mock_get_material_text
        
        logging.basicConfig(level=logging.INFO)
        print("Running python_tool...")
        
        result = await tr.python_tool(
            query="Load sales_data.csv, print its content, and plot a bar chart of Sales by Month.",
            user_id="test_user",
            notebook_id="test_notebook",
            material_ids=["mock_m_id"],
            intent="DATA_ANALYSIS",
            session_id="test_session"
        )
        
        print("\n--- TOOL RESULT OUTPUT ---")
        print(result["output"])
        print("--------------------------")
        
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
