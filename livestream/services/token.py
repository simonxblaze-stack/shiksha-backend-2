import json
from datetime import timedelta

from django.conf import settings
from livekit.api import AccessToken, VideoGrants


def generate_livekit_token(
    user,
    session,
    is_teacher=False,
    display_name=None,
    allow_publish=None,
):
    token = AccessToken(
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET,
    )

    token.with_identity(str(user.id))

    # Resolve display name
    if display_name is None:
        profile = getattr(user, "profile", None)
        if profile and getattr(profile, "full_name", None):
            display_name = profile.full_name
        else:
            display_name = user.get_full_name() or user.username

    token.with_name(display_name)

    # ✅ safer metadata (future-proof)
    token.with_metadata(json.dumps({
        "role": "teacher" if is_teacher else "student",
        "user_id": str(user.id),
    }, default=str))

    # ✅ FIX: increase TTL (important for reconnections)
    token.with_ttl(timedelta(hours=2))

    # ✅ FIX: safe room name fallback
    room_name = getattr(session, "room_name", None)
    if not room_name:
        raise ValueError("Session has no room_name")

    # Teachers: full publish
    if allow_publish is not None:
        can_publish = allow_publish
    else:
        can_publish = is_teacher

    if can_publish:
        grants = VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
    else:
        # ✅ FIX: safer for compatibility
        grants = VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,  # still needed for mic
            can_subscribe=True,
        )

    token.with_grants(grants)

    return token.to_jwt()
