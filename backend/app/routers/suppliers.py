from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SupplierBrief, SupplierResponse
from app.services import supplier_service

router = APIRouter(prefix="/api/v1/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierBrief])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    return await supplier_service.list_suppliers(db)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: str, db: AsyncSession = Depends(get_db)):
    supplier = await supplier_service.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier
