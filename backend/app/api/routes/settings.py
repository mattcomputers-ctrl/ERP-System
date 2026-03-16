from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.settings import ShipVia, Branding, PriceList, PriceHistory, SalesTaxOption
from app.models.sales import ShipTo, Customer
from app.schemas.settings import (
    ShipViaCreate, ShipViaUpdate, ShipViaResponse,
    BrandingUpdate, BrandingResponse,
    PriceListCreate, PriceListUpdate, PriceListResponse, PriceHistoryResponse,
    ShipToCreate, ShipToUpdate, ShipToResponse,
    SalesTaxOptionCreate, SalesTaxOptionUpdate, SalesTaxOptionResponse,
)

router = APIRouter(prefix="/settings", tags=["Settings"])


# --- Ship Via ---

@router.get("/ship-vias", response_model=List[ShipViaResponse])
def list_ship_vias(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ShipVia).filter(ShipVia.is_active == True).all()


@router.get("/ship-vias/all", response_model=List[ShipViaResponse])
def list_all_ship_vias(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ShipVia).all()


@router.post("/ship-vias", response_model=ShipViaResponse, status_code=status.HTTP_201_CREATED)
def create_ship_via(
    sv_in: ShipViaCreate,
    current_user=Depends(require_permission("settings", "create")),
    db: Session = Depends(get_db),
):
    if db.query(ShipVia).filter(ShipVia.name == sv_in.name).first():
        raise HTTPException(status_code=400, detail="Ship Via name already exists")
    sv = ShipVia(**sv_in.model_dump())
    db.add(sv)
    db.commit()
    db.refresh(sv)
    return sv


