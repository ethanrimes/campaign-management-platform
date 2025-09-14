# backend/db/models/initiative_token.py

from pydantic import Field
from pydantic import UUID4
from typing import Optional
import datetime
from uuid import uuid4
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate


class InitiativeTokensBaseSchema(CustomModel):
    """InitiativeTokens Base Schema."""
    
    # Primary Keys
    id: UUID4
    
    # Columns
    created_at: Optional[datetime.datetime] = Field(default=None)
    created_by: Optional[str] = Field(default=None)
    fb_page_access_token_encrypted: Optional[str] = Field(default=None, description="Encrypted Facebook Page Access Token")
    fb_page_id: Optional[str] = Field(default=None)
    fb_page_name: Optional[str] = Field(default=None)
    fb_system_user_token_encrypted: Optional[str] = Field(default=None)
    initiative_id: UUID4
    insta_access_token_encrypted: Optional[str] = Field(default=None, description="Encrypted Instagram Access Token")
    insta_app_id_encrypted: Optional[str] = Field(default=None)
    insta_app_secret_encrypted: Optional[str] = Field(default=None)
    insta_business_id: Optional[str] = Field(default=None)
    insta_username: Optional[str] = Field(default=None)
    tokens_expire_at: Optional[datetime.datetime] = Field(default=None)
    tokens_last_validated: Optional[datetime.datetime] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class InitiativeTokensInsert(CustomModelInsert):
    """InitiativeTokens Insert Schema."""
    
    # Primary Keys (optional for insert)
    id: Optional[UUID4] = Field(default_factory=uuid4)
    
    # Required fields
    initiative_id: UUID4
    
    # Optional fields
    created_at: Optional[datetime.datetime] = Field(default=None)
    created_by: Optional[str] = Field(default=None)
    fb_page_access_token_encrypted: Optional[str] = Field(default=None, description="Encrypted Facebook Page Access Token")
    fb_page_id: Optional[str] = Field(default=None)
    fb_page_name: Optional[str] = Field(default=None)
    fb_system_user_token_encrypted: Optional[str] = Field(default=None)
    insta_access_token_encrypted: Optional[str] = Field(default=None, description="Encrypted Instagram Access Token")
    insta_app_id_encrypted: Optional[str] = Field(default=None)
    insta_app_secret_encrypted: Optional[str] = Field(default=None)
    insta_business_id: Optional[str] = Field(default=None)
    insta_username: Optional[str] = Field(default=None)
    tokens_expire_at: Optional[datetime.datetime] = Field(default=None)
    tokens_last_validated: Optional[datetime.datetime] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class InitiativeTokensUpdate(CustomModelUpdate):
    """InitiativeTokens Update Schema."""
    
    # All fields optional for update
    id: Optional[UUID4] = Field(default=None)
    created_at: Optional[datetime.datetime] = Field(default=None)
    created_by: Optional[str] = Field(default=None)
    fb_page_access_token_encrypted: Optional[str] = Field(default=None, description="Encrypted Facebook Page Access Token")
    fb_page_id: Optional[str] = Field(default=None)
    fb_page_name: Optional[str] = Field(default=None)
    fb_system_user_token_encrypted: Optional[str] = Field(default=None)
    initiative_id: Optional[UUID4] = Field(default=None)
    insta_access_token_encrypted: Optional[str] = Field(default=None, description="Encrypted Instagram Access Token")
    insta_app_id_encrypted: Optional[str] = Field(default=None)
    insta_app_secret_encrypted: Optional[str] = Field(default=None)
    insta_business_id: Optional[str] = Field(default=None)
    insta_username: Optional[str] = Field(default=None)
    tokens_expire_at: Optional[datetime.datetime] = Field(default=None)
    tokens_last_validated: Optional[datetime.datetime] = Field(default=None)
    updated_at: Optional[datetime.datetime] = Field(default=None)


class InitiativeTokens(InitiativeTokensBaseSchema):
    """InitiativeTokens Schema for Pydantic."""
    pass