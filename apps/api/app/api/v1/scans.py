from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org
from app.database import get_db
from app.models.organization import Organization
from app.schemas.scan import GitHubScanCreate, ScanRead
from app.services import scan_service
from app.services.scan.parsers import ScanParseError

router = APIRouter(prefix="/scans", tags=["scans"])

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2MB — agent manifests are small text files


@router.get("", response_model=list[ScanRead])
async def list_scans(
    db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    return await scan_service.list_scans(db, org.id)


@router.post("/upload", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
async def upload_scan(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds the 2MB limit")
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "File must be UTF-8 text") from exc

    try:
        return await scan_service.create_upload_scan(db, org.id, file.filename or "upload.json", content)
    except ScanParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/github", response_model=ScanRead, status_code=status.HTTP_201_CREATED)
async def github_scan(
    data: GitHubScanCreate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    try:
        return await scan_service.create_github_scan(db, org.id, data.repo_url, data.github_token)
    except ScanParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("/{scan_id}/start", response_model=ScanRead, status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
    scan_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
):
    scan = await scan_service.get_scan(db, org.id, scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    try:
        return await scan_service.start_scan(db, scan, background_tasks)
    except scan_service.ScanAlreadyStartedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.get("/{scan_id}", response_model=ScanRead)
async def get_scan(
    scan_id: str, db: AsyncSession = Depends(get_db), org: Organization = Depends(get_current_org)
):
    scan = await scan_service.get_scan(db, org.id, scan_id)
    if scan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    return scan
