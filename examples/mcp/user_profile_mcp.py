from pydantic import BaseModel
from fastmcp import FastMCP

mcp = FastMCP("user_profile_server")

class UserProfile(BaseModel):
    """A Pydantic model describing a user's profile."""
    name: str
    email: str
    user_id: int
    status: str

@mcp.tool
def get_user_profile(user_id: int) -> UserProfile:
    """
    Retrieves a user's profile from the database.
    Returns a UserProfile object.
    """
    # In a real application, you would fetch this from a database.
    return UserProfile(
        name="Alice",
        email="alice@example.com",
        user_id=user_id,
        status="active"
    )

if __name__ == "__main__":
    mcp.run()
