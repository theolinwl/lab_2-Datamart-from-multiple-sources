from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import json


app = FastAPI()


class Transaction(BaseModel):
    transaction_id: int
    org_id: int
    date: str
    amount: float
    currency: str


class TransactionUpdate(BaseModel):
    org_id: int | None = None
    date: str | None = None
    amount: float | None = None
    currency: str | None = None


def load_transactions():
    try:
        with open('data/raw/transactions.json', 'r') as file:
            transactions = json.load(file)
            return transactions
    except FileNotFoundError:
        return []


def save_transactions():
    with open('data/raw/transactions.json', 'w') as file:
        json.dump(transactions, file)


transactions = load_transactions()

@app.get('/api/transactions')
def get_transactions(currency: str | None = None):
    if currency is None:
        return transactions
    return [
        transaction for transaction in transactions 
        if transaction['currency'] == currency
    ]


@app.get("/api/transactions-redirect")
def redirect_transactions():
    return RedirectResponse(
        url="/api/transactions",
        status_code=307
    )


@app.get('/api/transactions/{transaction_id}')
def get_transaction(transaction_id: int):
    for transaction in transactions:
        if transaction['transaction_id'] == transaction_id:
            return transaction
    raise HTTPException(status_code=404, detail="Transaction not found")


@app.post('/api/transactions')
def create_transaction(transaction: Transaction):
    if any(t['transaction_id'] == transaction.transaction_id for t in transactions):
        raise HTTPException(status_code=400, detail="Transaction with this ID already exists")
    transactions.append(transaction.model_dump())
    save_transactions()
    return transaction


@app.put('/api/transactions/{transaction_id}')
def update_transaction(transaction_id: int, updated_transaction: Transaction):
    for index, transaction in enumerate(transactions):
        if transaction['transaction_id'] == transaction_id:
            updated_transaction.transaction_id = transaction_id
            transactions[index] = updated_transaction.model_dump()
            save_transactions() 
            return updated_transaction.model_dump()

    raise HTTPException(status_code=404, detail="Transaction not found")


@app.patch('/api/transactions/{transaction_id}')
def patch_transaction(transaction_id: int, updated_fields: TransactionUpdate):
    for index, transaction in enumerate(transactions):
        if transaction['transaction_id'] == transaction_id:
            data = transaction.copy()
            updated_data = updated_fields.model_dump(exclude_unset=True)
            data.update(updated_data)

            updated_transaction = Transaction(**data)
            transactions[index] = updated_transaction.model_dump()
            save_transactions()
            return updated_transaction
    
    raise HTTPException(status_code=404, detail="Transaction not found")


@app.delete('/api/transactions/{transaction_id}')
def delete_transaction(transaction_id: int):
    for index, transaction in enumerate(transactions):
        if transaction['transaction_id'] == transaction_id:
            del transactions[index]
            save_transactions()
            return {"message": "Transaction deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Transaction not found")