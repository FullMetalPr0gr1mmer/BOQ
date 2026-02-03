"""
Price Book API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Optional
import os
import csv
import io
from pathlib import Path
from datetime import datetime
import logging

from Schemas.BOQ.PriceBookSchema import (
    PriceBookResponse,
    PriceBookListResponse,
    PriceBookCreate,
    PriceBookUpdate
)
from APIs.Core import get_current_user, get_db
from Models.Admin.User import User
from Models.BOQ.PriceBook import PriceBook
from utils.file_validation import validate_csv_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/price-books", tags=["Price Books"])

# Use absolute path based on the backend directory location
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads" / "price_books"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_price_book_csv(
    csv_file: UploadFile = File(..., description="Price Book CSV file"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload Price Book data from CSV file.
    CSV should contain columns matching the Price Book fields.
    """
    # Validate CSV file
    await validate_csv_file(csv_file, max_size=50 * 1024 * 1024)  # 50 MB limit

    try:
        # Read CSV content
        content = await csv_file.read()

        # Try multiple encodings
        csv_text = None
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'windows-1252', 'cp1252', 'iso-8859-1']:
            try:
                csv_text = content.decode(encoding)
                logger.info(f"Successfully decoded CSV with encoding: {encoding}")
                break
            except UnicodeDecodeError:
                continue

        if csv_text is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode CSV file. Please ensure the file is in a supported encoding (UTF-8, Latin-1, Windows-1252)"
            )

        csv_reader = csv.DictReader(io.StringIO(csv_text))

        # Normalize column names (strip whitespace and handle case variations)
        fieldnames = [field.strip() for field in csv_reader.fieldnames] if csv_reader.fieldnames else []

        records_created = 0
        errors = []
        bulk_records = []

        # Parse CSV and prepare records for bulk insert
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (1 is header)
            try:
                # Create normalized row dict
                normalized_row = {key.strip(): value.strip() if value else None for key, value in row.items()}

                # Prepare record dict for bulk insert
                record = {
                    'project_name': normalized_row.get('Project Name') or normalized_row.get('project_name'),
                    'merge_poline_uplline': normalized_row.get('Merge POLine#UPLLine#') or normalized_row.get('merge_poline_uplline'),
                    'po_number': normalized_row.get('PO#') or normalized_row.get('po_number'),
                    'customer_item_type': normalized_row.get('*Customer Item Type') or normalized_row.get('Customer Item Type') or normalized_row.get('customer_item_type'),
                    'local_content': normalized_row.get('Local Content') or normalized_row.get('local_content'),
                    'scope': normalized_row.get('Scope') or normalized_row.get('scope'),
                    'sub_scope': normalized_row.get('Sub Scope') or normalized_row.get('sub_scope'),
                    'po_line': normalized_row.get('PO line') or normalized_row.get('PO Line') or normalized_row.get('po_line'),
                    'upl_line': normalized_row.get('UPL Line') or normalized_row.get('upl_line'),
                    'merge_po_poline_uplline': normalized_row.get('Merge PO#, POLine#, UPLLine#') or normalized_row.get('merge_po_poline_uplline'),
                    'vendor_part_number_item_code': normalized_row.get('Vendor Part Number (Item Code)') or normalized_row.get('vendor_part_number_item_code'),
                    'po_line_item_description': normalized_row.get('PO Line Item Description') or normalized_row.get('po_line_item_description'),
                    'zain_item_category': normalized_row.get('Zain Item Category (Reference Categories Sheet)') or normalized_row.get('zain_item_category'),
                    'serialized': normalized_row.get('Serialized (when delivered will have serial no)') or normalized_row.get('serialized'),
                    'active_or_passive': normalized_row.get('Active or Passive') or normalized_row.get('active_or_passive'),
                    'uom': normalized_row.get('UOM') or normalized_row.get('uom'),
                    'quantity': normalized_row.get('*Quantity') or normalized_row.get('Quantity') or normalized_row.get('quantity'),
                    'unit': normalized_row.get('Unit') or normalized_row.get('unit'),
                    'currency': normalized_row.get('*Currency') or normalized_row.get('Currency') or normalized_row.get('currency'),
                    'discount': normalized_row.get('Discount') or normalized_row.get('discount'),
                    'unit_price_before_discount': normalized_row.get('*Unit Price before discount') or normalized_row.get('Unit Price before discount') or normalized_row.get('unit_price_before_discount'),
                    'po_total_amt_before_discount': normalized_row.get('PO Total amt before discount') or normalized_row.get('po_total_amt_before_discount'),
                    'special_discount': normalized_row.get('Special Discount given for this project only (% on),not applicable for future reference') or normalized_row.get('special_discount'),
                    'claimed_percentage_after_special_discount': normalized_row.get('Claimed percentage after Special Discount Unit Price(SAR)  given for this project only (% on), not applicable for future reference') or normalized_row.get('claimed_percentage_after_special_discount'),
                    'unit_price_sar_after_special_discount': normalized_row.get('Unit Price(SAR) after Special Discount for this project only (% on), not applicable for future reference') or normalized_row.get('unit_price_sar_after_special_discount'),
                    'old_up': normalized_row.get('old UP') or normalized_row.get('old_up'),
                    'delta': normalized_row.get('Delta') or normalized_row.get('delta'),
                    'final_total_price_after_discount': normalized_row.get('Final Total Price After Discount') or normalized_row.get('final_total_price_after_discount'),
                    'fv_percent_as_per_rrb': normalized_row.get('FV % as per RRB') or normalized_row.get('fv_percent_as_per_rrb'),
                    'fv': normalized_row.get('FV') or normalized_row.get('fv'),
                    'total_fv_sar': normalized_row.get('Total FV SAR') or normalized_row.get('total_fv_sar'),
                    'revised_fv_percent': normalized_row.get('Revised FV%') or normalized_row.get('revised_fv_percent'),
                    'fv_unit_price_after_descope': normalized_row.get('FV Unit Price after Descope') or normalized_row.get('fv_unit_price_after_descope'),
                    'to_go_contract_price_eur': normalized_row.get('To Go Contract Price Eur') or normalized_row.get('to_go_contract_price_eur'),
                    'r_ssp_eur': normalized_row.get('R SSP Eur') or normalized_row.get('r_ssp_eur'),
                    'uploaded_by': current_user.id,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }

                bulk_records.append(record)
                records_created += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                logger.error(f"Error processing row {row_num}: {e}")

        # Bulk insert all records at once for better performance
        if bulk_records:
            db.bulk_insert_mappings(PriceBook, bulk_records)
            db.commit()

        logger.info(f"Price Book upload: {records_created} records created by user {current_user.id}")

        result = {
            "message": f"Successfully uploaded {records_created} price book records",
            "records_created": records_created,
            "total_rows": row_num - 1 if 'row_num' in locals() else 0
        }

        if errors:
            result["errors"] = errors[:10]  # Return first 10 errors
            result["total_errors"] = len(errors)

        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Price Book upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading CSV: {str(e)}"
        )


