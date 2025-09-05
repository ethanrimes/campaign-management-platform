# backend/config/logging_config.py

"""
Centralized logging configuration for the Campaign Management Platform.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import os

class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for terminal output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class LoggingConfig:
    """Manages centralized logging configuration"""
    
    # Log levels mapping
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    @classmethod
    def setup_logging(
        cls,
        log_level: str = None,
        log_file: Optional[str] = None,
        log_to_console: bool = True,
        log_format: Optional[str] = None,
        colored_output: bool = True
    ):
        """
        Setup centralized logging configuration
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (optional)
            log_to_console: Whether to log to console
            log_format: Custom log format string
            colored_output: Whether to use colored output for console
        """
        from backend.config.settings import settings
        
        # Get log level from settings or parameter
        if log_level is None:
            log_level = getattr(settings, 'LOG_LEVEL', 'INFO')
        
        level = cls.LOG_LEVELS.get(log_level.upper(), logging.INFO)
        
        # Default format
        if log_format is None:
            log_format = getattr(
                settings, 
                'LOG_FORMAT',
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove existing handlers to avoid duplicates
        root_logger.handlers = []
        
        # Console handler
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            
            if colored_output and sys.stdout.isatty():
                formatter = ColoredFormatter(log_format)
            else:
                formatter = logging.Formatter(log_format)
            
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if log_file is None:
            log_file = getattr(settings, 'LOG_FILE', None)
        
        if log_file:
            # Create log directory if needed
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(file_handler)
        
        # Configure specific loggers
        cls._configure_module_loggers(level)
        
        # Log initial setup
        logger = logging.getLogger(__name__)
        logger.info(f"Logging configured - Level: {log_level}, Console: {log_to_console}, File: {log_file}")
    
    @classmethod
    def _configure_module_loggers(cls, level):
        """Configure logging levels for specific modules"""
        
        # Reduce noise from third-party libraries
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('supabase').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        # Set specific levels for our modules if needed
        module_configs = {
            'agents': level,
            'backend': level,
            'tools': level,
            'scripts': level,
        }
        
        for module, module_level in module_configs.items():
            logging.getLogger(module).setLevel(module_level)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance with the given name
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)
    
    @classmethod
    def setup_test_logging(cls):
        """Setup logging configuration for tests"""
        cls.setup_logging(
            log_level='DEBUG',
            log_to_console=True,
            colored_output=True,
            log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    @classmethod
    def setup_production_logging(cls):
        """Setup logging configuration for production"""
        cls.setup_logging(
            log_level='INFO',
            log_file='logs/campaign_platform.log',
            log_to_console=True,
            colored_output=False
        )


# Initialize logging on import
def init_logging():
    """Initialize logging based on environment"""
    env = os.getenv('ENVIRONMENT', 'development')
    
    if env == 'production':
        LoggingConfig.setup_production_logging()
    elif env == 'test':
        LoggingConfig.setup_test_logging()
    else:  # development
        LoggingConfig.setup_logging(
            log_level='INFO',
            log_to_console=True,
            colored_output=True
        )


# Updated backend/config/settings.py additions
SETTINGS_ADDITIONS = """
# Add these to backend/config/settings.py:

    # Logging Configuration
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: Optional[str] = None  # Path to log file
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_TO_CONSOLE: bool = True
    LOG_COLORED_OUTPUT: bool = True
    
    # Environment
    ENVIRONMENT: str = "development"  # development, test, production
"""