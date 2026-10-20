import os
import sys
import re
import json
import html
import base64
import binascii
import asyncio

from datetime import date, datetime, time
from decimal import Decimal
from functools import lru_cache
from html.parser import HTMLParser
from typing import Any
from uuid import UUID

import pyodbc

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage

from llm_setup import llm
from config import config


# ============================================================
# UTF-8 SUPPORT
# ============================================================

os.environ.setdefault(
    "PYTHONUTF8",
    "1"
)

os.environ.setdefault(
    "PYTHONIOENCODING",
    "utf-8"
)


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        pass


if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        pass


# ============================================================
# CONFIGURATION
# ============================================================

MSSQL_SCHEMA = "dbo"


# These are the ONLY database tables used by this service.
ALLOWED_TABLES = [
    "tblSingMapProject",
    "tblSingMapProjectFact",
]


# Limit recursive JSON/Base64 decoding so malformed/circular-like
# data cannot cause excessive recursion.
MAX_DECODE_DEPTH = 20


# ============================================================
# MSSQL CONNECTION
# ============================================================

CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=showflat.database.windows.net;"
    "DATABASE=oneportalsg-dev;"
    f"UID={config.MSSQL_DATABASE_USERNAME};"
    f"PWD={config.MSSQL_DATABASE_PASSWORD};"
    "Connection Timeout=15;"
    "MARS_Connection=Yes;"
    "Encrypt=Yes;"
    "TrustServerCertificate=No;"
)


# Let SQLAlchemy handle pooling.
pyodbc.pooling = False


connection_url = URL.create(
    "mssql+pyodbc",
    query={
        "odbc_connect": CONNECTION_STRING
    }
)


engine = create_engine(
    connection_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)


# ============================================================
# LANGCHAIN DATABASE
# ============================================================

# The SQL LLM is allowed to see ONLY the two relevant tables.
db = SQLDatabase(
    engine=engine,
    schema=MSSQL_SCHEMA,
    include_tables=ALLOWED_TABLES,
    sample_rows_in_table_info=0,
    indexes_in_table_info=False,
    view_support=False,
)


# Same shared LLM instance.
# Only override temperature for deterministic SQL generation.
sql_llm = llm.bind(
    temperature=0
)


# ============================================================
# DATABASE SCHEMA CACHE
# ============================================================

@lru_cache(maxsize=1)
def get_project_schema() -> str:
    """
    Only the project table schema is needed by the SQL LLM.

    tblSingMapProjectFact is queried using a fixed safe query
    after the project Id has been found.
    """

    return db.get_table_info(
        table_names=[
            "tblSingMapProject"
        ]
    )


def clear_schema_cache() -> None:
    get_project_schema.cache_clear()


# ============================================================
# SQL AGENT PROMPT
# ============================================================

