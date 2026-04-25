import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

_client: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"],
)


def upsert_athlete(strava_id: int, name: str, entity_id: str) -> dict:
    res = (
        _client.table("athletes")
        .upsert(
            {"strava_athlete_id": strava_id, "name": name, "composio_entity_id": entity_id},
            on_conflict="strava_athlete_id",
        )
        .execute()
    )
    return res.data[0]


def create_session(athlete_id: str) -> str:
    res = (
        _client.table("coaching_sessions")
        .insert({"athlete_id": athlete_id})
        .execute()
    )
    return res.data[0]["id"]


def close_session(session_id: str, summary: str) -> None:
    from datetime import datetime, timezone

    _client.table("coaching_sessions").update(
        {"ended_at": datetime.now(timezone.utc).isoformat(), "summary": summary}
    ).eq("id", session_id).execute()


def save_plan(athlete_id: str, session_id: str, week_start: str, plan_json: dict) -> None:
    _client.table("training_plans").insert(
        {
            "athlete_id": athlete_id,
            "session_id": session_id,
            "week_start": week_start,
            "plan_json": plan_json,
        }
    ).execute()
