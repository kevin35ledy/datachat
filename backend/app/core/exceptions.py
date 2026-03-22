from __future__ import annotations


class DBIAError(Exception):
    """Base exception for all DB-IA domain errors."""


# --- Connection errors ---

class ConnectionError(DBIAError):
    """Cannot establish a database connection."""


class ConnectionNotFoundError(DBIAError):
    """Requested connection config does not exist."""


class UnsupportedDatabaseError(DBIAError):
    """Database type is not supported by any registered connector."""


# --- SQL validation errors ---

class SQLValidationError(DBIAError):
    """SQL failed structural or safety validation."""


class SQLSecurityError(SQLValidationError):
    """SQL contains forbidden patterns (non-SELECT, system tables, etc.)."""


class SQLExtractionError(DBIAError):
    """Could not extract SQL from LLM response."""


class QueryTimeoutError(DBIAError):
    """Query exceeded the configured timeout."""


# --- LLM errors ---

class LLMError(DBIAError):
    """LLM call failed."""


class LLMProviderNotFoundError(DBIAError):
    """Requested LLM provider is not registered."""


class LLMContextTooLargeError(DBIAError):
    """Assembled prompt exceeds model context window."""


# --- Schema errors ---

class SchemaIntrospectionError(DBIAError):
    """Could not introspect database schema."""


class SchemaNotFoundError(DBIAError):
    """Schema for the given connection has not been loaded."""


# --- Dashboard errors ---

class DashboardNotFoundError(DBIAError):
    """Dashboard ID does not exist."""


class DashboardWidgetCreationError(DBIAError):
    """NL2SQL pipeline failed during widget creation."""


# --- Audit errors ---

class AuditJobNotFoundError(DBIAError):
    """Audit job ID not found."""


class AuditError(DBIAError):
    """Generic audit execution error."""
