from typing import List, Dict, Any

class AccessControlManager:
    """
    Simple Role-Based Access Control (RBAC) manager.
    """

    # Define role hierarchy and permissions
    ROLES = {
        "admin": {
            "permissions": ["view", "download", "edit", "delete", "archive"],
            "access_levels": ["public", "internal", "confidential", "secret"]
        },
        "manager": {
            "permissions": ["view", "download", "edit", "archive"],
            "access_levels": ["public", "internal", "confidential"]
        },
        "user": {
            "permissions": ["view", "download"],
            "access_levels": ["public", "internal"]
        },
        "guest": {
            "permissions": ["view"],
            "access_levels": ["public"]
        }
    }

    def check_permission(self, user_role: str, action: str) -> bool:
        """Check if role has permission for action."""
        role_config = self.ROLES.get(user_role, self.ROLES["guest"])
        return action in role_config["permissions"]

    def can_access_document(self, user_role: str, doc_access_level: str) -> bool:
        """Check if role can access document level."""
        role_config = self.ROLES.get(user_role, self.ROLES["guest"])
        return doc_access_level in role_config["access_levels"]
