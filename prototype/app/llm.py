import os
import re
import textwrap
from typing import TypeVar
from openai import OpenAI
from pydantic import BaseModel

LITELLM_BASE_URL = os.environ.get("LITELLM_URL", "http://localhost:8080")
LITELLM_API_KEY = os.environ.get("LITELLM_API_KEY", "admin")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "gemini/gemini-3.6-flash")
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "180")) # time until the LLM request times out

llm_client = OpenAI(base_url=LITELLM_BASE_URL, api_key=LITELLM_API_KEY, timeout=LLM_TIMEOUT)

Schema = TypeVar("Schema", bound=BaseModel)

# -----------------------------------------------------------------------------
# helpers.

def extract_xml(text: str, tag: str) -> str:
    """
    Extracts the content of the specified XML tag from the given text. Used for parsing structured responses

    Args:
        text (str): The text containing the XML.
        tag (str): The XML tag to extract content from.

    Returns:
        str: The content of the specified XML tag, or an empty string if the tag is not found.
    """
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    response = match.group(1) if match else ""
    formated = textwrap.dedent(response).strip()
    return formated

# -----------------------------------------------------------------------------
# calling the model.

def call_llm(
    messages: list[dict],
    model: str = "gemini/gemini-3.6-flash"
)-> str:
    """
    Call the LLM with the given messages and return the response content.

    Args:
        messages (list[dict]): The list of messages to send to the LLM.
        model (str, optional): The model id to use for the LLM call.

    Returns:
        str: The content of the LLM's response.
    """
    response = llm_client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content


def call_llm_structured(
    messages: list[dict],
    schema: type[Schema],
    model: str = DEFAULT_MODEL,
) -> Schema:
    """
    Call the LLM and return the answer as a validated Pydantic object.

    The JSON schema of the given model is sent along with the request. The
    provider constrains the generation to that schema, so the answer can be
    parsed directly instead of being read out of free text.

    Raises pydantic.ValidationError: If the answer does not match the schema.
    """
    response = llm_client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "schema": schema.model_json_schema(),
            },
        },
    )
    content = response.choices[0].message.content
    return schema.model_validate_json(content)
