CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS athletes (
    id               uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    strava_athlete_id bigint UNIQUE NOT NULL,
    name             text NOT NULL,
    composio_entity_id text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS coaching_sessions (
    id         uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id uuid NOT NULL REFERENCES athletes(id),
    started_at timestamptz NOT NULL DEFAULT now(),
    ended_at   timestamptz,
    summary    text
);

CREATE TABLE IF NOT EXISTS training_plans (
    id         uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    athlete_id uuid NOT NULL REFERENCES athletes(id),
    session_id uuid NOT NULL REFERENCES coaching_sessions(id),
    week_start date NOT NULL,
    plan_json  jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
