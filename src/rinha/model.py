from pydantic import BaseModel, field_validator

class TransacaoIn(BaseModel):
    valor: int
    tipo: str
    descricao: str

    @field_validator("tipo")
    @classmethod
    def valid_type(cls, v):
        if v not in {"c", "d"}:
            raise ValueError("tipo must be 'c' (credit) or 'd' (debit)")
        return v

    @field_validator("descricao")
    @classmethod
    def short_description(cls, v):
        if not (1 <= len(v) <= 10):
            raise ValueError("descricao must be between 1 and 10 characters")
        return v