SQL_AGENT_PROMPT = """
You are a SQL Server retrieval agent for a Singapore
real-estate database.

Your ONLY job is to generate ONE SQL query that finds the
single project requested by the user.

You do NOT answer the user's real-estate question.

You do NOT summarize data.

You do NOT decide which project facts are relevant.

You ONLY generate the SQL needed to retrieve the correct
project row.


============================================================
AVAILABLE PROJECT TABLE
============================================================

dbo.tblSingMapProject


Every column in dbo.tblSingMapProject is useful.

Therefore the query MUST retrieve:

    p.*

This is intentional.

The ListJson column is extremely important and MUST always
be included.

Using:

    SELECT TOP 1 p.*

is the expected pattern.


============================================================
UNDERSTANDING THE USER QUESTION
============================================================

The user will send a complete natural-language question.

Examples:

"Which MRT stations are near V on Shenton?"

"What unit types are available in Turquoise?"

"Who is the developer of One Sophia?"

"What facilities does The Collective at One Sophia have?"


Your job is to identify the PROJECT / DEVELOPMENT name from
the question and use it to find the correct project row.

Terms such as:

MRT
school
unit type
facility
bedroom
price
amenity
restaurant
bus station

describe WHAT information the user wants.

They should NOT be treated as project names.


============================================================
PROJECT MATCHING PRIORITY
============================================================

Prefer:

1. exact ProjectName
2. exact ProjectTitle
3. exact SingMapProjectId
4. partial ProjectName
5. partial ProjectTitle
6. partial StreetAddress


Normally retrieve exactly ONE project.

Always use:

    TOP 1


Never use:

    TOP 100


Never retrieve many projects and expect another LLM to choose
between them.


============================================================
PARAMETERIZATION
============================================================

NEVER place the user's project name directly inside SQL.

Use SQLAlchemy named parameters.

Example:

    :exact_name
    :partial_name


Return the values separately inside "params".


Correct example:

{
  "project_query": "SELECT TOP 1 p.* FROM dbo.tblSingMapProject AS p WHERE p.ProjectName = :exact_name OR p.ProjectTitle = :exact_name OR p.ProjectName LIKE :partial_name OR p.ProjectTitle LIKE :partial_name ORDER BY CASE WHEN p.ProjectName = :exact_name THEN 0 WHEN p.ProjectTitle = :exact_name THEN 1 WHEN p.ProjectName LIKE :partial_name THEN 2 ELSE 3 END, p.IsActive DESC, p.Id DESC",
  "params": {
    "exact_name": "V on Shenton",
    "partial_name": "%V on Shenton%"
  }
}


============================================================
SECURITY
============================================================

Only SELECT is permitted.

Never generate:

INSERT
UPDATE
DELETE
MERGE
DROP
ALTER
CREATE
TRUNCATE
EXEC
EXECUTE
GRANT
REVOKE
DENY

Never query another database.

Never query another schema.

Never query another table.

Never JOIN another table.

Never use comments.

Never generate multiple SQL statements.


============================================================
OUTPUT FORMAT
============================================================

Return JSON ONLY.

Exactly this structure:

{
  "project_query": "SELECT ...",
  "params": {
    "parameter_name": "value"
  }
}

Do not use markdown.

Do not explain the SQL.

Do not answer the user's question.
""".strip()


# ============================================================
# SQL SAFETY
# ============================================================

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b("
    r"INSERT|"
    r"UPDATE|"
    r"DELETE|"
    r"MERGE|"
    r"DROP|"
    r"ALTER|"
    r"CREATE|"
    r"TRUNCATE|"
    r"EXEC|"
    r"EXECUTE|"
    r"GRANT|"
    r"REVOKE|"
    r"DENY|"
    r"BACKUP|"
    r"RESTORE|"
    r"OPENROWSET|"
    r"OPENQUERY|"
    r"OPENDATASOURCE"
    r")\b",
    re.IGNORECASE
)


PARAMETER_PATTERN = re.compile(
    r":([A-Za-z_][A-Za-z0-9_]*)"
)


# ============================================================
# SQL / MODEL RESPONSE HELPERS
# ============================================================

def message_to_text(
    content: Any
) -> str:
    """
    Convert OpenAI-compatible model content into text.
    """

    if isinstance(content, str):
        return content


    if isinstance(content, list):

        parts: list[str] = []

        for item in content:

            if isinstance(item, str):

                parts.append(
                    item
                )

            elif isinstance(item, dict):

                value = item.get(
                    "text"
                )

                if value is not None:

                    parts.append(
                        str(value)
                    )


        return "\n".join(
            parts
        )


    return str(content)


def extract_json_object(
    content: str
) -> dict[str, Any]:
    """
    Parse JSON returned by the SQL LLM.
    """

    content = content.strip()


    # Remove accidental markdown fences.
    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE
    )


    content = re.sub(
        r"\s*```$",
        "",
        content
    )


    content = content.strip()


    # First try the complete response.
    try:

        result = json.loads(
            content
        )


        if isinstance(result, dict):

            return result


    except json.JSONDecodeError:
        pass


    # Fallback if the model accidentally added text.
    start = content.find(
        "{"
    )

    end = content.rfind(
        "}"
    )


    if (
        start != -1
        and end > start
    ):

        try:

            result = json.loads(
                content[start:end + 1]
            )


            if isinstance(result, dict):

                return result


        except json.JSONDecodeError:
            pass


    raise ValueError(
        "SQL agent returned invalid JSON."
    )


