import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Configuration manager for loading and managing YAML config files"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files"""
        config_files = {
            'rag': 'rag_config.yaml',
            'api': 'api_config.yaml',
            'app': 'app_config.yaml'
        }
        
        for config_name, filename in config_files.items():
            config_path = self.config_dir / filename
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as file:
                        self._configs[config_name] = yaml.safe_load(file)
                    logger.info(f"Loaded config: {config_name}")
                except Exception as e:
                    logger.error(f"Error loading config {config_name}: {e}")
                    self._configs[config_name] = {}
            else:
                logger.warning(f"Config file not found: {config_path}")
                self._configs[config_name] = {}
    
    def get_rag_config(self) -> Dict[str, Any]:
        """Get RAG configuration"""
        return self._configs.get('rag', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return self._configs.get('api', {})
    
    def get_app_config(self) -> Dict[str, Any]:
        """Get application configuration"""
        return self._configs.get('app', {})
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configurations"""
        return self._configs.copy()
    
    def get_nested_config(self, *keys: str, default: Any = None) -> Any:
        """Get nested configuration value using dot notation"""
        config_name = keys[0]
        if config_name not in self._configs:
            return default
        
        config = self._configs[config_name]
        for key in keys[1:]:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                return default
        
        return config
    
    def get_with_env_override(self, *keys: str, env_var: str = None, default: Any = None) -> Any:
        """Get config value with environment variable override"""
        value = self.get_nested_config(*keys, default=default)
        
        if env_var and os.getenv(env_var):
            env_value = os.getenv(env_var)
            # Try to convert to appropriate type
            if isinstance(value, bool):
                env_value = env_value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(value, int):
                try:
                    env_value = int(env_value)
                except ValueError:
                    pass
            elif isinstance(value, float):
                try:
                    env_value = float(env_value)
                except ValueError:
                    pass
            
            return env_value
        
        return value
    
    def reload_configs(self):
        """Reload all configuration files"""
        logger.info("Reloading configuration files")
        self._load_all_configs()
    
    def validate_configs(self) -> bool:
        """Validate that all required configurations are present"""
        required_configs = ['rag', 'api', 'app']
        missing_configs = [config for config in required_configs if config not in self._configs]
        
        if missing_configs:
            logger.error(f"Missing required configurations: {missing_configs}")
            return False
        
        # Validate specific required fields
        rag_config = self.get_rag_config()
        if not rag_config.get('rag'):
            logger.error("RAG configuration is missing or invalid")
            return False
        
        api_config = self.get_api_config()
        if not api_config.get('api'):
            logger.error("API configuration is missing or invalid")
            return False
        
        app_config = self.get_app_config()
        if not app_config.get('app'):
            logger.error("Application configuration is missing or invalid")
            return False
        
        logger.info("All configurations validated successfully")
        return True

# Global configuration instance
config_manager = ConfigManager() 