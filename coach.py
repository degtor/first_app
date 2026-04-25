"""
Strava Training Coach
Usage: python coach.py [--entity ENTITY_ID] [--week-start YYYY-MM-DD]

Connects to Strava via Composio, fetches recent activities, and uses Claude
to generate a personalised weekly training plan stored in Supabase.

Before first run:
  pip install -r requirements.txt
  composio add strava -e <entity_id>
  Apply schema.sql to your Supabase project.
"""

import argparse
import json
import os
import re
from datetime import date, timedelta

import anthropic
from composio_anthropic import App, ComposioToolSet
from dotenv import load_dotenv

import db

load_dotenv()

SYSTEM_PROMPT = """You are an expert endurance training coach with deep knowledge of
periodisation, heart-rate zones, and recovery science. You have access to the athlete's
Strava data via tools. When asked for a training plan:

1. Call the Strava tools to fetch the athlete's profile and recent activities.
2. Identify current fitness level, weekly volume, intensity distribution, and any
   signs of over- or under-training.
3. Produce a concrete 7-day training plan (Mon–Sun) tailored to the data, with each
   session including: type, duration, intensity zone, and a brief rationale.
4. Finish with a JSON block (delimited by ```json and ```) containing the plan in this
   structure:
   {
     "week_start": "YYYY-MM-DD",
     "sessions": [
       {"day": "Monday", "type": "Easy Run", "duration_min": 45,
        "zone": "Z2", "notes": "..."},
       ...
     ],
     "weekly_notes": "..."
   }
"""


def next_monday() -> str:
    today = date.today()
    days_ahead = (7 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days_ahead)).isoformat()


def extract_json_plan(text: str) -> dict | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def run_coach(entity_id: str, week_start: str) -> None:
    toolset = ComposioToolSet(
        api_key=os.environ["COMPOSIO_API_KEY"],
        entity_id=entity_id,
    )
    tools = toolset.get_tools(apps=[App.STRAVA])

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages = [
        {
            "role": "user",
            "content": (
                f"Please analyse my recent Strava training and build a weekly plan "
                f"starting {week_start}. Fetch my profile and last 20 activities first."
            ),
        }
    ]

    print(f"Coaching session started | entity={entity_id} | week={week_start}\n")

    # Agentic loop — keep going until Claude stops calling tools
    while True:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Collect assistant turn (may contain tool_use blocks)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        # Execute tool calls via Composio and append results
        tool_results = toolset.handle_tool_calls(response)
        messages.append({"role": "user", "content": tool_results})

    # Extract the final text from the last assistant message
    final_text = "\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )
    print(final_text)

    # Persist to Supabase
    # We don't have the Strava athlete ID here without parsing tool results,
    # so use entity_id as a stable key with a sentinel strava_id of 0 for now.
    athlete = db.upsert_athlete(
        strava_id=hash(entity_id) & 0x7FFFFFFF,  # stable placeholder until real ID is parsed
        name=entity_id,
        entity_id=entity_id,
    )
    session_id = db.create_session(athlete["id"])

    plan_json = extract_json_plan(final_text)
    if plan_json:
        db.save_plan(athlete["id"], session_id, week_start, plan_json)

    summary = final_text[:500]
    db.close_session(session_id, summary)
    print("\nSession saved to Supabase.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Strava AI Training Coach")
    parser.add_argument(
        "--entity",
        default=os.environ.get("COMPOSIO_ENTITY_ID", "default"),
        help="Composio entity ID for the athlete",
    )
    parser.add_argument(
        "--week-start",
        default=next_monday(),
        help="Start date of the training week (YYYY-MM-DD, default: next Monday)",
    )
    args = parser.parse_args()
    run_coach(args.entity, args.week_start)


if __name__ == "__main__":
    main()
