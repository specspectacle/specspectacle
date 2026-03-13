"""
YAML parser with Pydantic validation
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from specspectacle.parser.schema import SpecModel
from specspectacle.utils.logger import logger


class YAMLParser:
    """Parser for SpecSpectacle YAML specifications."""

    @staticmethod
    def load_yaml(filepath: str) -> dict[str, Any]:
        """
        Load YAML file and return as dictionary.

        Args:
            filepath: Path to YAML file

        Returns:
            Dictionary representation of YAML

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"YAML file not found: {filepath}")

        with open(path, encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                if data is None:
                    raise yaml.YAMLError("Empty YAML file")
                return data
            except yaml.YAMLError:
                logger.error(f"YAML syntax error in {filepath}")
                raise

    @staticmethod
    def parse(filepath: str) -> SpecModel:
        """
        Load and validate YAML file against Pydantic schema.

        Args:
            filepath: Path to YAML file

        Returns:
            Validated SpecModel instance

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML syntax is invalid
            ValidationError: If YAML doesn't match schema
        """
        logger.debug(f"Parsing YAML file: {filepath}")

        # Load YAML
        try:
            data = YAMLParser.load_yaml(filepath)
        except FileNotFoundError as e:
            logger.error(str(e))
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML syntax: {e}")
            raise

        # Validate against schema
        try:
            spec = SpecModel(**data)
            logger.debug(f"Successfully parsed spec: {spec.name} v{spec.version}")
            return spec
        except ValidationError:
            logger.error("YAML validation failed")
            raise

    @staticmethod
    def format_validation_error(error: ValidationError) -> str:
        """
        Format Pydantic ValidationError into user-friendly message.

        Args:
            error: Pydantic ValidationError

        Returns:
            Formatted error message
        """
        lines = ["Validation errors found:"]
        for err in error.errors():
            loc = " → ".join(str(x) for x in err["loc"])
            msg = err["msg"]
            lines.append(f"  • {loc} : {msg}")

        return "\n".join(lines)


__all__ = ["YAMLParser"]
