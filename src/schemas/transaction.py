from pydantic import BaseModel, Field


class StatementItem(BaseModel):
    transaction_id: str = Field(alias="id")
    time: int
    description: str
    mcc: int
    original_mcc: int = Field(alias="originalMcc")
    amount: int
    operation_amount: int = Field(alias="operationAmount")
    currency_code: int = Field(alias="currencyCode")
    commission_rate: int = Field(alias="commissionRate", default=0)
    cashback_amount: int = Field(alias="cashbackAmount", default=0)
    balance: int
    hold: bool = False
    comment: str | None = None
    receipt_id: str | None = Field(alias="receiptId", default=None)
    counter_edrpou: str | None = Field(alias="counterEdrpou", default=None)
    counter_iban: str | None = Field(alias="counterIban", default=None)
    counter_name: str | None = Field(alias="counterName", default=None)


class WebhookData(BaseModel):
    account: str
    statement_item: StatementItem = Field(alias="statementItem")


class WebhookPayload(BaseModel):
    type: str
    data: WebhookData
