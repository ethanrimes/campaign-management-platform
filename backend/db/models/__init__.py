# backend/db/models/__init__.py

"""
Centralized database models with serialization support.
All agent models should import from here rather than defining their own.
"""

# Import base models with serialization
from backend.db.models.base import CustomModel, CustomModelInsert, CustomModelUpdate

# Import serialization utilities
from backend.db.models.serialization import (
    serialize_value,
    serialize_dict,
    deserialize_datetime,
    deserialize_uuid,
    deserialize_decimal,
    prepare_for_db,
    CustomJSONEncoder,
    SerializableBaseModel
)

# Import all database models
from backend.db.models.ad_set import (
    AdSetsBaseSchema, 
    AdSetsInsert, 
    AdSetsUpdate, 
    AdSets
)

from backend.db.models.campaign import (
    CampaignsBaseSchema,
    CampaignsInsert,
    CampaignsUpdate,
    Campaigns
)

from backend.db.models.execution_log import (
    ExecutionLogsBaseSchema,
    ExecutionLogsInsert,
    ExecutionLogsUpdate,
    ExecutionLogs
)

from backend.db.models.initiative import (
    InitiativesBaseSchema,
    InitiativesInsert,
    InitiativesUpdate,
    Initiatives
)

from backend.db.models.initiative_token import (
    InitiativeTokensBaseSchema,
    InitiativeTokensInsert,
    InitiativeTokensUpdate,
    InitiativeTokens
)

from backend.db.models.media_file import (
    MediaFilesBaseSchema,
    MediaFilesInsert,
    MediaFilesUpdate,
    MediaFiles
)

from backend.db.models.metrics import (
    MetricsBaseSchema,
    MetricsInsert,
    MetricsUpdate,
    Metrics
)

from backend.db.models.post import (
    PostsBaseSchema,
    PostsInsert,
    PostsUpdate,
    Posts
)

from backend.db.models.research import (
    ResearchBaseSchema,
    ResearchInsert,
    ResearchUpdate,
    Research
)

# Export all models and utilities
__all__ = [
    # Base models
    'CustomModel',
    'CustomModelInsert',
    'CustomModelUpdate',
    
    # Serialization utilities
    'serialize_value',
    'serialize_dict',
    'deserialize_datetime',
    'deserialize_uuid',
    'deserialize_decimal',
    'prepare_for_db',
    'CustomJSONEncoder',
    'SerializableBaseModel',
    
    # Ad Sets
    'AdSetsBaseSchema',
    'AdSetsInsert',
    'AdSetsUpdate',
    'AdSets',
    
    # Campaigns
    'CampaignsBaseSchema',
    'CampaignsInsert',
    'CampaignsUpdate',
    'Campaigns',
    
    # Execution Logs
    'ExecutionLogsBaseSchema',
    'ExecutionLogsInsert',
    'ExecutionLogsUpdate',
    'ExecutionLogs',
    
    # Initiatives
    'InitiativesBaseSchema',
    'InitiativesInsert',
    'InitiativesUpdate',
    'Initiatives',
    
    # Initiative Tokens
    'InitiativeTokensBaseSchema',
    'InitiativeTokensInsert',
    'InitiativeTokensUpdate',
    'InitiativeTokens',
    
    # Media Files
    'MediaFilesBaseSchema',
    'MediaFilesInsert',
    'MediaFilesUpdate',
    'MediaFiles',
    
    # Metrics
    'MetricsBaseSchema',
    'MetricsInsert',
    'MetricsUpdate',
    'Metrics',
    
    # Posts
    'PostsBaseSchema',
    'PostsInsert',
    'PostsUpdate',
    'Posts',
    
    # Research
    'ResearchBaseSchema',
    'ResearchInsert',
    'ResearchUpdate',
    'Research',
]

# Provide convenient imports for common use cases
def get_model_for_table(table_name: str):
    """Get the appropriate model class for a database table"""
    table_model_map = {
        'ad_sets': AdSets,
        'campaigns': Campaigns,
        'execution_logs': ExecutionLogs,
        'initiatives': Initiatives,
        'initiative_tokens': InitiativeTokens,
        'media_files': MediaFiles,
        'metrics': Metrics,
        'posts': Posts,
        'research': Research,
    }
    return table_model_map.get(table_name)

def get_insert_model_for_table(table_name: str):
    """Get the appropriate insert model class for a database table"""
    table_model_map = {
        'ad_sets': AdSetsInsert,
        'campaigns': CampaignsInsert,
        'execution_logs': ExecutionLogsInsert,
        'initiatives': InitiativesInsert,
        'initiative_tokens': InitiativeTokensInsert,
        'media_files': MediaFilesInsert,
        'metrics': MetricsInsert,
        'posts': PostsInsert,
        'research': ResearchInsert,
    }
    return table_model_map.get(table_name)

def get_update_model_for_table(table_name: str):
    """Get the appropriate update model class for a database table"""
    table_model_map = {
        'ad_sets': AdSetsUpdate,
        'campaigns': CampaignsUpdate,
        'execution_logs': ExecutionLogsUpdate,
        'initiatives': InitiativesUpdate,
        'initiative_tokens': InitiativeTokensUpdate,
        'media_files': MediaFilesUpdate,
        'metrics': MetricsUpdate,
        'posts': PostsUpdate,
        'research': ResearchUpdate,
    }
    return table_model_map.get(table_name)