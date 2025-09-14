# agents/researcher/tools/__init__.py

from agents.researcher.tools.facebook_search import FacebookSearch
from agents.researcher.tools.instagram_search import InstagramSearch
from agents.researcher.tools.perplexity_search import PerplexitySearch

__all__ = [
    'FacebookSearch',
    'InstagramSearch', 
    'PerplexitySearch'
]