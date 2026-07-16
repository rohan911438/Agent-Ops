from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Keeps Postgres org/user rows in sync with Clerk (source of truth for
    identity). Signature verification against CLERK_WEBHOOK_SECRET is left
    for the Clerk SDK integration step — this only handles the two event
    types the MVP data model cares about.
    """
    payload = await request.json()
    event_type = payload.get("type", "")
    data = payload.get("data", {})

    if event_type == "organization.created":
        org = Organization(
            name=data.get("name", ""), slug=data.get("slug", ""), clerk_org_id=data.get("id")
        )
        db.add(org)
        await db.commit()

    elif event_type == "user.created":
        org_id = data.get("organization_id")
        if org_id:
            result = await db.execute(select(Organization).where(Organization.clerk_org_id == org_id))
            org = result.scalar_one_or_none()
            if org:
                email_addresses = data.get("email_addresses", [])
                email = email_addresses[0]["email_address"] if email_addresses else ""
                user = User(
                    org_id=org.id,
                    clerk_user_id=data.get("id"),
                    email=email,
                    name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                )
                db.add(user)
                await db.commit()
