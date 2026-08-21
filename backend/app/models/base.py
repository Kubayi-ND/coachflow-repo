from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base for API request/response schemas.

    Python code and the DB layer stay snake_case; JSON over the wire is
    camelCase to match the hand-maintained frontend types in
    frontend/src/types/index.ts. apiClient.ts does no key transformation,
    so the two sides must agree on casing at the model layer.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
