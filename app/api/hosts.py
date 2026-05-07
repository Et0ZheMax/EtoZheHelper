import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit.logger import log_event
from app.db import get_db
from app.models import Host, SshProfile, utcnow
from app.schemas import (
    DeleteResponse,
    HostCreateRequest,
    HostListResponse,
    HostResponse,
    HostUpdateRequest,
    SshProfileCreateRequest,
    SshProfileListResponse,
    SshProfileResponse,
    SshProfileUpdateRequest,
)

router = APIRouter(tags=["hosts"])


def _tags_to_json(tags: list[str]) -> str:
    return json.dumps(tags, ensure_ascii=False)


def _tags_from_json(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _host_response(host: Host) -> HostResponse:
    return HostResponse(
        id=host.id,
        name=host.name,
        hostname=host.hostname,
        port=host.port,
        os_family=host.os_family,
        tags=_tags_from_json(host.tags),
        enabled=host.enabled,
        notes=host.notes,
        ssh_profile_id=host.ssh_profile_id,
        created_at=host.created_at,
        updated_at=host.updated_at,
    )


def _profile_response(profile: SshProfile) -> SshProfileResponse:
    return SshProfileResponse(
        id=profile.id,
        name=profile.name,
        username=profile.username,
        auth_type=profile.auth_type,
        key_ref=profile.key_ref,
        password_ref=profile.password_ref,
        sudo_mode=profile.sudo_mode,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _host_or_404(db: Session, host_id: int) -> Host:
    host = db.get(Host, host_id)
    if host is None:
        raise HTTPException(status_code=404, detail="Host not found")
    return host


def _profile_or_404(db: Session, profile_id: int) -> SshProfile:
    profile = db.get(SshProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="SSH profile not found")
    return profile


def _validate_profile_reference(db: Session, profile_id: int | None) -> None:
    if profile_id is not None and db.get(SshProfile, profile_id) is None:
        raise HTTPException(status_code=422, detail="ssh_profile_id does not reference an existing SSH profile")


@router.get("/hosts", response_model=HostListResponse)
def list_hosts(
    q: str | None = Query(default=None, max_length=200),
    enabled: bool | None = Query(default=None),
    tag: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> HostListResponse:
    query = db.query(Host)
    if enabled is not None:
        query = query.filter(Host.enabled == enabled)
    hosts = query.order_by(Host.name.asc(), Host.id.asc()).all()
    if q:
        needle = q.casefold()
        hosts = [host for host in hosts if needle in host.name.casefold() or needle in host.hostname.casefold()]
    if tag:
        normalized_tag = tag.casefold()
        hosts = [host for host in hosts if normalized_tag in {item.casefold() for item in _tags_from_json(host.tags)}]
    total = len(hosts)
    return HostListResponse(items=[_host_response(host) for host in hosts[offset : offset + limit]], total=total, limit=limit, offset=offset)


@router.get("/hosts/{host_id}", response_model=HostResponse)
def get_host(host_id: int, db: Session = Depends(get_db)) -> HostResponse:
    return _host_response(_host_or_404(db, host_id))


@router.post("/hosts", response_model=HostResponse)
def create_host(payload: HostCreateRequest, db: Session = Depends(get_db)) -> HostResponse:
    _validate_profile_reference(db, payload.ssh_profile_id)
    host = Host(
        name=payload.name,
        hostname=payload.hostname,
        port=payload.port,
        os_family=payload.os_family,
        tags=_tags_to_json(payload.tags),
        enabled=payload.enabled,
        notes=payload.notes,
        ssh_profile_id=payload.ssh_profile_id,
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    log_event(db, "host_created", {"host_id": host.id, "name": host.name, "hostname": host.hostname})
    return _host_response(host)


@router.patch("/hosts/{host_id}", response_model=HostResponse)
def update_host(host_id: int, payload: HostUpdateRequest, db: Session = Depends(get_db)) -> HostResponse:
    host = _host_or_404(db, host_id)
    updates = payload.model_dump(exclude_unset=True)
    if "ssh_profile_id" in updates:
        _validate_profile_reference(db, updates["ssh_profile_id"])
    if "tags" in updates:
        host.tags = _tags_to_json(updates.pop("tags"))
    for key, value in updates.items():
        setattr(host, key, value)
    host.updated_at = utcnow()
    db.add(host)
    db.commit()
    db.refresh(host)
    log_event(db, "host_updated", {"host_id": host.id, "name": host.name})
    return _host_response(host)


@router.delete("/hosts/{host_id}", response_model=DeleteResponse)
def delete_host(host_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    host = _host_or_404(db, host_id)
    db.delete(host)
    db.commit()
    log_event(db, "host_deleted", {"host_id": host_id})
    return DeleteResponse(status="deleted", id=host_id)


@router.get("/ssh-profiles", response_model=SshProfileListResponse)
def list_ssh_profiles(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SshProfileListResponse:
    profiles = db.query(SshProfile).order_by(SshProfile.name.asc(), SshProfile.id.asc()).all()
    total = len(profiles)
    return SshProfileListResponse(items=[_profile_response(profile) for profile in profiles[offset : offset + limit]], total=total, limit=limit, offset=offset)


@router.get("/ssh-profiles/{profile_id}", response_model=SshProfileResponse)
def get_ssh_profile(profile_id: int, db: Session = Depends(get_db)) -> SshProfileResponse:
    return _profile_response(_profile_or_404(db, profile_id))


@router.post("/ssh-profiles", response_model=SshProfileResponse)
def create_ssh_profile(payload: SshProfileCreateRequest, db: Session = Depends(get_db)) -> SshProfileResponse:
    profile = SshProfile(
        name=payload.name,
        username=payload.username,
        auth_type=payload.auth_type,
        key_ref=payload.key_ref,
        password_ref=payload.password_ref,
        sudo_mode=payload.sudo_mode,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    log_event(db, "ssh_profile_created", {"profile_id": profile.id, "name": profile.name, "auth_type": profile.auth_type})
    return _profile_response(profile)


@router.patch("/ssh-profiles/{profile_id}", response_model=SshProfileResponse)
def update_ssh_profile(profile_id: int, payload: SshProfileUpdateRequest, db: Session = Depends(get_db)) -> SshProfileResponse:
    profile = _profile_or_404(db, profile_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    profile.updated_at = utcnow()
    db.add(profile)
    db.commit()
    db.refresh(profile)
    log_event(db, "ssh_profile_updated", {"profile_id": profile.id, "name": profile.name})
    return _profile_response(profile)


@router.delete("/ssh-profiles/{profile_id}", response_model=DeleteResponse)
def delete_ssh_profile(profile_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    profile = _profile_or_404(db, profile_id)
    referenced = db.query(Host).filter(Host.ssh_profile_id == profile.id).first()
    if referenced is not None:
        raise HTTPException(status_code=409, detail="SSH profile is referenced by one or more hosts")
    db.delete(profile)
    db.commit()
    log_event(db, "ssh_profile_deleted", {"profile_id": profile_id})
    return DeleteResponse(status="deleted", id=profile_id)
