# from datetime import timedelta
# from app.auth.dependencies import verify_password
# from fastapi import Depends, FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.security import OAuth2PasswordRequestForm
# from requests import Session
# from streamlit import status
# from app.api import stations, bookings, payments, routes, admin
# from app.core.config import settings
# from app.database.session import engine, get_db
# from app.database import base
# from backend.app.models.admin import Admin
# from dependencies import ACCESS_TOKEN_EXPIRE_MINUTES, UserRole, create_access_token


# # Create database tables
# base.Base.metadata.create_all(bind=engine)

# app = FastAPI(title=settings.PROJECT_NAME)

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],           #settings.ALLOWED_HOSTS,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Include API routers
# app.include_router(stations.router, prefix="/stations", tags=["stations"])
# app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
# app.include_router(payments.router, prefix="/payments", tags=["payments"])
# app.include_router(routes.router, prefix="/routes", tags=["routes"])
# app.include_router(admin.router, prefix="/admin", tags=["admin"])

# @app.get("/")
# def health_check():
#     return {"status": "healthy"}

from datetime import timedelta
from typing import Dict, Any, Union

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from app.api import stations, bookings, payments, routes, admin
from app.core.config import settings
from app.database.session import engine, get_db
from app.database import base
from app.models.admin import Admin
from app.models.user import User
from app.schemas.auth import Token  # Import the actual Token schema

from app.auth.dependencies import (
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    UserRole, 
    create_access_token,
    verify_password
)

# Create database tables
base.Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME,debug=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[""],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(stations.router, prefix="/stations", tags=["stations"])
app.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(routes.router, prefix="/routes", tags=["routes"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

# Custom OpenAPI for Swagger UI with security scheme
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Bus Ticket Booking System API",
        routes=app.routes,
    )

    # Don't overwrite components, just add the security scheme
    components = openapi_schema.get("components", {})
    security_schemes = components.get("securitySchemes", {})

    security_schemes["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    components["securitySchemes"] = security_schemes
    openapi_schema["components"] = components

    # Apply security globally
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation.setdefault("security", [{"bearerAuth": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

@app.get("/")
def health_check():
    return {"status": "healthy"}

def authenticate_user(db: Session, username: str, password: str):
    print("🔍 Looking up user or admin:", username)

    # First, check if it's an admin
    admin = db.query(Admin).filter(Admin.username == username).first()
    if admin:
        print("👤 Found admin:", admin.username)
        if verify_password(password, admin.hashed_password):
            print("🔐 Password match for admin")
            return admin
        else:
            print("❌ Admin password mismatch")
            return None

    # If not an admin, try checking the user table
    user = db.query(User).filter(User.username == username).first()
    if user:
        print("👤 Found user:", user.username)
        if verify_password(password, user.hashed_password):
            print("🔐 Password match for user")
            return user
        else:
            print("❌ User password mismatch")
            return None

    print("❓ No admin or user found with that username")
    return None

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    try:
        print("🟡 Login attempt received")
        print(f"➡️ Username: {form_data.username}")
        print(f"➡️ Password: {form_data.password}")  # Be careful, only log this in dev

        # Verify user credentials
        user = authenticate_user(db, form_data.username, form_data.password)

        if not user:
            print("❌ Authentication failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        print(f"✅ Authenticated user: {user.username} (id: {user.id})")

        # Determine role
        if isinstance(user, Admin):
            role = UserRole.SUPER_ADMIN.value if user.is_super_admin else UserRole.ADMIN.value
            print(f"🔐 Role determined: {role}")
        else:
            role = UserRole.USER.value
            print("🔐 Role determined: USER")

        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "role": role}, 
            expires_delta=access_token_expires
        )

        print("✅ Access token created successfully")
        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        print("❌ Error during login:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
            headers={"WWW-Authenticate": "Bearer"},
        )