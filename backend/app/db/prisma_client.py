"""
Prisma database client for the application.

Usage:
    from app.db.prisma_client import prisma

    # In your service/route:
    user = await prisma.user.find_unique(where={"id": user_id})

The client is connected/disconnected in the FastAPI lifespan (main.py).
"""

import logging
from prisma import Prisma

logger = logging.getLogger(__name__)

# ── Single global Prisma client instance ──────────────────────────
prisma = Prisma()

# ── Export function for compatibility ──────────────────────────────
def get_prisma() -> Prisma:
    """Get the Prisma client instance.
    
    Returns:
        Prisma: The global Prisma client instance
    """
    return prisma


async def connect_db() -> None:
    """Connect the Prisma client to the database.
    
    Safe to call multiple times – skips if already connected.
    """
    if prisma.is_connected():
        logger.debug("Prisma client already connected")
        return
    try:
        await prisma.connect()
        logger.info("Prisma client connected to database")
    except Exception as e:
        logger.error(f"Failed to connect Prisma client: {e}")
        raise


async def disconnect_db() -> None:
    """Disconnect the Prisma client from the database.
    
    Safe to call multiple times – skips if already disconnected.
    """
    if not prisma.is_connected():
        logger.debug("Prisma client already disconnected")
        return
    try:
        await prisma.disconnect()
        logger.info("Prisma client disconnected from database")
    except Exception as e:
        logger.error(f"Error disconnecting Prisma client: {e}")
        raise
