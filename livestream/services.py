from livekit.api import AccessToken, VideoGrants
from datetime import timedelta
from django.conf import settings
import json  # ✅ ADD THIS

def generate_livekit_token(user, session, is_teacher=False):
    token = AccessToken(
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET,
    )

    # ✅ identity (keep ID for tracking)
    token.with_identity(str(user.id))

    # ✅ proper display name (IMPORTANT)
    token.with_name(user.get_full_name() or user.username)

    # ✅ ADD METADATA (CRITICAL FIX)
    token.with_metadata(json.dumps({
        "role": "teacher" if is_teacher else "student",
        "user_id": str(user.id),
    }))

    # ✅ expiry
    token.with_ttl(timedelta(minutes=10))

    grants = VideoGrants(
        room_join=True,
        room=session.room_name,
        can_publish=is_teacher,
        can_subscribe=True,
    )

    token.with_grants(grants)

    return token.to_jwt()