# ============================================================
# SQL VALIDATION
# ============================================================

def validate_project_query(
    sql: str,
    params: dict[str, Any]
) -> str:
    """
    Validate LLM-generated project SQL before execution.
    """

    if not isinstance(sql, str):

        raise ValueError(
            "project_query must be a string."
        )


    sql = sql.strip()


    if not sql:

        raise ValueError(
            "Project query is empty."
        )


    upper_sql = sql.upper()

    lower_sql = sql.lower()


    # --------------------------------------------------------
    # Only SELECT
    # --------------------------------------------------------

    if not upper_sql.startswith(
        "SELECT"
    ):

        raise ValueError(
            "Only SELECT queries are allowed."
        )


    # --------------------------------------------------------
    # Dangerous SQL
    # --------------------------------------------------------

    if FORBIDDEN_SQL_PATTERN.search(
        sql
    ):

        raise ValueError(
            "Unsafe SQL operation detected."
        )


    # --------------------------------------------------------
    # No SQL comments
    # --------------------------------------------------------

    if (
        "--" in sql
        or "/*" in sql
        or "*/" in sql
    ):

        raise ValueError(
            "SQL comments are not allowed."
        )


    # --------------------------------------------------------
    # One statement only
    # --------------------------------------------------------

    stripped_without_final_semicolon = (
        sql[:-1]
        if sql.endswith(";")
        else sql
    )


    if ";" in stripped_without_final_semicolon:

        raise ValueError(
            "Multiple SQL statements are not allowed."
        )


    # --------------------------------------------------------
    # Correct table only
    # --------------------------------------------------------

    if (
        "tblsingmapproject"
        not in lower_sql
    ):

        raise ValueError(
            "Project query must use tblSingMapProject."
        )


    if (
        "tblsingmapprojectfact"
        in lower_sql
    ):

        raise ValueError(
            "Project query must not query tblSingMapProjectFact."
        )


    # --------------------------------------------------------
    # No joins
    # --------------------------------------------------------

    if re.search(
        r"\bJOIN\b",
        sql,
        flags=re.IGNORECASE
    ):

        raise ValueError(
            "Project query must not contain JOIN."
        )


    # --------------------------------------------------------
    # dbo schema only
    # --------------------------------------------------------

    from_matches = re.findall(
        r"\bFROM\s+([A-Za-z0-9_\.\[\]]+)",
        sql,
        flags=re.IGNORECASE
    )


    if not from_matches:

        raise ValueError(
            "Project query does not contain a valid FROM."
        )


    for table_reference in from_matches:

        cleaned = (
            table_reference
            .replace("[", "")
            .replace("]", "")
            .lower()
        )


        if cleaned not in {
            "dbo.tblsingmapproject",
            "tblsingmapproject"
        }:

            raise ValueError(
                f"Unauthorized table: {table_reference}"
            )


    # --------------------------------------------------------
    # Must retrieve only one project
    # --------------------------------------------------------

    if not re.search(
        r"\bTOP\s*\(?\s*1\s*\)?\b",
        sql,
        flags=re.IGNORECASE
    ):

        raise ValueError(
            "Project query must use TOP 1."
        )


    # --------------------------------------------------------
    # Must retrieve ALL project columns / ListJson
    # --------------------------------------------------------

    select_part = lower_sql.split(
        "from",
        1
    )[0]


    if (
        "p.*" not in select_part
        and re.search(
            r"\bselect\s+top\s*\(?\s*1\s*\)?\s+\*",
            lower_sql
        ) is None
    ):

        raise ValueError(
            "Project query must retrieve all project columns "
            "using p.* or *."
        )


    # --------------------------------------------------------
    # Parameters
    # --------------------------------------------------------

    if not isinstance(
        params,
        dict
    ):

        raise ValueError(
            "SQL parameters must be a dictionary."
        )


    required_parameters = set(
        PARAMETER_PATTERN.findall(
            sql
        )
    )


    supplied_parameters = set(
        params.keys()
    )


    missing_parameters = (
        required_parameters
        - supplied_parameters
    )


    if missing_parameters:

        raise ValueError(
            "Missing SQL parameters: "
            + ", ".join(
                sorted(
                    missing_parameters
                )
            )
        )


    # Keep params simple/safe.
    for key, value in params.items():

        if not isinstance(
            key,
            str
        ):

            raise ValueError(
                "SQL parameter names must be strings."
            )


        if not isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
                type(None)
            )
        ):

            raise ValueError(
                f"Unsupported SQL parameter type for {key}."
            )


    return sql