@router.get("/", response_model=PriceBookListResponse)
async def list_price_books(
    search: Optional[str] = None,
    po_number: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List price books with optional filtering"""
    # Validate pagination parameters
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 1000:
        page_size = 50

    query = db.query(PriceBook)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (PriceBook.project_name.like(search_pattern)) |
            (PriceBook.po_number.like(search_pattern)) |
            (PriceBook.vendor_part_number_item_code.like(search_pattern))
        )

    if po_number:
        query = query.filter(PriceBook.po_number == po_number)

    # Use more efficient count query
    total = query.with_entities(func.count(PriceBook.id)).scalar()

    # Eager load uploader relationship to prevent N+1 queries
    items = query.options(joinedload(PriceBook.uploader)).order_by(
        PriceBook.created_at.desc()
    ).offset((page - 1) * page_size).limit(page_size).all()

    # Build response items efficiently
    response_items = [
        PriceBookResponse(
            id=item.id,
            project_name=item.project_name,
            merge_poline_uplline=item.merge_poline_uplline,
            po_number=item.po_number,
            customer_item_type=item.customer_item_type,
            local_content=item.local_content,
            scope=item.scope,
            sub_scope=item.sub_scope,
            po_line=item.po_line,
            upl_line=item.upl_line,
            merge_po_poline_uplline=item.merge_po_poline_uplline,
            vendor_part_number_item_code=item.vendor_part_number_item_code,
            po_line_item_description=item.po_line_item_description,
            zain_item_category=item.zain_item_category,
            serialized=item.serialized,
            active_or_passive=item.active_or_passive,
            uom=item.uom,
            quantity=item.quantity,
            unit=item.unit,
            currency=item.currency,
            discount=item.discount,
            unit_price_before_discount=item.unit_price_before_discount,
            po_total_amt_before_discount=item.po_total_amt_before_discount,
            special_discount=item.special_discount,
            claimed_percentage_after_special_discount=item.claimed_percentage_after_special_discount,
            unit_price_sar_after_special_discount=item.unit_price_sar_after_special_discount,
            old_up=item.old_up,
            delta=item.delta,
            final_total_price_after_discount=item.final_total_price_after_discount,
            fv_percent_as_per_rrb=item.fv_percent_as_per_rrb,
            fv=item.fv,
            total_fv_sar=item.total_fv_sar,
            revised_fv_percent=item.revised_fv_percent,
            fv_unit_price_after_descope=item.fv_unit_price_after_descope,
            to_go_contract_price_eur=item.to_go_contract_price_eur,
            r_ssp_eur=item.r_ssp_eur,
            uploaded_by=item.uploaded_by,
            uploader_name=item.uploader.username if item.uploader else None,
            created_at=item.created_at,
            updated_at=item.updated_at
        )
        for item in items
    ]

    return PriceBookListResponse(
        items=response_items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/po-numbers")
async def get_unique_po_numbers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of unique PO numbers"""
    po_numbers = db.query(PriceBook.po_number).filter(
        PriceBook.po_number.isnot(None),
        PriceBook.po_number != ''
    ).distinct().order_by(PriceBook.po_number).all()

    return [po[0] for po in po_numbers]


@router.get("/export/csv")
async def export_price_books_csv(
    po_number: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export price books as CSV with optional PO number filter"""
    def generate_csv():
        """Generator function for streaming CSV export"""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'ID', 'Project Name', 'Merge POLine#UPLLine#', 'PO#', '*Customer Item Type', 'Local Content',
            'Scope', 'Sub Scope', 'PO line', 'UPL Line', 'Merge PO#, POLine#, UPLLine#',
            'Vendor Part Number (Item Code)', 'PO Line Item Description',
            'Zain Item Category (Reference Categories Sheet)', 'Serialized (when delivered will have serial no)',
            'Active or Passive', 'UOM', '*Quantity', 'Unit', '*Currency', 'Discount',
            '*Unit Price before discount', 'PO Total amt before discount', 'Special Discount',
            'Claimed percentage after Special Discount', 'Unit Price(SAR) after Special Discount',
            'old UP', 'Delta', 'Final Total Price After Discount', 'FV % as per RRB', 'FV',
            'Total FV SAR', 'Revised FV%', 'FV Unit Price after Descope', 'To Go Contract Price Eur',
            'R SSP Eur', 'Uploaded By', 'Created At'
        ])
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        # Build query with optional filter
        query = db.query(PriceBook).order_by(PriceBook.created_at.desc())
        if po_number:
            query = query.filter(PriceBook.po_number == po_number)

        # Stream rows in batches for memory efficiency
        batch_size = 1000
        offset = 0

        while True:
            items = query.limit(batch_size).offset(offset).all()
            if not items:
                break

            for item in items:
                writer.writerow([
                    item.id,
                    item.project_name,
                    item.merge_poline_uplline,
                    item.po_number,
                    item.customer_item_type,
                    item.local_content,
                    item.scope,
                    item.sub_scope,
                    item.po_line,
                    item.upl_line,
                    item.merge_po_poline_uplline,
                    item.vendor_part_number_item_code,
                    item.po_line_item_description,
                    item.zain_item_category,
                    item.serialized,
                    item.active_or_passive,
                    item.uom,
                    item.quantity,
                    item.unit,
                    item.currency,
                    item.discount,
                    item.unit_price_before_discount,
                    item.po_total_amt_before_discount,
                    item.special_discount,
                    item.claimed_percentage_after_special_discount,
                    item.unit_price_sar_after_special_discount,
                    item.old_up,
                    item.delta,
                    item.final_total_price_after_discount,
                    item.fv_percent_as_per_rrb,
                    item.fv,
                    item.total_fv_sar,
                    item.revised_fv_percent,
                    item.fv_unit_price_after_descope,
                    item.to_go_contract_price_eur,
                    item.r_ssp_eur,
                    item.uploaded_by,
                    item.created_at.strftime('%Y-%m-%d %H:%M:%S') if item.created_at else ''
                ])

            yield output.getvalue()
            output.truncate(0)
            output.seek(0)
            offset += batch_size

    filename = f"price_books_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/by-po-number/{po_number}")
async def delete_by_po_number(
    po_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all price book records for a specific PO number"""
    try:
        deleted_count = db.query(PriceBook).filter(PriceBook.po_number == po_number).delete(synchronize_session=False)
        db.commit()

        logger.info(f"Deleted {deleted_count} price book records for PO# {po_number} by user {current_user.id}")

        return {"success": True, "message": f"Deleted {deleted_count} price book records for PO# {po_number}", "deleted_count": deleted_count}

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting PO# {po_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting price book records: {str(e)}"
        )


@router.get("/{price_book_id}", response_model=PriceBookResponse)
async def get_price_book(
    price_book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get single price book record by ID"""
    price_book = db.query(PriceBook).options(
        joinedload(PriceBook.uploader)
    ).filter(PriceBook.id == price_book_id).first()

    if not price_book:
        raise HTTPException(status_code=404, detail="Price book record not found")

    return PriceBookResponse(
        id=price_book.id,
        project_name=price_book.project_name,
        merge_poline_uplline=price_book.merge_poline_uplline,
        po_number=price_book.po_number,
        customer_item_type=price_book.customer_item_type,
        local_content=price_book.local_content,
        scope=price_book.scope,
        sub_scope=price_book.sub_scope,
        po_line=price_book.po_line,
        upl_line=price_book.upl_line,
        merge_po_poline_uplline=price_book.merge_po_poline_uplline,
        vendor_part_number_item_code=price_book.vendor_part_number_item_code,
        po_line_item_description=price_book.po_line_item_description,
        zain_item_category=price_book.zain_item_category,
        serialized=price_book.serialized,
        active_or_passive=price_book.active_or_passive,
        uom=price_book.uom,
        quantity=price_book.quantity,
        unit=price_book.unit,
        currency=price_book.currency,
        discount=price_book.discount,
        unit_price_before_discount=price_book.unit_price_before_discount,
        po_total_amt_before_discount=price_book.po_total_amt_before_discount,
        special_discount=price_book.special_discount,
        claimed_percentage_after_special_discount=price_book.claimed_percentage_after_special_discount,
        unit_price_sar_after_special_discount=price_book.unit_price_sar_after_special_discount,
        old_up=price_book.old_up,
        delta=price_book.delta,
        final_total_price_after_discount=price_book.final_total_price_after_discount,
        fv_percent_as_per_rrb=price_book.fv_percent_as_per_rrb,
        fv=price_book.fv,
        total_fv_sar=price_book.total_fv_sar,
        revised_fv_percent=price_book.revised_fv_percent,
        fv_unit_price_after_descope=price_book.fv_unit_price_after_descope,
        to_go_contract_price_eur=price_book.to_go_contract_price_eur,
        r_ssp_eur=price_book.r_ssp_eur,
        uploaded_by=price_book.uploaded_by,
        uploader_name=price_book.uploader.username if price_book.uploader else None,
        created_at=price_book.created_at,
        updated_at=price_book.updated_at
    )


@router.put("/{price_book_id}", response_model=PriceBookResponse)
async def update_price_book(
    price_book_id: int,
    update_data: PriceBookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a price book record"""
    try:
        price_book = db.query(PriceBook).options(
            joinedload(PriceBook.uploader)
        ).filter(PriceBook.id == price_book_id).first()

        if not price_book:
            raise HTTPException(status_code=404, detail="Price book record not found")

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(price_book, key, value)

        price_book.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(price_book)

        logger.info(f"Price book {price_book_id} updated by user {current_user.id}")

        # Uploader already loaded via joinedload
        uploader = price_book.uploader

        return PriceBookResponse(
            id=price_book.id,
            project_name=price_book.project_name,
            merge_poline_uplline=price_book.merge_poline_uplline,
            po_number=price_book.po_number,
            customer_item_type=price_book.customer_item_type,
            local_content=price_book.local_content,
            scope=price_book.scope,
            sub_scope=price_book.sub_scope,
            po_line=price_book.po_line,
            upl_line=price_book.upl_line,
            merge_po_poline_uplline=price_book.merge_po_poline_uplline,
            vendor_part_number_item_code=price_book.vendor_part_number_item_code,
            po_line_item_description=price_book.po_line_item_description,
            zain_item_category=price_book.zain_item_category,
            serialized=price_book.serialized,
            active_or_passive=price_book.active_or_passive,
            uom=price_book.uom,
            quantity=price_book.quantity,
            unit=price_book.unit,
            currency=price_book.currency,
            discount=price_book.discount,
            unit_price_before_discount=price_book.unit_price_before_discount,
            po_total_amt_before_discount=price_book.po_total_amt_before_discount,
            special_discount=price_book.special_discount,
            claimed_percentage_after_special_discount=price_book.claimed_percentage_after_special_discount,
            unit_price_sar_after_special_discount=price_book.unit_price_sar_after_special_discount,
            old_up=price_book.old_up,
            delta=price_book.delta,
            final_total_price_after_discount=price_book.final_total_price_after_discount,
            fv_percent_as_per_rrb=price_book.fv_percent_as_per_rrb,
            fv=price_book.fv,
            total_fv_sar=price_book.total_fv_sar,
            revised_fv_percent=price_book.revised_fv_percent,
            fv_unit_price_after_descope=price_book.fv_unit_price_after_descope,
            to_go_contract_price_eur=price_book.to_go_contract_price_eur,
            r_ssp_eur=price_book.r_ssp_eur,
            uploaded_by=price_book.uploaded_by,
            uploader_name=uploader.username if uploader else None,
            created_at=price_book.created_at,
            updated_at=price_book.updated_at
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating price book {price_book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating price book record: {str(e)}"
        )


@router.delete("/{price_book_id}")
async def delete_price_book(
    price_book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a price book record"""
    try:
        price_book = db.query(PriceBook).filter(PriceBook.id == price_book_id).first()

        if not price_book:
            raise HTTPException(status_code=404, detail="Price book record not found")

        db.delete(price_book)
        db.commit()

        logger.info(f"Price book {price_book_id} deleted by user {current_user.id}")

        return {"success": True, "message": "Price book record deleted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting price book {price_book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting price book record: {str(e)}"
        )
