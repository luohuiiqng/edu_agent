from app.models.base_model import BaseModel
from app.schemas.model_response import ModelResponse
from app.schemas.model_request import ModelRequest
from typing import Any
from openai import OpenAI


class OpenAIModel(BaseModel):
    def __init__(self,model_name:str,api_key:str,base_url:str|None=None,organization:str|None = None,**kwargs):
        super().__init__(model_name = model_name,api_key=api_key,**kwargs)
        self._base_url = base_url
        self._organization = organization
        self._client = OpenAI(api_key=self._api_key,base_url=self._base_url,organization = self._organization)
    def validate_config(self)->None:
        super().validate_config()
        if not self._api_key:
            raise ValueError("api_key is empty")
    def generate(self,input_data:ModelRequest,**kwargs:Any)->ModelResponse:
        if not input_data.prompt.strip():
            return ModelResponse(
                content=None,
                success=False,
                error_message="prompt 不能为空",
                metadata={"model_name":self._model_name}
                )
        try:
            response = self._client.chat.completions.create(
                model=self._model_name,
                messages=[{"role": "user", "content": input_data.prompt}],
            )
            content = response.choices[0].message.content or ""
            return ModelResponse(
                content=content,
                success=True,
                metadata={"model_name": self._model_name},
            )
        except Exception as e:
            return ModelResponse(
                content=None,
                success=False,
                error_message=str(e),
                metadata={"model_name": self._model_name},
            )

        