# ============================================================
# SQL GENERATION
# ============================================================

async def generate_project_query(
    question: str
) -> tuple[
    str,
    dict[str, Any]
]:
    """
    SQL LLM determines the requested project and creates only
    the project lookup query.

    It does NOT answer the user's question.
    """

    schema = await asyncio.to_thread(
        get_project_schema
    )


    request = f"""
DATABASE SCHEMA:

{schema}


USER QUESTION:

{question}


Generate ONE safe SQL Server query that retrieves the single
requested project.

Requirements:

- SELECT TOP 1
- retrieve ALL project columns using p.*
- ListJson must therefore be included
- use dbo.tblSingMapProject only
- use named SQLAlchemy parameters
- return JSON only
""".strip()


    response = await sql_llm.ainvoke(
        [
            SystemMessage(
                content=SQL_AGENT_PROMPT
            ),

            HumanMessage(
                content=request
            )
        ]
    )
    
    print(response)


    result = extract_json_object(
        message_to_text(
            response.content
        )
    )


    project_query = result.get(
        "project_query"
    )


    params = result.get(
        "params",
        {}
    )


    if not isinstance(
        project_query,
        str
    ):

        raise ValueError(
            "SQL agent did not return project_query."
        )


    if not isinstance(
        params,
        dict
    ):

        raise ValueError(
            "SQL agent did not return valid params."
        )


    project_query = validate_project_query(
        project_query,
        params
    )


    return (
        project_query,
        params
    )


# ============================================================
# DATABASE VALUE NORMALIZATION
# ============================================================

def normalize_database_value(
    value: Any
) -> Any:
    """
    Convert SQL Server-specific Python values into JSON-safe
    values.

    Strings are intentionally preserved here.
    They are decoded in a separate recursive preprocessing
    step.
    """

    if value is None:

        return None


    if isinstance(
        value,
        (
            datetime,
            date,
            time
        )
    ):

        return value.isoformat()


    if isinstance(
        value,
        Decimal
    ):

        return float(
            value
        )


    if isinstance(
        value,
        UUID
    ):

        return str(
            value
        )


    if isinstance(
        value,
        bytes
    ):

        return value.hex()


    return value


def normalize_database_row(
    row: dict[str, Any]
) -> dict[str, Any]:

    return {
        key: normalize_database_value(
            value
        )
        for key, value
        in row.items()
    }


# ============================================================
# HTML DECODING
# ============================================================

class LLMHTMLParser(
    HTMLParser
):
    """
    Strip HTML/CSS while preserving useful human-readable text,
    image URLs and hyperlinks.
    """

    def __init__(
        self
    ) -> None:

        super().__init__()

        self.text_parts: list[str] = []

        self.images: list[str] = []

        self.links: list[str] = []

        self.skip_depth = 0


    def handle_starttag(
        self,
        tag: str,
        attrs
    ) -> None:

        tag = tag.lower()


        # Ignore style/javascript body contents.
        if tag in {
            "style",
            "script"
        }:

            self.skip_depth += 1

            return


        attrs_dict = dict(
            attrs
        )


        if tag == "img":

            src = attrs_dict.get(
                "src"
            )


            if src:

                self.images.append(
                    src
                )


        elif tag == "a":

            href = attrs_dict.get(
                "href"
            )


            if href:

                self.links.append(
                    href
                )


        elif tag in {
            "br",
            "p",
            "div",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6"
        }:

            self.text_parts.append(
                "\n"
            )


    def handle_endtag(
        self,
        tag: str
    ) -> None:

        tag = tag.lower()


        if tag in {
            "style",
            "script"
        }:

            if self.skip_depth > 0:

                self.skip_depth -= 1

            return


        if tag in {
            "p",
            "div",
            "li",
            "tr",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6"
        }:

            self.text_parts.append(
                "\n"
            )


    def handle_data(
        self,
        data: str
    ) -> None:

        if self.skip_depth > 0:

            return


        if data:

            self.text_parts.append(
                data
            )