@router.put("/ship-vias/{sv_id}", response_model=ShipViaResponse)
def update_ship_via(
    sv_id: int, sv_in: ShipViaUpdate,
    current_user=Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    sv = db.query(ShipVia).filter(ShipVia.id == sv_id).first()
    if not sv:
        raise HTTPException(status_code=404, detail="Ship Via not found")
    for k, v in sv_in.model_dump(exclude_unset=True).items():
        setattr(sv, k, v)
    db.commit()
    db.refresh(sv)
    return sv


@router.delete("/ship-vias/{sv_id}")
def delete_ship_via(
    sv_id: int,
    current_user=Depends(require_permission("settings", "delete")),
    db: Session = Depends(get_db),
):
    sv = db.query(ShipVia).filter(ShipVia.id == sv_id).first()
    if not sv:
        raise HTTPException(status_code=404, detail="Ship Via not found")
    sv.is_active = False
    db.commit()
    return {"detail": "Ship Via deactivated"}


# --- Branding ---

@router.get("/branding", response_model=BrandingResponse)
def get_branding(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    branding = db.query(Branding).first()
    if not branding:
        branding = Branding(company_name="My Company")
        db.add(branding)
        db.commit()
        db.refresh(branding)
    return branding


@router.put("/branding", response_model=BrandingResponse)
def update_branding(
    b_in: BrandingUpdate,
    current_user=Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    branding = db.query(Branding).first()
    if not branding:
        branding = Branding(company_name="My Company")
        db.add(branding)
        db.flush()
    for k, v in b_in.model_dump(exclude_unset=True).items():
        setattr(branding, k, v)
    db.commit()
    db.refresh(branding)
    return branding


# --- Price Lists ---

@router.get("/price-lists", response_model=List[PriceListResponse])
def list_price_lists(
    price_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    item_id: Optional[int] = None,
    current_user=Depends(require_permission("settings", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(PriceList).filter(PriceList.is_active == True)
    if price_type:
        q = q.filter(PriceList.price_type == price_type)
    if entity_id:
        q = q.filter(PriceList.entity_id == entity_id)
    if item_id:
        q = q.filter(PriceList.item_id == item_id)
    return q.all()


@router.post("/price-lists", response_model=PriceListResponse, status_code=status.HTTP_201_CREATED)
def create_price_list(
    pl_in: PriceListCreate,
    current_user=Depends(require_permission("settings", "create")),
    db: Session = Depends(get_db),
):
    pl = PriceList(**pl_in.model_dump())
    db.add(pl)
    db.flush()
    # Record price history
    history = PriceHistory(
        price_list_id=pl.id,
        item_id=pl.item_id,
        price_type=pl.price_type,
        entity_id=pl.entity_id,
        old_price=None,
        new_price=pl.unit_price,
        changed_by=current_user.id,
    )
    db.add(history)
    db.commit()
    db.refresh(pl)
    return pl


@router.put("/price-lists/{pl_id}", response_model=PriceListResponse)
def update_price_list(
    pl_id: int, pl_in: PriceListUpdate,
    current_user=Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    pl = db.query(PriceList).filter(PriceList.id == pl_id).first()
    if not pl:
        raise HTTPException(status_code=404, detail="Price list entry not found")
    old_price = pl.unit_price
    for k, v in pl_in.model_dump(exclude_unset=True).items():
        setattr(pl, k, v)
    # Record price history if price changed
    if pl_in.unit_price is not None and pl_in.unit_price != old_price:
        history = PriceHistory(
            price_list_id=pl.id,
            item_id=pl.item_id,
            price_type=pl.price_type,
            entity_id=pl.entity_id,
            old_price=old_price,
            new_price=pl_in.unit_price,
            changed_by=current_user.id,
        )
        db.add(history)
    db.commit()
    db.refresh(pl)
    return pl


@router.get("/price-history", response_model=List[PriceHistoryResponse])
def list_price_history(
    item_id: Optional[int] = None,
    entity_id: Optional[int] = None,
    price_type: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    current_user=Depends(require_permission("settings", "read")),
    db: Session = Depends(get_db),
):
    q = db.query(PriceHistory)
    if item_id:
        q = q.filter(PriceHistory.item_id == item_id)
    if entity_id:
        q = q.filter(PriceHistory.entity_id == entity_id)
    if price_type:
        q = q.filter(PriceHistory.price_type == price_type)
    return q.order_by(PriceHistory.changed_at.desc()).offset(skip).limit(limit).all()


# --- Ship-To ---

@router.get("/ship-tos", response_model=List[ShipToResponse])
def list_ship_tos(
    customer_id: Optional[int] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ShipTo).filter(ShipTo.is_active == True)
    if customer_id:
        q = q.filter(ShipTo.customer_id == customer_id)
    return q.all()


@router.post("/ship-tos", response_model=ShipToResponse, status_code=status.HTTP_201_CREATED)
def create_ship_to(
    st_in: ShipToCreate,
    current_user=Depends(require_permission("sales", "create")),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == st_in.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    st = ShipTo(**st_in.model_dump())
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


@router.get("/ship-tos/{st_id}", response_model=ShipToResponse)
def get_ship_to(st_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    st = db.query(ShipTo).filter(ShipTo.id == st_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Ship-To not found")
    return st


@router.put("/ship-tos/{st_id}", response_model=ShipToResponse)
def update_ship_to(
    st_id: int, st_in: ShipToUpdate,
    current_user=Depends(require_permission("sales", "update")),
    db: Session = Depends(get_db),
):
    st = db.query(ShipTo).filter(ShipTo.id == st_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Ship-To not found")
    for k, v in st_in.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    db.commit()
    db.refresh(st)
    return st


@router.delete("/ship-tos/{st_id}")
def delete_ship_to(
    st_id: int,
    current_user=Depends(require_permission("sales", "delete")),
    db: Session = Depends(get_db),
):
    st = db.query(ShipTo).filter(ShipTo.id == st_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="Ship-To not found")
    st.is_active = False
    db.commit()
    return {"detail": "Ship-To deactivated"}


# --- Sales Tax Options ---

@router.get("/sales-tax-options", response_model=List[SalesTaxOptionResponse])
def list_sales_tax_options(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(SalesTaxOption).filter(SalesTaxOption.is_active == True).all()


@router.post("/sales-tax-options", response_model=SalesTaxOptionResponse, status_code=status.HTTP_201_CREATED)
def create_sales_tax_option(
    data: SalesTaxOptionCreate,
    current_user=Depends(require_permission("settings", "create")),
    db: Session = Depends(get_db),
):
    if db.query(SalesTaxOption).filter(SalesTaxOption.name == data.name).first():
        raise HTTPException(status_code=400, detail="Sales tax option with this name already exists")
    obj = SalesTaxOption(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/sales-tax-options/{opt_id}", response_model=SalesTaxOptionResponse)
def update_sales_tax_option(
    opt_id: int, data: SalesTaxOptionUpdate,
    current_user=Depends(require_permission("settings", "update")),
    db: Session = Depends(get_db),
):
    obj = db.query(SalesTaxOption).filter(SalesTaxOption.id == opt_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Sales tax option not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/sales-tax-options/{opt_id}")
def delete_sales_tax_option(
    opt_id: int,
    current_user=Depends(require_permission("settings", "delete")),
    db: Session = Depends(get_db),
):
    obj = db.query(SalesTaxOption).filter(SalesTaxOption.id == opt_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Sales tax option not found")
    obj.is_active = False
    db.commit()
    return {"detail": "Sales tax option deactivated"}
