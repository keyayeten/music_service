from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_current_identity_user, get_db_session, get_moderation_report_use_cases
from backend.api.v1.schemas.reports import CreateReportRequest, ListReportsResponse, ReportResponse, UpdateReportStatusRequest
from backend.application.moderation.use_cases.reports import ModerationReportUseCases
from backend.domain.common.exceptions import AuthorizationError, ValidationError
from backend.domain.identity.repositories import IdentityUserReadModel
from backend.domain.moderation.repositories import ReportReadModel

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: CreateReportRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: ModerationReportUseCases = Depends(get_moderation_report_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    try:
        result = await use_cases.create_report(
            user.id,
            target_type=payload.target_type,
            target_id=UUID(payload.target_id),
            reason=payload.reason,
        )
        await db_session.commit()
    except ValueError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", "Target id should be a valid UUID value.") from exc
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    except IntegrityError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_409_CONFLICT, "conflict_error", "Report constraints violated.") from exc
    return _to_report_response(result)


@router.get("", response_model=ListReportsResponse)
async def list_reports(
    status_filter: str | None = Query(default=None, alias="status"),
    target_type: str | None = Query(default=None),
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: ModerationReportUseCases = Depends(get_moderation_report_use_cases),
) -> ListReportsResponse:
    try:
        reports = await use_cases.list_reports(user.id, status=status_filter, target_type=target_type)
    except ValidationError as exc:
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return ListReportsResponse(items=[_to_report_response(item) for item in reports])


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: ModerationReportUseCases = Depends(get_moderation_report_use_cases),
) -> ReportResponse:
    try:
        report = await use_cases.get_report(user.id, report_id=report_id)
    except ValidationError as exc:
        raise _http_error(status.HTTP_404_NOT_FOUND, "not_found", exc.message) from exc
    except AuthorizationError as exc:
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_report_response(report)


@router.post("/{report_id}/status", response_model=ReportResponse)
async def update_report_status(
    report_id: UUID,
    payload: UpdateReportStatusRequest,
    user: IdentityUserReadModel = Depends(get_current_identity_user),
    use_cases: ModerationReportUseCases = Depends(get_moderation_report_use_cases),
    db_session: AsyncSession = Depends(get_db_session),
) -> ReportResponse:
    try:
        result = await use_cases.set_report_status(user.id, report_id=report_id, target_status=payload.status)
        await db_session.commit()
    except ValidationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_400_BAD_REQUEST, "validation_error", exc.message) from exc
    except AuthorizationError as exc:
        await db_session.rollback()
        raise _http_error(status.HTTP_403_FORBIDDEN, "authorization_error", exc.message) from exc
    return _to_report_response(result.report)


def _to_report_response(item: ReportReadModel) -> ReportResponse:
    return ReportResponse(
        id=str(item.id),
        reporter_user_id=str(item.reporter_user_id),
        target_type=item.target_type,
        target_id=str(item.target_id),
        reason=item.reason,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _http_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
