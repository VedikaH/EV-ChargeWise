from requests import Session
from app.models.admin import Admin
from app.auth.dependencies import get_password_hash


def init_super_admin(db: Session):
    super_admin = Admin(
        username="superadmin",
        email="superadmin@example.com",
        hashed_password=get_password_hash("initial-password"),
        is_super_admin=True
    )
    db.add(super_admin)
    db.commit()