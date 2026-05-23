import os
from google import genai
from google.genai import types

# Use dummy API key for syntax testing if we don't need real request, or let it fail at request time.
# We just want to check if types compile.

tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="classify_document",
            description="Classify an Indian MCA corporate filing document.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "document_type": {
                        "type": "STRING",
                        "description": "Exact document type."
                    }
                }
            }
        )
    ]
)
print("Tool instantiated successfully")