def looks_like_html(
    value: str
) -> bool:

    return bool(
        re.search(
            r"<\s*/?\s*"
            r"(html|body|p|div|span|br|img|a|table|tr|td|"
            r"ul|ol|li|strong|b|i|em|h[1-6])"
            r"\b",
            value,
            flags=re.IGNORECASE
        )
    )


def clean_html_for_llm(
    value: str
) -> Any:
    """
    HTML -> compact LLM-friendly data.

    Example:

        <p>Hello <img src="image.jpg"></p>

    becomes:

        {
            "text": "Hello",
            "images": ["image.jpg"]
        }
    """

    parser = LLMHTMLParser()


    try:

        parser.feed(
            value
        )

        parser.close()


    except Exception:

        # If HTML parsing somehow fails, at least decode HTML
        # entities and return the original content.
        return html.unescape(
            value
        )


    text_value = "".join(
        parser.text_parts
    )


    text_value = html.unescape(
        text_value
    )


    # Normalize whitespace but preserve meaningful line breaks.
    text_value = re.sub(
        r"[ \t]+",
        " ",
        text_value
    )


    text_value = re.sub(
        r"\n\s*\n+",
        "\n",
        text_value
    )


    text_value = text_value.strip()


    images = list(
        dict.fromkeys(
            parser.images
        )
    )


    links = list(
        dict.fromkeys(
            parser.links
        )
    )


    # Simplest possible output if there is only text.
    if (
        not images
        and not links
    ):

        return text_value


    result: dict[str, Any] = {}


    if text_value:

        result["text"] = (
            text_value
        )


    if images:

        result["images"] = (
            images
        )


    if links:

        result["links"] = (
            links
        )


    return result


# ============================================================
# JSON DECODING
# ============================================================

