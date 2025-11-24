from pydantic import BaseModel
from typing import List, Optional


class Create5GRolloutSheet(BaseModel):
    """Schema for creating a new 5G Rollout Sheet entry."""
    site_id: str
    scope: Optional[str] = None
    year_target_scope: Optional[str] = None
    partner: Optional[str] = None
    partner_requester_name: Optional[str] = None
    date_of_partner_request: Optional[str] = None
    survey_partner: Optional[str] = None
    implementation_partner: Optional[str] = None
    ant_swap: Optional[str] = None
    additional_cost: Optional[str] = None
    wr_transportation: Optional[str] = None
    crane: Optional[str] = None
    ac_armod_cable_new_sran: Optional[str] = None
    military_factor: Optional[str] = None
    cicpa_factor: Optional[str] = None
    nokia_rollout_requester: Optional[str] = None
    services_validation_by_rollout: Optional[str] = None
    date_of_validation_by_rollout: Optional[str] = None
    request_status: Optional[str] = None
    du_po_number: Optional[str] = None
    integration_status: Optional[str] = None
    integration_date: Optional[str] = None
    du_po_convention_name: Optional[str] = None
    po_year_issuance: Optional[str] = None
    smp_number: Optional[str] = None
    wo_number: Optional[str] = None
    sps_category: Optional[str] = None
    submission_date: Optional[str] = None
    po_status: Optional[str] = None
    pac_received: Optional[str] = None
    date_of_pac: Optional[str] = None
    hardware_remark: Optional[str] = None
    project_id: Optional[str] = None


class Update5GRolloutSheet(BaseModel):
    """Schema for updating an existing 5G Rollout Sheet entry."""
    site_id: Optional[str] = None
    scope: Optional[str] = None
    year_target_scope: Optional[str] = None
    partner: Optional[str] = None
    partner_requester_name: Optional[str] = None
    date_of_partner_request: Optional[str] = None
    survey_partner: Optional[str] = None
    implementation_partner: Optional[str] = None
    ant_swap: Optional[str] = None
    additional_cost: Optional[str] = None
    wr_transportation: Optional[str] = None
    crane: Optional[str] = None
    ac_armod_cable_new_sran: Optional[str] = None
    military_factor: Optional[str] = None
    cicpa_factor: Optional[str] = None
    nokia_rollout_requester: Optional[str] = None
    services_validation_by_rollout: Optional[str] = None
    date_of_validation_by_rollout: Optional[str] = None
    request_status: Optional[str] = None
    du_po_number: Optional[str] = None
    integration_status: Optional[str] = None
    integration_date: Optional[str] = None
    du_po_convention_name: Optional[str] = None
    po_year_issuance: Optional[str] = None
    smp_number: Optional[str] = None
    wo_number: Optional[str] = None
    sps_category: Optional[str] = None
    submission_date: Optional[str] = None
    po_status: Optional[str] = None
    pac_received: Optional[str] = None
    date_of_pac: Optional[str] = None
    hardware_remark: Optional[str] = None
    project_id: Optional[str] = None


class RolloutSheetOut(BaseModel):
    """Schema for returning a 5G Rollout Sheet entry."""
    id: int
    site_id: Optional[str] = None
    scope: Optional[str] = None
    year_target_scope: Optional[str] = None
    partner: Optional[str] = None
    partner_requester_name: Optional[str] = None
    date_of_partner_request: Optional[str] = None
    survey_partner: Optional[str] = None
    implementation_partner: Optional[str] = None
    ant_swap: Optional[str] = None
    additional_cost: Optional[str] = None
    wr_transportation: Optional[str] = None
    crane: Optional[str] = None
    ac_armod_cable_new_sran: Optional[str] = None
    military_factor: Optional[str] = None
    cicpa_factor: Optional[str] = None
    nokia_rollout_requester: Optional[str] = None
    services_validation_by_rollout: Optional[str] = None
    date_of_validation_by_rollout: Optional[str] = None
    request_status: Optional[str] = None
    du_po_number: Optional[str] = None
    integration_status: Optional[str] = None
    integration_date: Optional[str] = None
    du_po_convention_name: Optional[str] = None
    po_year_issuance: Optional[str] = None
    smp_number: Optional[str] = None
    wo_number: Optional[str] = None
    sps_category: Optional[str] = None
    submission_date: Optional[str] = None
    po_status: Optional[str] = None
    pac_received: Optional[str] = None
    date_of_pac: Optional[str] = None
    hardware_remark: Optional[str] = None
    project_id: Optional[str] = None

    class Config:
        from_attributes = True


class RolloutSheetPagination(BaseModel):
    """Schema for paginated 5G Rollout Sheet responses."""
    records: List[RolloutSheetOut]
    total: int

    class Config:
        from_attributes = True


class RolloutSheetStatsResponse(BaseModel):
    """Schema for 5G Rollout Sheet statistics."""
    total_items: int
    unique_sites: int
    unique_partners: int


class UploadResponse(BaseModel):
    """Schema for CSV upload response."""
    inserted: int
    updated: int
    message: str