def try_parse_json_string(
    value: str
) -> Any | None:
    """
    Parse only strings that clearly look like JSON.

    This handles:

    ListJson
    PayloadJson
    facilitiesMap
    facilitiesMap1
    facilitiesMap05
    and other nested JSON strings.
    """

    stripped = value.strip()


    if not stripped:

        return None


    looks_like_object = (
        stripped.startswith("{")
        and stripped.endswith("}")
    )


    looks_like_array = (
        stripped.startswith("[")
        and stripped.endswith("]")
    )


    if not (
        looks_like_object
        or looks_like_array
    ):

        return None


    try:

        return json.loads(
            stripped
        )


    except (
        json.JSONDecodeError,
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# BASE64 DECODING
# ============================================================

BASE64_PATTERN = re.compile(
    r"^[A-Za-z0-9+/]+={0,2}$"
)


def try_decode_base64_text(
    value: str
) -> str | None:
    """
    Conservatively detect Base64 text.

    Random project IDs, hashes and normal strings should remain
    untouched.

    A value is accepted only when:

    - it has valid Base64 syntax
    - it decodes as UTF-8
    - decoded content is mostly printable
    - decoded result strongly resembles useful text, JSON or
      HTML
    """

    stripped = value.strip()


    if len(stripped) < 16:

        return None


    # Do not treat URLs as Base64.
    if stripped.startswith(
        (
            "http://",
            "https://"
        )
    ):

        return None


    # Normal prose is not Base64.
    if re.search(
        r"\s",
        stripped
    ):

        return None


    if not BASE64_PATTERN.fullmatch(
        stripped
    ):

        return None


    # Restore missing Base64 padding if needed.
    padded = stripped + (
        "="
        * (
            (-len(stripped))
            % 4
        )
    )


    try:

        decoded_bytes = base64.b64decode(
            padded,
            validate=True
        )


    except (
        binascii.Error,
        ValueError
    ):

        return None


    if not decoded_bytes:

        return None


    try:

        decoded_text = decoded_bytes.decode(
            "utf-8"
        )


    except UnicodeDecodeError:

        return None


    decoded_text = decoded_text.strip()


    if not decoded_text:

        return None


    printable_characters = sum(
        1
        for character
        in decoded_text
        if (
            character.isprintable()
            or character
            in "\r\n\t"
        )
    )


    printable_ratio = (
        printable_characters
        / len(decoded_text)
    )


    if printable_ratio < 0.95:

        return None


    # Strong evidence: decoded HTML.
    if looks_like_html(
        decoded_text
    ):

        return decoded_text


    # Strong evidence: decoded JSON.
    if try_parse_json_string(
        decoded_text
    ) is not None:

        return decoded_text


    # Plain Base64 text must resemble actual prose.
    alphabetic_count = sum(
        character.isalpha()
        for character
        in decoded_text
    )


    alphabetic_ratio = (
        alphabetic_count
        / len(decoded_text)
    )


    # Requiring spaces/newlines dramatically reduces the chance
    # of accidentally decoding database IDs/hashes.
    contains_word_spacing = bool(
        re.search(
            r"\s",
            decoded_text
        )
    )


    if (
        alphabetic_ratio >= 0.50
        and contains_word_spacing
    ):

        return decoded_text


    return None


# ============================================================
# RECURSIVE DATABASE DECODER
# ============================================================

def decode_database_content(
    value: Any,
    depth: int = 0
) -> Any:
    """
    Recursively transform raw database data into LLM-friendly
    structured data.

    Handles:

    - normal JSON strings
    - nested JSON strings
    - ListJson
    - PayloadJson
    - facilitiesMap-style embedded JSON
    - Base64 text
    - Base64 HTML
    - raw HTML
    - HTML entities
    - dictionaries
    - lists

    Normal URLs, IDs, names and numbers remain unchanged.
    """

    if depth >= MAX_DECODE_DEPTH:

        return value


    # ========================================================
    # DICTIONARY
    # ========================================================

    if isinstance(
        value,
        dict
    ):

        return {
            key: decode_database_content(
                child,
                depth + 1
            )
            for key, child
            in value.items()
        }


    # ========================================================
    # LIST
    # ========================================================

    if isinstance(
        value,
        list
    ):

        return [
            decode_database_content(
                child,
                depth + 1
            )
            for child
            in value
        ]


    # ========================================================
    # NON-STRING
    # ========================================================

    if not isinstance(
        value,
        str
    ):

        return value


    stripped = value.strip()


    if not stripped:

        return value


    # ========================================================
    # 1. JSON
    # ========================================================

    parsed_json = try_parse_json_string(
        stripped
    )


    if parsed_json is not None:

        return decode_database_content(
            parsed_json,
            depth + 1
        )


    # ========================================================
    # 2. BASE64
    # ========================================================

    decoded_base64 = (
        try_decode_base64_text(
            stripped
        )
    )


    if (
        decoded_base64 is not None
        and decoded_base64 != stripped
    ):

        # Base64 could decode into another JSON string,
        # HTML value, or even another Base64 layer.
        return decode_database_content(
            decoded_base64,
            depth + 1
        )


    # ========================================================
    # 3. HTML
    # ========================================================

    if looks_like_html(
        stripped
    ):

        cleaned_html = (
            clean_html_for_llm(
                stripped
            )
        )


        return decode_database_content(
            cleaned_html,
            depth + 1
        )


    # ========================================================
    # 4. HTML ENTITIES
    # ========================================================

    unescaped = html.unescape(
        value
    )


    return unescaped


# ============================================================
# FIXED PROJECT FACT QUERY
# ============================================================

FACTS_QUERY = """
SELECT
    f.SourceKey,
    f.PayloadJson
FROM dbo.tblSingMapProjectFact AS f
WHERE
    f.SingMapProjectRowId = :project_id

    AND f.PayloadJson IS NOT NULL

    AND LEN(
        LTRIM(
            RTRIM(
                f.PayloadJson
            )
        )
    ) > 0

    AND LTRIM(
        RTRIM(
            f.PayloadJson
        )
    ) NOT IN (
        '',
        '[]',
        '{}'
    )

ORDER BY
    f.SourceKey ASC;
""".strip()


# ============================================================
# EXECUTE DATABASE QUERIES
# ============================================================

def execute_database_queries(
    project_query: str,
    project_params: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute:

    1. SQL-LLM-generated project query
    2. fixed safe project-facts query

    Then recursively decode all returned database content
    before returning it to MCP / the main LLM.
    """

    # Revalidate immediately before execution.
    project_query = (
        validate_project_query(
            project_query,
            project_params
        )
    )


    with engine.connect() as connection:

        # ====================================================
        # PROJECT
        # ====================================================

        project_result = (
            connection.execute(
                text(
                    project_query
                ),
                project_params
            )
        )


        project_row = (
            project_result
            .mappings()
            .first()
        )


        if project_row is None:

            return {
                "status": "not_found",
                "project": None,
                "facts": []
            }


        project = (
            normalize_database_row(
                dict(
                    project_row
                )
            )
        )


        project_id = (
            project.get(
                "Id"
            )
        )


        if project_id is None:

            raise ValueError(
                "Project query did not return Id."
            )


        project_id = int(
            project_id
        )


        # ====================================================
        # PROJECT FACTS
        # ====================================================

        facts_result = (
            connection.execute(
                text(
                    FACTS_QUERY
                ),
                {
                    "project_id":
                        project_id
                }
            )
        )


        facts = [
            normalize_database_row(
                dict(row)
            )
            for row
            in facts_result
            .mappings()
            .all()
        ]


    # ========================================================
    # DECODE EVERYTHING BEFORE MAIN LLM
    # ========================================================

    decoded_project = (
        decode_database_content(
            project
        )
    )


    decoded_facts = (
        decode_database_content(
            facts
        )
    )


    return {
        "status": "success",

        # Contains every tblSingMapProject column,
        # including decoded ListJson.
        "project": decoded_project,

        # Contains SourceKey and decoded PayloadJson.
        "facts": decoded_facts,
    }


# ============================================================
# PUBLIC DATABASE FUNCTION
# ============================================================

async def query_database(
    question: str
) -> dict[str, Any]:
    """
    Called by get_project_details MCP tool.

    Flow:

        complete user question
                ↓
        internal SQL LLM
                ↓
        project lookup SQL
                ↓
        tblSingMapProject
                ↓
        project Id
                ↓
        tblSingMapProjectFact
                ↓
        recursive JSON/Base64/HTML decoding
                ↓
        raw structured DB result
                ↓
        main LLM

    This function does NOT generate the final answer.
    """

    if not isinstance(
        question,
        str
    ):

        return {
            "status": "error",
            "message": "Question must be a string."
        }


    question = question.strip()


    if not question:

        return {
            "status": "error",
            "message": "Question is required."
        }


    # ========================================================
    # SQL AGENT
    # ========================================================

    project_query, project_params = (
        await generate_project_query(
            question
        )
    )


    # ========================================================
    # DATABASE EXECUTION
    # ========================================================

    result = await asyncio.to_thread(
        execute_database_queries,
        project_query,
        project_params
    )


    return result


# ============================================================
# CONNECTION TEST
# ============================================================

def test_database_connection() -> bool:
    """
    Minimal MSSQL connectivity test.
    """

    try:

        with engine.connect() as connection:

            result = (
                connection.execute(
                    text(
                        "SELECT 1 AS connection_test"
                    )
                )
            )


            return (
                result.scalar_one()
                == 1
            )


    except Exception:

        return False


# ============================================================
# OPTIONAL LOCAL TEST
# ============================================================

if __name__ == "__main__":

    async def _test():

        result = await query_database(
            "What facilities are available in Turquoise?"
        )


        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=True,
                default=str
            )
        )


    asyncio.run(
        _test()
    )