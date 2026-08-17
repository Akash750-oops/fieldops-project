--
-- PostgreSQL database dump
--

\restrict aWzcgNGlUT3HZ9XVvfNgiHgh4jbAZ6qYzh7wl33pXUFQDKWDbW2WohaK7coHcwY

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: create_gps_ping_partition(timestamp with time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.create_gps_ping_partition(target_date timestamp with time zone) RETURNS void
    LANGUAGE plpgsql
    AS $$
                DECLARE
                    partition_start DATE;
                    partition_end DATE;
                    partition_name TEXT;
                    sql TEXT;
                BEGIN
                    partition_start := DATE_TRUNC('month', target_date)::DATE;
                    partition_end := (partition_start + INTERVAL '1 month')::DATE;
                    partition_name := 'gps_pings_' || TO_CHAR(partition_start, 'YYYY_MM');
                    
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM pg_class c 
                        JOIN pg_namespace n ON n.oid = c.relnamespace 
                        WHERE c.relname = partition_name
                    ) THEN
                        BEGIN
                            sql := 'CREATE TABLE ' || partition_name || ' PARTITION OF gps_pings ' ||
                                   'FOR VALUES FROM (' || quote_literal(partition_start) || ') TO (' || quote_literal(partition_end) || ')';
                            EXECUTE sql;
                        EXCEPTION WHEN OTHERS THEN
                            NULL;
                        END;
                    END IF;
                END;
                $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_state_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_state_records (
    id integer NOT NULL,
    agent_id character varying(36) NOT NULL,
    agent_type character varying(50) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    agent_version character varying(50) NOT NULL,
    state character varying(30) NOT NULL,
    correlation_id character varying(100),
    last_error character varying(500),
    safe_metadata json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: COLUMN agent_state_records.agent_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.agent_id IS 'UUID4 agent instance identifier.';


--
-- Name: COLUMN agent_state_records.agent_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.agent_type IS 'AITask value for this agent.';


--
-- Name: COLUMN agent_state_records.tenant_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.tenant_id IS 'Tenant that owns this agent.';


--
-- Name: COLUMN agent_state_records.agent_version; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.agent_version IS 'Agent implementation version.';


--
-- Name: COLUMN agent_state_records.state; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.state IS 'AgentState string value.';


--
-- Name: COLUMN agent_state_records.correlation_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.correlation_id IS 'Correlation ID from the last lifecycle event.';


--
-- Name: COLUMN agent_state_records.last_error; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.last_error IS 'Safe error summary only — no stack traces or secrets.';


--
-- Name: COLUMN agent_state_records.safe_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.safe_metadata IS 'Safe operational metadata — no customer data or secrets.';


--
-- Name: agent_state_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_state_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_state_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_state_records_id_seq OWNED BY public.agent_state_records.id;


--
-- Name: ai_brand_safety_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_brand_safety_rules (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    rule_id character varying(100) NOT NULL,
    category character varying(30) NOT NULL,
    match_type character varying(20) NOT NULL,
    pattern character varying(200) NOT NULL,
    severity character varying(20) NOT NULL,
    active boolean NOT NULL,
    case_sensitive boolean NOT NULL,
    created_by character varying(100) NOT NULL,
    updated_by character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_ai_brand_safety_category CHECK (((category)::text = ANY ((ARRAY['COMPETITOR'::character varying, 'POLITICAL'::character varying, 'OFF_BRAND'::character varying, 'BLOCKED_PHRASE'::character varying])::text[]))),
    CONSTRAINT ck_ai_brand_safety_match_type CHECK (((match_type)::text = ANY ((ARRAY['WORD'::character varying, 'PHRASE'::character varying])::text[]))),
    CONSTRAINT ck_ai_brand_safety_severity CHECK (((severity)::text = ANY ((ARRAY['INFO'::character varying, 'WARNING'::character varying, 'ERROR'::character varying, 'CRITICAL'::character varying])::text[])))
);


--
-- Name: ai_guardrail_violations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_guardrail_violations (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    correlation_id character varying(100),
    job_id character varying(100),
    agent_name character varying(100) NOT NULL,
    notification_type character varying(100),
    channel character varying(20) NOT NULL,
    checker_name character varying(100) NOT NULL,
    violation_code character varying(100) NOT NULL,
    category character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    affected_field character varying(50),
    safe_message text NOT NULL,
    safe_metadata json NOT NULL,
    pipeline_decision character varying(20) NOT NULL,
    fallback_triggered boolean NOT NULL,
    prompt_hash character varying(64) NOT NULL,
    output_hash character varying(64) NOT NULL,
    checker_latency_ms double precision NOT NULL,
    total_latency_ms double precision NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: assignment_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assignment_overrides (
    id integer NOT NULL,
    tenant_id character varying(50) NOT NULL,
    job_id integer NOT NULL,
    actor_name character varying(100) NOT NULL,
    actor_role character varying(30) NOT NULL,
    justification text NOT NULL,
    previous_technician_id integer,
    previous_technician_name character varying(100),
    new_technician_id integer NOT NULL,
    new_technician_name character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: assignment_overrides_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.assignment_overrides_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: assignment_overrides_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.assignment_overrides_id_seq OWNED BY public.assignment_overrides.id;


--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_events (
    id integer NOT NULL,
    tech_id character varying(36),
    tenant_id character varying(50) NOT NULL,
    event_type character varying(50) NOT NULL,
    old_status character varying(30),
    new_status character varying(30),
    reason text,
    created_at timestamp with time zone DEFAULT now(),
    job_id character varying(36),
    actor_id character varying(50),
    details json,
    "timestamp" timestamp with time zone,
    correlation_id character varying(36)
);


--
-- Name: audit_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_events_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_events_id_seq OWNED BY public.audit_events.id;


--
-- Name: communication_channel_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.communication_channel_configurations (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    channel character varying(50) NOT NULL,
    state character varying(20) NOT NULL,
    revision integer NOT NULL,
    updated_by character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_communication_channel_revision CHECK ((revision >= 1)),
    CONSTRAINT ck_communication_channel_state CHECK (((state)::text = ANY ((ARRAY['ENABLED'::character varying, 'DISABLED'::character varying, 'EMERGENCY_ONLY'::character varying])::text[])))
);


--
-- Name: communication_configuration_audits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.communication_configuration_audits (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    channel character varying(50) NOT NULL,
    previous_state character varying(20),
    new_state character varying(20) NOT NULL,
    previous_revision integer,
    new_revision integer NOT NULL,
    actor_id character varying(100) NOT NULL,
    actor_tenant_id character varying(50) NOT NULL,
    reason character varying(500) NOT NULL,
    correlation_id character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: customer_preference_audits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_preference_audits (
    id character varying(36) NOT NULL,
    customer_profile_id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    previous_revision integer NOT NULL,
    new_revision integer NOT NULL,
    changed_fields json NOT NULL,
    actor_id character varying(100) NOT NULL,
    actor_source character varying(50) NOT NULL,
    correlation_id character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_audit_actor_source CHECK (((actor_source)::text = ANY ((ARRAY['CUSTOMER'::character varying, 'ADMIN'::character varying, 'SYSTEM'::character varying])::text[]))),
    CONSTRAINT chk_audit_new_revision CHECK ((new_revision >= 1)),
    CONSTRAINT chk_audit_prev_revision CHECK ((previous_revision >= 0)),
    CONSTRAINT chk_audit_revision_progression CHECK ((new_revision > previous_revision))
);


--
-- Name: customer_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_profiles (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    customer_id character varying(50) NOT NULL,
    preferred_locale character varying(10) NOT NULL,
    sms_enabled boolean NOT NULL,
    email_enabled boolean NOT NULL,
    push_enabled boolean NOT NULL,
    portal_enabled boolean NOT NULL,
    revision integer NOT NULL,
    updated_by character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_customer_profiles_revision_positive CHECK ((revision >= 1))
);


--
-- Name: customer_profiles_extended; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_profiles_extended (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    full_name character varying(200) NOT NULL,
    mobile_number character varying(20) NOT NULL,
    address text,
    city character varying(100),
    state character varying(100),
    pincode character varying(10),
    company_name character varying(200),
    profile_completed boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: dispatcher_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dispatcher_alerts (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    type character varying(50) NOT NULL,
    severity character varying(20) NOT NULL,
    job_id integer NOT NULL,
    attempt_count integer NOT NULL,
    max_attempts integer NOT NULL,
    excluded_technicians json,
    recommended_action text,
    acknowledged integer,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: dispatcher_notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dispatcher_notifications (
    id integer NOT NULL,
    tech_id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: dispatcher_notifications_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dispatcher_notifications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dispatcher_notifications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dispatcher_notifications_id_seq OWNED BY public.dispatcher_notifications.id;


--
-- Name: enterprise_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enterprise_audit_logs (
    id character varying(36) NOT NULL,
    user_id character varying(36),
    user_email character varying(255),
    role character varying(30),
    tenant_id character varying(50) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    ip_address character varying(50),
    user_agent text,
    action character varying(100) NOT NULL,
    entity_type character varying(50),
    entity_id character varying(100),
    old_value json,
    new_value json,
    details json,
    correlation_id character varying(100),
    severity character varying(20) NOT NULL
);


--
-- Name: eta_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eta_history (
    id character varying(36) NOT NULL,
    job_id integer NOT NULL,
    eta timestamp with time zone NOT NULL,
    duration_minutes double precision NOT NULL,
    distance_km double precision NOT NULL,
    traffic_delay_minutes double precision,
    source_ping_id character varying(36) NOT NULL,
    calculated_at timestamp with time zone DEFAULT now(),
    tenant_id character varying(50) NOT NULL
);


--
-- Name: gps_pings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gps_pings (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    technician_id character varying(36) NOT NULL,
    job_id character varying(36) NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    accuracy double precision,
    altitude double precision,
    ip_address character varying(50),
    user_agent text,
    correlation_id character varying(36),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: gps_purge_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gps_purge_audit_logs (
    id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    job_id character varying(36),
    purge_type character varying(20) NOT NULL,
    deleted_count integer NOT NULL,
    correlation_id character varying(36),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: gps_rejected_ping_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gps_rejected_ping_logs (
    id character varying(36) NOT NULL,
    technician_id character varying(50),
    job_id character varying(36),
    reason character varying(200) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    tenant_id character varying(50) NOT NULL
);


--
-- Name: job_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_assignments (
    id integer NOT NULL,
    job_id integer NOT NULL,
    tenant_id character varying(50) NOT NULL,
    technician_id integer NOT NULL,
    rank integer NOT NULL,
    status character varying(30) NOT NULL,
    assigned_at timestamp with time zone,
    responded_at timestamp with time zone,
    is_current boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: job_assignments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_assignments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_assignments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_assignments_id_seq OWNED BY public.job_assignments.id;


--
-- Name: job_closures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.job_closures (
    id integer NOT NULL,
    job_id integer NOT NULL,
    tenant_id character varying(50) NOT NULL,
    work_summary text NOT NULL,
    before_images json,
    after_images json NOT NULL,
    labour_cost double precision NOT NULL,
    material_cost double precision NOT NULL,
    subtotal double precision NOT NULL,
    completed_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: job_closures_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.job_closures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: job_closures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.job_closures_id_seq OWNED BY public.job_closures.id;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jobs (
    id integer NOT NULL,
    tenant_id character varying(50),
    customer_name character varying(100) NOT NULL,
    location character varying(150) NOT NULL,
    issue_description text NOT NULL,
    priority character varying(20) NOT NULL,
    service_type character varying(50) NOT NULL,
    contact_number character varying(15) NOT NULL,
    preferred_service_date date NOT NULL,
    required_skill character varying(100),
    status character varying(30),
    assigned_technician_id integer,
    sla_deadline timestamp with time zone,
    attempt_count integer,
    gps_active boolean NOT NULL,
    work_report text,
    customer_id character varying(50),
    customer_email character varying(100),
    geofence_radius double precision NOT NULL,
    previous_priority character varying(20),
    bumped_at timestamp with time zone,
    site_latitude double precision,
    site_longitude double precision,
    site_address character varying(255),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    assigned_at timestamp with time zone,
    en_route_at timestamp with time zone,
    on_site_at timestamp with time zone,
    completed_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    closed_at timestamp with time zone,
    assigned_by character varying(50),
    en_route_by character varying(50),
    on_site_by character varying(50),
    completed_by character varying(50),
    cancelled_by character varying(50),
    closed_by character varying(50),
    cancellation_reason text,
    closure_reason text,
    rejection_reason text,
    rejected_at timestamp with time zone,
    rejected_by_tech_id character varying(50),
    share_token character varying(36),
    share_token_expires_at timestamp with time zone
);


--
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.jobs_id_seq OWNED BY public.jobs.id;


--
-- Name: notification_deliveries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_deliveries (
    id integer NOT NULL,
    tech_id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    job_id integer NOT NULL,
    fcm_message_id character varying(255),
    status character varying(30) NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: notification_deliveries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notification_deliveries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_deliveries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notification_deliveries_id_seq OWNED BY public.notification_deliveries.id;


--
-- Name: notification_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification_templates (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    type character varying(50) NOT NULL,
    channel character varying(20) NOT NULL,
    locale character varying(10) NOT NULL,
    format character varying(20) NOT NULL,
    title_template text,
    body_template text NOT NULL,
    version integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    variables json DEFAULT '[]'::json,
    tenant_id character varying(50) DEFAULT 'tenant-1'::character varying,
    agent_type character varying(50) DEFAULT 'CommsAgent'::character varying,
    is_deleted boolean DEFAULT false,
    deleted_at timestamp with time zone,
    deleted_by character varying(50)
);


--
-- Name: notification_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notification_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notification_templates_id_seq OWNED BY public.notification_templates.id;


--
-- Name: notifications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notifications (
    id character varying(36) NOT NULL,
    tech_id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    job_id character varying(36),
    type character varying(50) NOT NULL,
    title character varying(200) NOT NULL,
    body text,
    status character varying(20),
    action_url character varying(500),
    action_type character varying(50),
    priority character varying(20),
    created_at timestamp with time zone DEFAULT now(),
    read_at timestamp with time zone,
    dismissed_at timestamp with time zone,
    expires_at timestamp with time zone,
    notification_metadata json,
    CONSTRAINT valid_status CHECK (((status)::text = ANY ((ARRAY['UNREAD'::character varying, 'READ'::character varying, 'DISMISSED'::character varying])::text[])))
);


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id character varying(50) NOT NULL,
    name character varying(200) NOT NULL,
    slug character varying(100) NOT NULL,
    status character varying(20) NOT NULL,
    subscription_plan character varying(50) NOT NULL,
    max_users integer NOT NULL,
    max_technicians integer NOT NULL,
    max_jobs_per_month integer NOT NULL,
    settings json NOT NULL,
    contact_email character varying(255),
    contact_phone character varying(20),
    address character varying(500),
    logo_url character varying(500),
    primary_color character varying(7),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by character varying(36),
    suspended_at timestamp with time zone,
    suspended_by character varying(36),
    suspension_reason character varying(500),
    CONSTRAINT ck_organizations_plan CHECK (((subscription_plan)::text = ANY ((ARRAY['FREE'::character varying, 'STARTER'::character varying, 'PROFESSIONAL'::character varying, 'ENTERPRISE'::character varying])::text[]))),
    CONSTRAINT ck_organizations_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'SUSPENDED'::character varying, 'DELETED'::character varying])::text[])))
);


--
-- Name: override_audit_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.override_audit_events (
    id character varying(36) NOT NULL,
    event_type character varying(50) NOT NULL,
    actor_id character varying(36) NOT NULL,
    actor_role character varying(50) NOT NULL,
    actor_name character varying(200),
    job_id integer NOT NULL,
    action character varying(50) NOT NULL,
    before_state json NOT NULL,
    after_state json NOT NULL,
    justification text NOT NULL,
    reason text,
    ip_address character varying(50),
    user_agent text,
    correlation_id character varying(36),
    tenant_id character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: preference_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.preference_audit_logs (
    id integer NOT NULL,
    tenant_id character varying(50) NOT NULL,
    tech_id character varying(36) NOT NULL,
    updated_by character varying(50) NOT NULL,
    old_preferences json,
    new_preferences json NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: preference_audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.preference_audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: preference_audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.preference_audit_logs_id_seq OWNED BY public.preference_audit_logs.id;


--
-- Name: redispatch_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.redispatch_attempts (
    id integer NOT NULL,
    job_id integer NOT NULL,
    attempt_number integer NOT NULL,
    technician_id integer,
    technician_name character varying(100),
    event_type character varying(30) NOT NULL,
    reason character varying(255),
    queue_position integer DEFAULT 1,
    next_dispatch_eta timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: redispatch_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.redispatch_attempts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: redispatch_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.redispatch_attempts_id_seq OWNED BY public.redispatch_attempts.id;


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    token_hash character varying(255) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    device_info character varying(255),
    ip_address character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: scoring_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scoring_configurations (
    id integer NOT NULL,
    tenant_id character varying(50) NOT NULL,
    proximity_weight double precision,
    skill_weight double precision,
    workload_weight double precision,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: scoring_configurations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scoring_configurations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scoring_configurations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scoring_configurations_id_seq OWNED BY public.scoring_configurations.id;


--
-- Name: security_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.security_audit_logs (
    id character varying(36) NOT NULL,
    event character varying(100) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now(),
    severity character varying(20) NOT NULL,
    user_tenant character varying(50),
    attempted_channel character varying(200),
    ip_address character varying(50),
    websocket_id character varying(50),
    action_taken character varying(50),
    payload_tenant character varying(50),
    target_tenant character varying(50),
    technician_id character varying(50),
    job_id character varying(50),
    tenant_id character varying(50) NOT NULL
);


--
-- Name: service_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.service_requests (
    id integer NOT NULL,
    request_number character varying(50) NOT NULL,
    customer_user_id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    title character varying(200) NOT NULL,
    description text NOT NULL,
    service_type character varying(100),
    priority character varying(20) NOT NULL,
    preferred_visit_date date,
    images json,
    location character varying(255),
    contact_number character varying(20),
    status character varying(30) NOT NULL,
    linked_job_id integer,
    cancellation_reason text,
    cancelled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: service_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.service_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: service_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.service_requests_id_seq OWNED BY public.service_requests.id;


--
-- Name: skill_taxonomy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.skill_taxonomy (
    id character varying(50) NOT NULL,
    taxonomy_data json NOT NULL,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: sla_escalations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sla_escalations (
    id integer NOT NULL,
    tenant_id character varying(50) NOT NULL,
    job_id integer NOT NULL,
    manager_notified_at timestamp with time zone,
    manager_responded_at timestamp with time zone,
    cto_notified_at timestamp with time zone,
    action_taken character varying(100),
    status character varying(50),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: sla_escalations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sla_escalations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sla_escalations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sla_escalations_id_seq OWNED BY public.sla_escalations.id;


--
-- Name: sms_deliveries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sms_deliveries (
    id integer NOT NULL,
    tech_id character varying(36) NOT NULL,
    job_id character varying(36) NOT NULL,
    sms_sid character varying(255),
    status character varying(30) NOT NULL,
    cost double precision,
    error_message text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: sms_deliveries_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sms_deliveries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sms_deliveries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sms_deliveries_id_seq OWNED BY public.sms_deliveries.id;


--
-- Name: technician_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.technician_profiles (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    full_name character varying(200) NOT NULL,
    profile_photo text,
    mobile_number character varying(20) NOT NULL,
    date_of_birth date,
    gender character varying(20),
    address text,
    city character varying(100),
    state character varying(100),
    pincode character varying(10),
    emergency_contact character varying(100),
    skills json,
    experience character varying(200),
    certifications json,
    profile_completed boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: technicians; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.technicians (
    technician_id integer NOT NULL,
    tech_id character varying(36),
    tenant_id character varying(50),
    technician_name character varying(100) NOT NULL,
    technician_skill character varying(100) NOT NULL,
    certifications_data json,
    technician_location character varying(150) NOT NULL,
    technician_status character varying(30),
    current_jobs integer,
    max_jobs integer,
    last_ping timestamp with time zone,
    fcm_token character varying(255),
    device_type character varying(20),
    phone_number character varying(20),
    sms_opt_out integer,
    notification_preferences json,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: technicians_technician_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.technicians_technician_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: technicians_technician_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.technicians_technician_id_seq OWNED BY public.technicians.technician_id;


--
-- Name: template_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.template_versions (
    id integer NOT NULL,
    template_id integer NOT NULL,
    version_number integer NOT NULL,
    title_template text,
    body_template text NOT NULL,
    created_by character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    change_summary text,
    is_active boolean NOT NULL
);


--
-- Name: template_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.template_versions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: template_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.template_versions_id_seq OWNED BY public.template_versions.id;


--
-- Name: tenant_gps_configurations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_gps_configurations (
    tenant_id character varying(50) NOT NULL,
    retention_days integer NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT valid_retention_days CHECK (((retention_days >= 1) AND (retention_days <= 90)))
);


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants (
    id character varying(50) NOT NULL,
    name character varying(100),
    parent_tenant_id character varying(50)
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id character varying(36) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    role character varying(30) NOT NULL,
    tenant_id character varying(50) NOT NULL,
    phone_number character varying(20),
    is_active boolean NOT NULL,
    is_email_verified boolean NOT NULL,
    failed_login_attempts integer NOT NULL,
    locked_until timestamp with time zone,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by character varying(36)
);


--
-- Name: agent_state_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_state_records ALTER COLUMN id SET DEFAULT nextval('public.agent_state_records_id_seq'::regclass);


--
-- Name: assignment_overrides id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assignment_overrides ALTER COLUMN id SET DEFAULT nextval('public.assignment_overrides_id_seq'::regclass);


--
-- Name: audit_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events ALTER COLUMN id SET DEFAULT nextval('public.audit_events_id_seq'::regclass);


--
-- Name: dispatcher_notifications id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispatcher_notifications ALTER COLUMN id SET DEFAULT nextval('public.dispatcher_notifications_id_seq'::regclass);


--
-- Name: job_assignments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_assignments ALTER COLUMN id SET DEFAULT nextval('public.job_assignments_id_seq'::regclass);


--
-- Name: job_closures id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_closures ALTER COLUMN id SET DEFAULT nextval('public.job_closures_id_seq'::regclass);


--
-- Name: jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs ALTER COLUMN id SET DEFAULT nextval('public.jobs_id_seq'::regclass);


--
-- Name: notification_deliveries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_deliveries ALTER COLUMN id SET DEFAULT nextval('public.notification_deliveries_id_seq'::regclass);


--
-- Name: notification_templates id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_templates ALTER COLUMN id SET DEFAULT nextval('public.notification_templates_id_seq'::regclass);


--
-- Name: preference_audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preference_audit_logs ALTER COLUMN id SET DEFAULT nextval('public.preference_audit_logs_id_seq'::regclass);


--
-- Name: redispatch_attempts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.redispatch_attempts ALTER COLUMN id SET DEFAULT nextval('public.redispatch_attempts_id_seq'::regclass);


--
-- Name: scoring_configurations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scoring_configurations ALTER COLUMN id SET DEFAULT nextval('public.scoring_configurations_id_seq'::regclass);


--
-- Name: service_requests id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_requests ALTER COLUMN id SET DEFAULT nextval('public.service_requests_id_seq'::regclass);


--
-- Name: sla_escalations id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sla_escalations ALTER COLUMN id SET DEFAULT nextval('public.sla_escalations_id_seq'::regclass);


--
-- Name: sms_deliveries id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sms_deliveries ALTER COLUMN id SET DEFAULT nextval('public.sms_deliveries_id_seq'::regclass);


--
-- Name: technicians technician_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technicians ALTER COLUMN technician_id SET DEFAULT nextval('public.technicians_technician_id_seq'::regclass);


--
-- Name: template_versions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_versions ALTER COLUMN id SET DEFAULT nextval('public.template_versions_id_seq'::regclass);


--
-- Data for Name: agent_state_records; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.agent_state_records (id, agent_id, agent_type, tenant_id, agent_version, state, correlation_id, last_error, safe_metadata, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: ai_brand_safety_rules; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ai_brand_safety_rules (id, tenant_id, rule_id, category, match_type, pattern, severity, active, case_sensitive, created_by, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: ai_guardrail_violations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.ai_guardrail_violations (id, tenant_id, correlation_id, job_id, agent_name, notification_type, channel, checker_name, violation_code, category, severity, affected_field, safe_message, safe_metadata, pipeline_decision, fallback_triggered, prompt_hash, output_hash, checker_latency_ms, total_latency_ms, created_at) FROM stdin;
\.


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
a7b892c8d632
\.


--
-- Data for Name: assignment_overrides; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.assignment_overrides (id, tenant_id, job_id, actor_name, actor_role, justification, previous_technician_id, previous_technician_name, new_technician_id, new_technician_name, created_at) FROM stdin;
\.


--
-- Data for Name: audit_events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.audit_events (id, tech_id, tenant_id, event_type, old_status, new_status, reason, created_at, job_id, actor_id, details, "timestamp", correlation_id) FROM stdin;
1	tech-0ad0e957	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 1, Priority: MEDIUM)	2026-08-06 10:56:34.890083+05:30	\N	\N	\N	\N	\N
2	tech-0ad0e957	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 2, Priority: MEDIUM)	2026-08-06 10:58:29.876237+05:30	\N	\N	\N	\N	\N
3	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 1, Priority: HIGH)	2026-08-08 12:29:15.452741+05:30	\N	\N	\N	\N	\N
4	tech-0ad0e957	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 12:32:07.922741+05:30	\N	\N	\N	\N	\N
5	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 12:32:07.922741+05:30	\N	\N	\N	\N	\N
6	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 2, Priority: HIGH)	2026-08-08 12:32:25.458721+05:30	\N	\N	\N	\N	\N
7	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 1, Priority: MEDIUM)	2026-08-08 12:39:10.460414+05:30	\N	\N	\N	\N	\N
8	tech-0ad0e957	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 2, Priority: MEDIUM)	2026-08-08 12:47:48.979341+05:30	\N	\N	\N	\N	\N
9	tech-e8ff3055	__platform__	STATUS_CHANGE	Available	OFFLINE	\N	2026-08-08 13:00:58.96534+05:30	\N	\N	\N	\N	\N
10	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 1, Priority: MEDIUM)	2026-08-08 14:51:33.540111+05:30	\N	\N	\N	\N	\N
11	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 2, Priority: MEDIUM)	2026-08-08 14:54:58.537979+05:30	\N	\N	\N	\N	\N
12	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 1, Priority: MEDIUM)	2026-08-08 15:06:03.545091+05:30	\N	\N	\N	\N	\N
13	tech-0ad0e957	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 15:10:58.78544+05:30	\N	\N	\N	\N	\N
14	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 15:10:58.78544+05:30	\N	\N	\N	\N	\N
15	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 2, Priority: MEDIUM)	2026-08-08 15:11:13.540808+05:30	\N	\N	\N	\N	\N
16	tech-0ad0e957	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 15:12:47.854438+05:30	\N	\N	\N	\N	\N
17	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 15:12:47.854438+05:30	\N	\N	\N	\N	\N
18	tech-0ad0e957	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 16:41:01.10936+05:30	\N	\N	\N	\N	\N
19	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-08 16:41:01.10936+05:30	\N	\N	\N	\N	\N
20	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 1, Priority: MEDIUM)	2026-08-10 10:19:53.896304+05:30	\N	\N	\N	\N	\N
21	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-10 10:20:50.091542+05:30	\N	\N	\N	\N	\N
22	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	JOB_REQUEUED	ASSIGNED	QUEUED	Triggered by: timeout (Attempt: 2, Priority: MEDIUM)	2026-08-10 10:21:08.891909+05:30	\N	\N	\N	\N	\N
23	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	CERT_REJECTED	missing_skills	DISQUALIFIED	\N	2026-08-10 10:22:07.738953+05:30	\N	\N	\N	\N	\N
24	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	STATUS_CHANGE	AVAILABLE	OFFLINE	\N	2026-08-10 10:23:33.886951+05:30	\N	\N	\N	\N	\N
\.


--
-- Data for Name: communication_channel_configurations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.communication_channel_configurations (id, tenant_id, channel, state, revision, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: communication_configuration_audits; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.communication_configuration_audits (id, tenant_id, channel, previous_state, new_state, previous_revision, new_revision, actor_id, actor_tenant_id, reason, correlation_id, created_at) FROM stdin;
\.


--
-- Data for Name: customer_preference_audits; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customer_preference_audits (id, customer_profile_id, tenant_id, previous_revision, new_revision, changed_fields, actor_id, actor_source, correlation_id, created_at) FROM stdin;
\.


--
-- Data for Name: customer_profiles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customer_profiles (id, tenant_id, customer_id, preferred_locale, sms_enabled, email_enabled, push_enabled, portal_enabled, revision, updated_by, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: customer_profiles_extended; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.customer_profiles_extended (id, user_id, tenant_id, full_name, mobile_number, address, city, state, pincode, company_name, profile_completed, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: dispatcher_alerts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dispatcher_alerts (id, tenant_id, type, severity, job_id, attempt_count, max_attempts, excluded_technicians, recommended_action, acknowledged, created_at) FROM stdin;
\.


--
-- Data for Name: dispatcher_notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.dispatcher_notifications (id, tech_id, tenant_id, message, created_at) FROM stdin;
1	tech-0ad0e957	tenant-1	Job 2 assignment revoked for Dharsan. Reason: timeout.	2026-08-06 10:56:34.890083+05:30
2	tech-0ad0e957	tenant-1	Job 2 assignment revoked for Dharsan. Reason: timeout.	2026-08-06 10:58:29.876237+05:30
3	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Job 1 assignment revoked for Tom Technician. Reason: timeout.	2026-08-08 12:29:15.452741+05:30
4	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Job 1 assignment revoked for Tom Technician. Reason: timeout.	2026-08-08 12:32:25.458721+05:30
5	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Job 3 assignment revoked for Tom Technician. Reason: timeout.	2026-08-08 12:39:10.460414+05:30
6	tech-0ad0e957	tenant-1	Job 3 assignment revoked for Dharsan. Reason: timeout.	2026-08-08 12:47:48.979341+05:30
7	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Job 4 assignment revoked for Tom Technician. Reason: timeout.	2026-08-08 14:51:33.540111+05:30
8	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Job 4 assignment revoked for Tom Technician. Reason: timeout.	2026-08-08 14:54:58.537979+05:30
9	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Job 5 assignment revoked for Tom Technician. Reason: timeout.	2026-08-08 15:06:03.545091+05:30
10	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Job 5 assignment revoked for Tom Technician. Reason: timeout.	2026-08-08 15:11:13.540808+05:30
11	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	Job 6 assignment revoked for John Doe. Reason: timeout.	2026-08-10 10:19:53.896304+05:30
12	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	Job 6 assignment revoked for John Doe. Reason: timeout.	2026-08-10 10:21:08.891909+05:30
13	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	Technician John Doe (ID: eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd) has active jobs but went OFFLINE due to missing heartbeat.	2026-08-10 10:23:33.886951+05:30
\.


--
-- Data for Name: enterprise_audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.enterprise_audit_logs (id, user_id, user_email, role, tenant_id, "timestamp", ip_address, user_agent, action, entity_type, entity_id, old_value, new_value, details, correlation_id, severity) FROM stdin;
0183b599-776b-43cb-a5b4-20d8fa94c678	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-05 17:04:54.917427+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
d1949768-eb6d-4296-93a3-ed9656961763	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-05 17:14:58.479053+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
aac3347b-42f5-4748-8b19-6a164e1905ac	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-05 17:53:24.265836+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
31b7d96b-a77d-416c-aeec-42491205284c	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-05 17:53:54.994546+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
743e34e7-4ec6-4fad-9e9c-96a06c334ff4	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-05 17:54:29.510945+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5d6821bb-bb2c-4264-92a3-a52434ea326e	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-05 17:55:56.339195+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	SERVICE_REQUEST_CREATED	service_request	SR-20260805122556-DB6360	null	{"title": "Ac Mechnice", "priority": "HIGH"}	null	\N	INFO
1e96069a-a4a5-4a21-ab3f-2e3eec43ef38	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-05 17:56:21.764973+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
b59ccff4-e518-4b20-b1ab-7521e96b0e86	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-05 17:56:53.452573+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
d6abfb53-4632-4a59-bd49-5540d09589e5	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-05 17:58:53.811931+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
a8173235-eb13-4aca-9900-874ce60e074b	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-06 10:26:15.748284+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
374e226e-2910-4a54-943a-fe9968d3c0dc	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-06 10:26:26.830784+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
d0b0e425-0ab3-4e5b-a4d8-a3bb942c3c83	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-06 10:27:07.463431+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
02143275-185b-4671-8374-9d8982778271	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-06 10:40:12.380605+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
16789c38-886c-400b-9a0d-75bedc21c196	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-06 10:41:57.779746+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
13360553-3e60-4369-b64f-9179bd52e115	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-06 10:42:07.242549+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	SERVICE_REQUEST_CANCELLED	service_request	1	null	null	null	\N	INFO
0da5fc6b-c5c5-4d9d-803b-1fd6bea00030	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-06 10:43:47.271694+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	SERVICE_REQUEST_CREATED	service_request	SR-20260806051347-C7DF1F	null	{"title": "Pipe is dameged", "priority": "MEDIUM"}	null	\N	INFO
74f497ba-ee31-49e1-88e5-8a6788863b9c	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-06 10:46:35.301589+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
bd55efac-d56c-4863-91dc-1ef00d0b0320	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-06 10:46:59.912688+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
342694af-5e89-46b3-b98d-eae3bfb0cfcc	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-06 10:48:38.730742+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
0209170c-f053-4b30-a124-c40301a26eb9	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-06 10:49:48.764436+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
2915a5ef-c069-4854-931f-7c9a0dacddb7	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-06 10:49:13.664445+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
7b2dff76-d15c-469f-bde2-aeefb228ccb2	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-06 10:57:39.664072+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
1efe094a-66f6-41ea-b247-df41ec03f314	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-06 10:57:58.970972+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
ebed656e-e20a-45ee-9122-4dc6356c9987	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-06 10:50:26.193831+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
7a04cb05-22b7-43fa-8715-93fb770a3cda	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-06 10:56:46.376494+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
e1a30dd9-ae7f-429d-a687-f948386ceb4b	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-06 10:57:22.006537+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
09e04472-2a04-4dc8-a87b-2e54def0b2e0	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-07 15:37:29.88626+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
cdf61f59-fb27-456f-a02f-360210c3570d	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-07 15:38:05.97605+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
376c424b-7a64-4bf0-8939-e004d53ee902	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-07 15:40:43.728332+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	PROFILE_CREATED	technician_profile	8ce69d3c-ca31-417d-badb-1dfc8b523c80	null	{"full_name": "Tom Technician"}	null	\N	INFO
8001b83f-2815-41f4-a07a-5df29e8b6b57	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-07 17:46:00.926959+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
97271f16-1288-4691-833b-c1513759ce87	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-07 17:59:23.927089+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
4fece37e-ca2d-4a2f-8151-73a40ee93d72	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-07 18:03:30.572585+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
a5ff7bc2-4eb0-4f46-aaaa-5ca30716aeaa	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-07 18:26:22.166933+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
915b7049-3544-4348-98d4-0701aaf1d402	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-07 18:27:05.569175+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
6cf0774e-043a-47fb-a701-13172a8ce0b3	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-07 18:31:56.362777+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	SERVICE_REQUEST_CANCELLED	service_request	2	null	null	null	\N	INFO
029723c4-ac0a-419a-9787-f9b0aadec4a2	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-07 18:41:23.804227+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
9f7c0e6f-729f-4198-9e2e-b9692054b3f8	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-07 18:42:06.571149+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5a09bc83-b1b8-4aa5-bb50-2bde8e63a913	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 09:42:45.466782+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.132.0 Chrome/148.0.7778.280 Electron/42.7.1 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
38af9ccf-5c4d-4cf3-be5b-5c7dea91ce26	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 10:09:15.893587+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
de470daf-af20-45ba-84f7-3d2c00259b52	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 10:39:41.803708+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	PROFILE_UPDATED	technician_profile	8ce69d3c-ca31-417d-badb-1dfc8b523c80	{"full_name": "Tom Technician", "mobile_number": "966886869966060", "date_of_birth": "2003-06-12", "gender": "Male", "address": "Chennai Kodambakkam", "city": "Chennai", "state": "Tamilnadu", "pincode": "700012", "emergency_contact": "8474748493338383737", "skills": ["Plumbing", "Network Support"], "experience": "2 years", "certifications": [], "profile_photo": ""}	{"full_name": "Tom Technician", "mobile_number": "9566316840", "date_of_birth": "2003-06-12", "gender": "Male", "address": "Chennai Kodambakkam", "city": "Chennai", "state": "Tamilnadu", "pincode": "700012", "emergency_contact": "", "skills": ["Plumbing", "Network Support"], "experience": "2 years", "certifications": [], "profile_photo": ""}	null	\N	INFO
e55e2256-b93a-4bf5-b34b-42debe422ed7	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:13:10.618656+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
f17f5cfe-97af-4da1-8e9f-1ebb5312be07	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:14:24.639158+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
3f35da3d-2ca1-4964-a826-25e30aceab68	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:14:48.278276+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
2baedc5d-5af8-46e6-8b9b-8741118d648f	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:21:37.754723+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
a4b305d1-dbcf-47fa-8f89-e5888eed525f	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:21:56.74095+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
864c0a3d-2153-4740-acec-c83b8272b6b0	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:23:14.432076+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
0fd7a541-1637-4532-accb-27b7c5ab6e9d	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:23:45.554742+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
de7580ae-be25-4dee-b2c8-59b213e7338a	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 12:23:59.048577+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	2	null	{"status": "EN_ROUTE"}	null	\N	INFO
8970229d-bba1-46e3-89de-24f0f8e4fddf	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:29:17.627769+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
be8ef1bb-6962-4378-8606-539595f3cf7f	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 12:24:12.554111+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	2	{"status": "EN_ROUTE"}	{"status": "IN_PROGRESS"}	null	\N	INFO
c31a8d97-7e0b-4c8c-9e84-b6afd8dd4aaa	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:28:12.771729+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
018880f8-512d-4170-8cc7-d63cfe9fd544	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:28:35.601882+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
0b4f5982-1ff0-4dcc-83d4-0e371a775243	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:29:36.664986+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
ffee63da-2a10-4eb7-a25c-fb0455a2a3ab	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 12:31:09.650757+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_COMPLETED	job	2	{"status": "COMPLETED"}	{"status": "COMPLETED", "completion_notes": "i completed the job ac is repair"}	null	\N	INFO
483b1fb0-4b21-494a-ad9c-6aed17d1c89e	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:31:21.063494+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
b413deb3-4e0a-4ba4-9f52-5a81f5921f2d	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:31:37.597172+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
64105188-cd43-4606-913b-37f937add4ed	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:32:33.984507+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
5242ef81-d91c-4725-9403-d7e206cc2eb5	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:33:09.750839+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
a0892929-0d36-407d-8b06-3273822b34a6	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:34:52.7659+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
8e25cba0-c34f-4375-ac7a-45f9c755557c	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-08 12:35:25.683182+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 1}	\N	WARNING
854aac5e-5e68-4e0e-95d0-3a78e4158dc4	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-08 12:35:49.315418+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
7b373549-6796-4835-a701-42ce3fad54de	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-08 12:37:42.631256+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	SERVICE_REQUEST_CREATED	service_request	SR-20260808070742-95F230	null	{"title": "Networking problem", "priority": "MEDIUM"}	null	\N	INFO
b45cabd3-7f5d-4b91-910d-cd07dec9d0a6	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-08 12:37:48.926625+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
bf3491cc-cb82-4488-855b-f6d8959a78b0	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-08 12:38:18.392673+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
d92efd37-4d2c-46db-83f9-26ee832fa323	3147275b-8e7d-49ab-8e8e-59a206437aa3	\N	\N	tenant-1	2026-08-08 12:39:09.212997+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
a00a9ffe-eaab-4ab3-b5db-b8a537f0c2e5	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:39:38.112062+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5ed30ec4-bf1b-4f23-b8da-65316b01e7ca	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:45:34.331031+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
0401c545-3f97-40ae-8a8a-f995fff9c30a	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:47:56.269195+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
76330511-436e-4f6e-9ca2-dd83280a2521	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:52:36.899817+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
d9793c24-e7f4-4552-9cfc-69345bdb7f38	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:53:19.146152+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
80f3e7dd-48b6-4c53-af08-8eabb8bd065c	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:55:16.097609+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
a640e12e-8505-4034-a701-d06730e770ae	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:55:49.48955+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
1fa54777-4a03-4be0-87b5-5fc0eea92469	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:56:02.237559+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
f5b69052-dd67-489e-b9f5-38cade9796ae	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:57:28.445928+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
2a0b384c-365f-48a3-b674-2dedda01e92f	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 12:58:42.658048+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
c2c0be5f-1147-4f1d-b54d-6ee408d048c6	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 12:59:07.402659+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5027f711-5337-4649-a0bb-5b916359f815	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 12:59:14.198035+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	3	null	{"status": "EN_ROUTE"}	null	\N	INFO
de244085-c636-49bc-bbd1-edce925e74ca	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 12:59:41.866348+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	3	{"status": "EN_ROUTE"}	{"status": "IN_PROGRESS"}	null	\N	INFO
0f4cb80f-0a47-4fc5-8961-d2eebb7ff725	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 13:22:00.962144+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
6287415d-533a-416c-9cf6-ba8dab3679e8	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 13:23:14.148431+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
b3ed8970-af42-4e57-8d78-63404797e4ad	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 13:23:35.590824+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5a38aae9-4d82-4027-b7d7-8b0d915b9ca3	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:46:42.749532+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
99b7dfb7-22b0-4f32-a197-e595c1423996	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:46:57.929142+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5cd0e57b-6354-4546-9989-7224ec2c30dd	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:47:41.429289+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
3934672d-5818-4573-975f-9476579d937e	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-08 14:48:26.585579+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
d5777499-fae7-45ba-9c92-4987261d3dcb	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-08 14:50:09.477239+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	SERVICE_REQUEST_CREATED	service_request	SR-20260808092009-2F8DF7	null	{"title": "Water Leak in Weashing Mechine", "priority": "MEDIUM"}	null	\N	INFO
d7ef09c7-f7b9-42e2-9ed6-00b823a6f978	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-08 14:50:15.321763+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
a7de9c30-84d4-49af-bb8a-93d9888fbfea	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:50:32.967239+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
d768dcbd-f7f6-4b3b-801f-8769bac2993e	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:51:37.672531+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
82fac41e-a567-4f4b-9ff7-e0c4d85e0322	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:52:43.940517+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
3cee6ae4-6f5a-4cd4-805e-d49611ca31d9	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 14:53:44.829646+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_COMPLETED	job	3	{"status": "COMPLETED"}	{"status": "COMPLETED", "completion_notes": "washing mechine issue"}	null	\N	INFO
db5249e5-3768-4490-81d2-7c5106746814	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:54:07.583104+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
e06ccc30-5a7c-4c89-b7ae-92f0a911bbb2	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:54:30.458678+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5c3cf367-67f2-4059-bc65-7e7ddc416c51	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:55:53.924614+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
b24feac0-9025-4e2e-be33-620d222a8420	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:56:14.335464+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
b5499e92-d174-464e-82da-0111a128292c	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:57:45.455771+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
7b8509b9-c264-4890-8f88-019772b89ca8	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:57:59.950637+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 1}	\N	WARNING
ccbf4738-36f6-4032-9e9f-f4809f8c97de	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:58:06.865656+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
dc754c1d-8baa-4864-8840-f5c8251e06b1	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:58:11.063946+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
7f149c11-4ebd-4691-babc-3ec863c53ba2	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:58:32.171048+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
d5295f9f-bf7a-4a38-8c54-1a90f9567a13	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 14:59:21.498875+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
1c333fb6-0fcc-4f88-9da6-2e98e3bcc0bb	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 14:59:35.717586+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
cd9f44b2-9939-4c87-8aeb-c714b0780370	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 15:01:43.618874+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
decfa51b-a7c8-45d9-9130-3a1c016d4ff3	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-08 15:04:53.851849+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	SERVICE_REQUEST_CREATED	service_request	SR-20260808093453-C08E69	null	{"title": "My fan is not working", "priority": "MEDIUM"}	null	\N	INFO
7bc03a13-cb1a-413e-9a0e-88c1e5627754	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 14:59:52.50166+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	4	null	{"status": "EN_ROUTE"}	null	\N	INFO
5fd1d61c-9cdc-4851-8c0a-0c4e4d52397f	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-08 15:02:18.693904+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
3a79b205-8d90-4f1f-a972-4de330b9015b	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-08 15:04:58.422504+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
62127964-fc79-49ad-b867-724a97947f1a	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-08 15:02:32.109157+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	SERVICE_REQUEST_CANCELLED	service_request	4	null	null	null	\N	INFO
be1c5dc8-a297-413a-badc-64e847537ede	176973fb-629e-49f7-89f9-01807a93d3cf	\N	customer	tenant-1	2026-08-08 15:02:35.320673+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	SERVICE_REQUEST_CANCELLED	service_request	3	null	null	null	\N	INFO
67152e7c-b670-4e1a-86f5-130bfba63a84	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 15:05:15.244979+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
bf73ad25-bc05-4626-8810-1be264a400e6	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 15:08:37.341439+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
68d17276-9269-471f-9c08-a7248c720a32	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 15:08:49.942746+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
d3b44d89-034a-4c2d-b89d-ffd3dd47d78e	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:09:32.303171+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	4	{"status": "EN_ROUTE"}	{"status": "IN_PROGRESS"}	null	\N	INFO
1792d5ed-5013-46f5-9dfa-4f9933f221af	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:10:05.141031+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_COMPLETED	job	4	{"status": "COMPLETED"}	{"status": "COMPLETED", "completion_notes": "washing machine is not showing"}	null	\N	INFO
b9c2b7a3-5d5a-4dca-b4a5-1a16b898b916	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 15:10:23.491729+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
56fb4eb8-f217-4c9d-affe-d788bae4dbb8	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 15:10:40.372134+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
f33b7053-7a0f-4eb8-a107-c3600a8f44ff	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 15:11:17.277987+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
8cac69e5-8f55-443e-af16-b68afcc61304	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 15:11:33.89819+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
b20d872a-b3ed-4d8c-8365-7d17a459d98d	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 15:11:54.000191+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
7b985ea0-5f3c-4ee6-be50-8e8e1c8a4fde	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 15:12:12.844087+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
48f5ddf6-a67c-4cfa-b7ec-41339c126e4d	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 15:13:02.764314+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
c6bdfca6-5123-4632-a925-c74b26debc82	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 15:13:15.982652+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
ba7dd8b6-892e-4bbb-a8d5-0a38467a8feb	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:13:35.7413+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	5	null	{"status": "EN_ROUTE"}	null	\N	INFO
07d70c30-95e8-4655-84b9-9175d041180e	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:41:02.413421+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	5	null	{"status": "EN_ROUTE"}	null	\N	INFO
15a95455-dd2a-4caf-b1a7-986ee4f164c3	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:48:34.242117+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_REJECTED_BY_TECHNICIAN	job	5	{"status": "EN_ROUTE", "assigned_technician_id": 2}	{"status": "REJECTED_BY_TECHNICIAN", "rejection_reason": "i have another job"}	null	\N	INFO
de6bd9be-1e1f-48be-801b-70b9fcd44cdf	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:49:38.354144+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	2	null	{"status": "EN_ROUTE"}	null	\N	INFO
840da299-6c83-4fc7-ae6d-09d0890d471d	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:49:51.497379+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	2	null	{"status": "EN_ROUTE"}	null	\N	INFO
c1914f9e-29a2-4056-9809-8ba4b354f7e5	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 15:55:42.886029+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	4	null	{"status": "EN_ROUTE"}	null	\N	INFO
128f139a-c2b5-4c0b-9731-115e9732c5b7	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 15:56:01.046867+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
6b03c189-2aec-4347-8129-79c6e55d00c9	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 15:56:18.071603+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
0c05fc54-c23d-4606-963e-a2bbcb23a6fe	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 16:01:27.816516+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
f43d0392-b171-4899-8372-3b66096890fa	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 16:01:38.912255+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
6c58d189-b397-41d6-975f-09bcab37d08e	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:01:44.828217+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	5	null	{"status": "EN_ROUTE"}	null	\N	INFO
1c38f35b-2890-4e63-8127-14d0680064ae	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 16:37:02.693581+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
d3502b52-5a32-4845-ad4e-db9d6b4bb650	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 16:37:16.614728+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
4fd0793f-556d-45ef-a4c9-9b971d50e0e4	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 16:37:42.702235+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
366b414b-28af-4ae0-bcf3-33a189aa07a5	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 16:38:03.170605+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
36c50606-8288-4bde-af6f-05ea6f95ddb0	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:38:05.933448+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	5	{"status": "EN_ROUTE"}	{"status": "IN_PROGRESS"}	null	\N	INFO
7f730602-0265-4ab0-a0cd-0b4f0bcf90dd	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:38:12.342519+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	5	{"status": "IN_PROGRESS"}	{"status": "IN_PROGRESS"}	null	\N	INFO
91ff0a60-6ad0-461b-9e3e-a4511732ac3b	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:38:12.349087+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	5	{"status": "IN_PROGRESS"}	{"status": "IN_PROGRESS"}	null	\N	INFO
9955ec34-70d1-4847-ac9a-72e966d3a96b	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:38:12.354236+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	5	{"status": "IN_PROGRESS"}	{"status": "IN_PROGRESS"}	null	\N	INFO
f0a27db3-c0d0-444f-9e0f-f9add55914e0	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:38:12.363236+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	5	{"status": "IN_PROGRESS"}	{"status": "IN_PROGRESS"}	null	\N	INFO
a66326d2-6187-4b34-a2ef-2066a4abdaf4	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:40:20.636469+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_COMPLETED	job	5	{"status": "COMPLETED"}	{"status": "COMPLETED", "completion_notes": "job is to fan cail is not working"}	null	\N	INFO
87108017-dbca-419a-b939-ac168cf704ff	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 16:40:29.113593+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
c901c118-a78b-46a5-8eab-04a21f44e274	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 16:40:42.777935+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
8795d576-aa8b-495e-940a-b6bc6a084ad4	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 16:41:14.140224+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
02cae3a0-737c-4def-acd8-a19d981feb69	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	tenant-1	2026-08-08 16:41:29.670055+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
a7d88788-55f5-4c4a-b5da-8286a489ffd9	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	technician	tenant-1	2026-08-08 16:41:35.675675+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	1	null	{"status": "EN_ROUTE"}	null	\N	INFO
f6916fc3-110b-4354-bc8e-80229d9537b8	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-08 17:58:58.936946+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
063617a6-994a-46a2-9246-a428e6193a34	87306d32-abbb-4add-94b2-675471fedcf8	\N	super_admin	__platform__	2026-08-08 18:00:24.631804+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	USER_CREATED	user	61fb8daa-dd90-4a62-ba3a-f99eedf7be9f	null	{"email": "bala@gmail.com", "role": "admin"}	null	\N	INFO
2e45f9cb-4b2d-40e0-8a14-1d1c19ff24d7	87306d32-abbb-4add-94b2-675471fedcf8	\N	super_admin	__platform__	2026-08-08 18:01:58.25672+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	USER_CREATED	user	d5195840-ec9a-4f73-b8ac-c73573100aab	null	{"email": "kevin@gmail.com", "role": "admin"}	null	\N	INFO
1822655e-34ad-4088-ba83-e01eabc219e8	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 09:57:56.545038+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.132.0 Chrome/148.0.7778.280 Electron/42.7.1 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
c72ba48b-ac08-479b-ab6c-ee655c233d8d	87306d32-abbb-4add-94b2-675471fedcf8	\N	super_admin	__platform__	2026-08-10 10:00:13.652962+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	USER_CREATED	user	c4d825cd-9dbc-4625-82ed-40724bff7c6d	null	{"email": "prabhu@gmail.com", "role": "admin"}	null	\N	INFO
ec396c92-384e-40d6-b4f9-08c8a54269ee	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:01:10.871613+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
7b91a0d1-3894-4d5a-ac4f-a4f3ea7cf95d	c4d825cd-9dbc-4625-82ed-40724bff7c6d	\N	\N	__platform__	2026-08-10 10:02:04.383835+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 1}	\N	WARNING
7c8adf7a-03ea-4763-bf08-ce8cdec84310	c4d825cd-9dbc-4625-82ed-40724bff7c6d	\N	\N	__platform__	2026-08-10 10:02:05.84839+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 2}	\N	WARNING
429327cd-3999-450d-8484-431a61dc04ac	c4d825cd-9dbc-4625-82ed-40724bff7c6d	\N	\N	__platform__	2026-08-10 10:02:11.577588+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 3}	\N	WARNING
94c1d7ba-2799-472d-bb24-508a17b02a9e	c4d825cd-9dbc-4625-82ed-40724bff7c6d	\N	\N	__platform__	2026-08-10 10:02:20.982815+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 4}	\N	WARNING
bd7e6c0a-82f8-4c41-841b-d8937c14c139	d5195840-ec9a-4f73-b8ac-c73573100aab	\N	\N	__platform__	2026-08-10 10:02:33.188655+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
dc70ca22-68d5-4009-be0c-11e897ef47a2	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-10 10:11:00.095705+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
be60084b-d53c-4b34-901f-b426c3fc76b6	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:12:22.679089+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
a38003c3-ebf9-41e6-893a-f2d0698ea0ae	87306d32-abbb-4add-94b2-675471fedcf8	\N	super_admin	__platform__	2026-08-10 10:16:44.982561+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	USER_CREATED	user	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	null	{"email": "john@gmail.com", "role": "admin"}	null	\N	INFO
c42eff05-d725-461f-9627-89085359c1ed	d5195840-ec9a-4f73-b8ac-c73573100aab	\N	\N	__platform__	2026-08-10 10:02:50.545935+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
d2c68195-f810-4dcc-b1cc-bb4def191468	87306d32-abbb-4add-94b2-675471fedcf8	\N	super_admin	__platform__	2026-08-10 10:12:14.027499+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	USER_CREATED	user	e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	null	{"email": "yaswanth@gmail.com", "role": "admin"}	null	\N	INFO
4c57ebd7-9dca-4b57-a294-5d5157f27535	e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	\N	\N	__platform__	2026-08-10 10:12:28.006341+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
00bfd950-1001-4405-8c02-32aa858367e7	176973fb-629e-49f7-89f9-01807a93d3cf	\N	\N	tenant-1	2026-08-10 10:03:18.778906+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
3e67943a-102a-4d15-9258-a30c1487eac8	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:11:22.595747+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
0ab0aa82-033e-4343-9489-6b2d4cb98db8	e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	\N	customer	__platform__	2026-08-10 10:14:15.534919+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	SERVICE_REQUEST_CREATED	service_request	SR-20260810044415-8E829C	null	{"title": "Warter Leak", "priority": "MEDIUM"}	null	\N	INFO
c57c2a4d-88b7-4727-82cd-14f27dae69fd	e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	\N	\N	__platform__	2026-08-10 10:14:20.951311+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
36cd97c7-bf3e-488b-82e6-97a1e18d6ebc	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:14:26.457551+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
3ec14f2e-d606-44f6-b497-ae42f19aba31	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:17:33.242916+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
955f5d75-eeae-498e-a7d7-a61936c9fd5b	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 10:17:35.396842+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
0370a110-d859-4286-aca9-5098f9935669	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	technician	__platform__	2026-08-10 10:19:16.346603+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	PROFILE_CREATED	technician_profile	850bf082-87dd-497c-92f5-fcbe220b78f8	null	{"full_name": "John Doe"}	null	\N	INFO
249645c4-a5ff-4de6-8420-019337510af2	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 10:19:26.611679+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
29f4c906-7bb6-4111-959f-ac8756363d28	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:19:32.276318+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
013d2e37-32bf-4c80-b3d8-1163dd6b5434	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:19:58.320787+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
b6c054be-ea18-4ab5-800e-e127debf883b	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 10:20:02.401715+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
9f24f0d7-3b23-49b3-8523-00235a0176f8	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 10:20:25.839135+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
88433645-a13b-4cd5-9cd8-7d3b4545fc86	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:20:30.077321+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
05ead5cb-751f-4657-9f4a-b9db90054f50	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:21:11.925646+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
fa5ea792-f727-4f8b-a627-01cb483a440e	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 10:21:15.498402+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
5fe19d66-c46c-4dd1-8305-75cee0203569	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 10:21:39.044906+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
d3012e6e-6a24-4199-a16a-68763625dc74	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:21:49.670338+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
459ef333-77e7-4dd2-9a91-96a7d258cb3a	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 10:22:41.75496+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
4b0f7490-1325-4cca-b07b-cfc9aab01fb7	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 10:22:47.310592+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
0eb0fc9b-6d2f-4de5-9049-04d7da56b13e	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	technician	__platform__	2026-08-10 10:22:53.779177+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_ACCEPTED	job	6	null	{"status": "EN_ROUTE"}	null	\N	INFO
19303068-2222-479e-848e-853c4d509f88	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	technician	__platform__	2026-08-10 15:14:24.380515+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	PASSWORD_CHANGED	user	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	null	null	null	\N	INFO
f540e848-8879-446e-8c52-fb44763322cb	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:14:33.439542+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
06979314-1f8f-47a1-a410-8294385dc3d9	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:14:37.855805+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
e6d95c3e-6190-4796-9d13-218fc388724f	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:14:42.170307+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
5b0d8d70-8154-42d9-b4ca-6c3b21fdb0d6	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:14:50.445917+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 1}	\N	WARNING
a8c84b15-10af-4e1f-9307-62428daeda5d	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:14:53.952541+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 2}	\N	WARNING
deeae033-f4a0-4a74-9a32-eceeb25cd326	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:14:59.36035+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 3}	\N	WARNING
f999a815-e01d-45c5-879b-411c2921e1c4	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:15:08.68996+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	FAILED_LOGIN	\N	\N	\N	\N	{"reason": "wrong_password", "attempts": 4}	\N	WARNING
3be8f73b-c941-42ae-ba27-afc333f9d6bd	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:16:09.236622+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGOUT	\N	\N	\N	\N	null	\N	INFO
4d7e8c06-841f-40c9-a47c-28dcfb080adf	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:16:18.214484+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
320fbd4a-e867-4497-8602-5131f05496c1	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	technician	__platform__	2026-08-10 15:16:46.615275+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	6	{"status": "IN_PROGRESS"}	{"status": "IN_PROGRESS"}	null	\N	INFO
d56a949d-ca7c-462c-8208-1d9d89663979	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	__platform__	2026-08-10 15:15:38.620427+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
6870b261-fc45-4e88-a6ec-b14a583ff032	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	technician	__platform__	2026-08-10 15:16:03.383642+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	PASSWORD_CHANGED	user	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	null	null	null	\N	INFO
3c742e42-b90d-4303-8ca4-58731cea7d25	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	technician	__platform__	2026-08-10 15:16:40.242173+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	6	{"status": "EN_ROUTE"}	{"status": "IN_PROGRESS"}	null	\N	INFO
97045a66-50be-40a2-b99b-2ddd552aceff	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	technician	__platform__	2026-08-10 15:16:46.624115+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	JOB_STARTED	job	6	{"status": "IN_PROGRESS"}	{"status": "IN_PROGRESS"}	null	\N	INFO
41ddff3b-212b-47a2-8278-34abf29c3efc	87306d32-abbb-4add-94b2-675471fedcf8	\N	\N	__platform__	2026-08-10 17:07:00.428219+05:30	127.0.0.1	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	LOGIN	\N	\N	\N	\N	null	\N	INFO
\.


--
-- Data for Name: eta_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.eta_history (id, job_id, eta, duration_minutes, distance_km, traffic_delay_minutes, source_ping_id, calculated_at, tenant_id) FROM stdin;
\.


--
-- Data for Name: gps_pings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.gps_pings (id, tenant_id, technician_id, job_id, latitude, longitude, "timestamp", accuracy, altitude, ip_address, user_agent, correlation_id, created_at) FROM stdin;
\.


--
-- Data for Name: gps_purge_audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.gps_purge_audit_logs (id, tenant_id, job_id, purge_type, deleted_count, correlation_id, created_at) FROM stdin;
\.


--
-- Data for Name: gps_rejected_ping_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.gps_rejected_ping_logs (id, technician_id, job_id, reason, "timestamp", tenant_id) FROM stdin;
\.


--
-- Data for Name: job_assignments; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_assignments (id, job_id, tenant_id, technician_id, rank, status, assigned_at, responded_at, is_current, created_at) FROM stdin;
\.


--
-- Data for Name: job_closures; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.job_closures (id, job_id, tenant_id, work_summary, before_images, after_images, labour_cost, material_cost, subtotal, completed_at, created_at, updated_at) FROM stdin;
1	2	tenant-1	i completed the job ac is repair	[]	["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/2wBDAQoLCw4NDhwQEBw7KCIoOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozv/wAARCAEoAyADASIAAhEBAxEB/8QAHAABAAEFAQEAAAAAAAAAAAAAAAUCAwQGBwEI/8QAUxAAAQMDAgIFBwUMBggGAwEAAQACAwQFERIhBjEHE0FRcRQiMmGBkbEVcqHB0RYjM0JSU1RzdJKTsiQ1NjdVYhclNENj0uHwCHWCorPCOIPxRf/EABkBAQEBAQEBAAAAAAAAAAAAAAABAgMEBf/EACMRAQEAAgICAgMBAQEAAAAAAAABAhESIQMxMkEEE1EiBeH/2gAMAwEAAhEDEQA/ANlREXreUREQEREBT/C3p1Pg361AKf4W9Op8G/Ws5/FrD5NiREXmegREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERBz5ERet5RERAREQFP8LenU+DfrUAp/hb06nwb9azn8WsPk2JEReZ6BERAREQEREBEUJXcRNp53QwRCQtOC4nbKslvpLZPabRa191E/wCjx+8p91E/6PH7ytcMmeeLZUWtfdRP+jx+8p91E/6PH7ynDI54tlRa191E/wCjx+8p91E/6PH7ynDI54tlRa191E/6PH7yn3UT/o8fvKcMjni2VFrX3UT/AKPH7yn3UT/o8fvKcMjni2VFrX3UT/o8fvKfdRP+jx+8pwyOeLZUWtfdRP8Ao8fvKuQ8TkyATwAMPMtO4Thkc8WwoqWPbIxr2HLXDIKqWGxERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBERAREQEREBEVmaojgj6yZ4Yz4oLyKO+WqL8t/7pXvyzRflv/dU2JBFH/LNF+W/3Lw3qiH47/wB1XYkUUab7Qj8d/wC6qTf7eOcj/wB0oJRFF/dBbvzr/wB0r35et55SvPsU3BJoos36gH48n7pXh4ht4/3kn7pTlF1UqiiPujtv5yT90p90lt/OSfulTlP6aqXRRH3R2385J+6V6OIrcTgPlP8A6SnLH+mqlkUR90dt/OSfulefdLbPzkn7pTlP6aqYRQ33TWz85L+6UHE9rzvLKPWWFXlDVTKKxT1UVTCJ4JWyxO/GHYr6qCIiAiIgIiICIiDnyIi9byiIiAiIgKf4W9Op8G/WoBT/AAt6dT4N+tZz+LWHybEiIvM9AiIgIiICIiAuf1BIfIe3JXQFz+oBLpAOZJXXxfbl5PpG8P1k1wslNVVBBlkDtRAxycR9S9juETKi4mapHV0haXAswIxpB59veouxy3e226moJbFMerJa6UVEWMFxOcas9qrqrNVVbb/FpEYrSzqHFww7DAOzluMLpu6c9dpCivdLXTCFjZonOZrZ1sZbrb3jKtx8RUMs7GASiOSTq2TmMiNzu4OXlPLca6Rsc1u8jiETmyOkc1ztRGPM0k7eOFBUthq2Q01vkt9S4wyt1zPq/vGlpzqDQ7OduWOabq6jYnXukbczbgJXzggODYyQ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"]	800	500	1300	2026-08-08 12:31:07.378253+05:30	2026-08-08 12:31:07.345878+05:30	2026-08-08 12:31:07.345878+05:30
2	3	tenant-1	washing mechine issue	[]	["data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAoHBwgHBgoICAgLCgoLDhgQDg0NDh0VFhEYIx8lJCIfIiEmKzcvJik0KSEiMEExNDk7Pj4+JS5ESUM8SDc9Pjv/2wBDAQoLCw4NDhwQEBw7KCIoOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozv/wAARCAJUAyADASIAAhEBAxEB/8QAGwABAQADAQEBAAAAAAAAAAAAAAYEBQcDAQL/xABTEAABBAIBAgQEAgQICQgIBwAAAQIDBAURBhIhBxMxQRQiUWFxgRUyQpEWIzM2UqGz0SQ3cnR1sbLB4RdXgoOU0vDxCCVVVmKSlaU1Q2NzdoST/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AOzAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAASmRm8Q4L881Crx+1QY9VigWSZliRn06l+RHL9fQCrBO8X5dFyCSzQtVVx2Xou6bVCR6Ocz005qp+s3undPr903v5poq8L5p5GRRRtVz3vcjWtRPVVVfRAP2CMs+JuKlyLcbx+rZ5BbTayspN+WNqa7q52kX19tp9VQsk7pvWgPoAAAGr5Fx+nybEvxt587InKjkdBKrHNcnov0X8FRU+wG0Ma7kaeO8j4yzHB8TM2CHrXXXI79VqfddKTHh7kcg6vk8Dl7DrF7CWlgWWRVWSWJ3zRvdv12m9L9EQy/EHFz5Th1xKUbnXqvTaqrH2e2SNepFavqjtbRNd++vcClBrsBlYc5gaWTgkbIyzC1/U306tfMn2VF2mvsbEAAAAAAAAAAAABOcjrcmitMyuBvslZXZ/GYqWNOmyiKqrp/q12uye29AUYNbgM7T5HhoMpRV3lSou2vTTmOTs5q/dF7GyA1md5FjON0fi8lY8tqqjWRtTqkkVfZrU7qpkYvINyuMgvsgngZO3rbHOzpeie209t+v5kXxHF1eQ8qzvJMo1bN3HZaajTRzl6II4kREVqfVepVX7900X4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABrpc7Si5FBgXK/4yeu6w1Eb8vQ1UTuv19f3L9t7EAAAAAAAAAAfFXSKq+iAfQRj/Fzg0b3MdmlRzV0qfCTdl/+Q3+E5LheRxOkxGRhtozSvaxdObv021e6fmgG0AAGuzPIMRx6r8TlshBUZpVakjvmfr16W+rl+yIp5cezM+dovuyYuxQgc/8Awb4hU65o9Jp6tTu3a77L7aX3JPC4uje8XOTzZOsyxYrMrOpJOnWkbFZ8zmovZO6N7+vr9VL2xYgqV32LM0cEMabfJI5Gtan1VV7IB6g0/wDC7jP/ALxYr/tsf95tYpY54mSwyNkje1HNexdo5F9FRfdAP2AAAAAAAAAAAAAA/E0rIIXzSKqMjarnKiKq6RNr2TupEWfF/ifk9OMsz5O49yMhqQ15Gvlcq6REVzUT3/8AMC6J3N84w/HsnHQyPxUbnta5ZkruWJiKutq/0RPr9Da4i7YyOMht2sfNj5pEXqrTKiuZ3VO+vr6/mZUsUc8T4Zo2yRvarXsem0ci+qKi+qAfipbrX6zLNOxFZgk7slhej2u9uyp2U9iE8PK8NDP8uoVWJDVgyDfKhb2ZHtu10nt/wLsDykswQyxRSzxxyTKrYmOeiK9UTaoie/bv2P2j2q9WI5OpERVbvuiL/wCSkZ4gJ8BlOM8ik2tbG31js9u0ccrelZFX2Ruk/eLzo8P4o43JLJ/gudpOp9Sd2pKxUexVXfZHNVUTXugFqD8TTRV4XzTSMijYiue97kRrUT3VV9D9eoH0AAAAAAAAA03JuTUeLYz4u4rpJJF6K9eNNyTyezWoBoa/+O+1/oFv9shtuf132uA5uJioipTkf3+jU6l/qQ1vG4E41QyHIuWWK9O/lJ1klfLKn8WxE/i4t+6oiL2Q2+O5hxnOW0oUMvUtTyNXULXd3Iid+y+vYCT4/wCI3E8TgKNStWsora0azJTpq5rXqxNoqt7K76lziM5i89TS3ir0NuJUTaxvRVYqpvTk9Wr9l7nvSo08dWbVo1IKsDVVWxQRoxqb7r2TsQvKMXFxXlGEz+DVKUmTycNC9XjbqKw2RVVXK32cml7/AH/eHQgAAAAEZxj/ABn83/8A6H9ipZepyXA81gocy5badRv5O/buthjp4+orlZFCisY9yqvZF2iL9FTeu5ZYW/zXJZGO3dxuMx2Jeq7ryvkdcamtIqqnyd17/gBpODZzG8YTLcZzd+vjrFC9I+P4mdkbJIpF6mqza+mu+vbaH78N+ZYr+A1D9NckpJfVZfNS3dYkv8o7W0cu/TWvtos8hg8RlnMfksVSuujRUYtmuyRW79ddSLr0Ijg/G+Py3uS0bmGxtmapmJVjV9NjvLiejXMaiqnZE+bt7AdERUc1HNVFRe6KnufT4iIiIiJpE9j6AAAAAAAAAAAEN4bywY/G56m+ZkNWln7Veukj0RGsRWqjdr6+q+vcpK/J8Bbvx0KuZo2bUquRsME7ZHbRFVdo1V12RfU01rwu4jdyk+Rs458stiV00rVnf0Oe71Xp39V2bvG8bweGekmNxFKpIjOjzIYGterforkTa+ieqgT+HV2E8SsxjJV6K2YibfqIvZrpGp0yo32V3o5UTvpEVSzJLxCx8q4eLP0dJkMDJ8ZD9HsRP4xi/ZW7/cUeMyEOWxdXIVl3FZibKzv7Km9AZQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEVyCzPy7MS8Qx0qx0Ym/+uLbE7tRfSFi+nU73+ifuNjz3O2cBxeWenE19mxI2rErnK1GOf2Ry679jL4pxurxXAw4ysvW5vzzTKmlmkX1cv8AUn4IgHNPE2zZwXP8HkKDpEZjKLJZUa9VVYkm6XIvuqKi9/ts7BXsQ260VmvI2WGZiPje1do5qptFRfoqEFhK6cs5/wAiydyCJ1GnE/DthevWr9Lt7voiKi6/Mx+P5i/4c4tmF5Ji7X6OqvejMvBuaLpVyq3qanzNTvr7dvqB0kw8tWvW8bLBjsh+j7T0Ty7Pktl6O/8ARXsvbseWI5BiM9D5uKyNe41Go5yRSIrmIvp1N9W+i+qexsQIz+DHO/8AnF/+ywf3nxeI8vsosV7xCsvgX9ZKuOiryfbT0VVQr7FmCpXfYszRwQxp1PkkcjWtT6qq9kJaz4ncZYqRY+xYzFpybZVxsDppHInqvsnb17qB+sXwexRycFy1yvN5BsDutsE9n5HO1pN69U7+hWET/DLlV5erEcCuuj9UdfsMrOVPb5V9/sUuDmy8+NbLm6terbe5V8iCRXpG32RXe7k99dvoBsQAB8VNppSA5Zj6fEM9iOW4+nFUrRSOr5JtZiMdKyTTWfL6Lpyb+vodAInxc/mJJ/nUH9ogFsAAIbM8T5S/mdnM8fzNLHxXYIoZpJYVkljRq9+lqorV/NU9fb1Pet4X8edM25mmz5vIdXU6zdmcu/t0IvT0/ZUUsj56AaH+AnEv/dvG/wDZm/3Gn8JUd/BGZ0bpHUHX5/0er3Kv+DoqI3W+6JtHdl+5+srl5uY5B3HeO2+mnErVyeTgk7NZ6+VG5PV6+6+iJ9+xV4zG1MPjYMdRhSGtXZ0RsTvpP94GUAAAAAAAAAAOW3YOQZ/knLLWLvysyeHSKvjImq1GNR2nv7L26ndOtr9fw1svDfxGXk6SYrMoytmYF15fSrPORETa6X0ci72hs83xTJNy7s5xXIx46/Nr4qGdqugt6T5epE9F9tp30pMVeBZXkvKcjl+RYtmFfJXYkM9O0jnpYb2SVitXaJpPRde3qvdA6oYUeSjX4hbMb6bIJvKR9lWsbL2Repq77ou/6lJOPj3iHAxIo+aVZGN7NdLj2q5U+6/U2Vbic2TxD6fM7EGdf8R5sapD5TY06URERGr+P7wN9BkaNmZYK9yvLKjetWRytc5G71vSL6bPzlLq43E27zYXzrXhfIkTE256om9J+Jh4TiuC446V2IxsVR0yIkjmbVXInom1VTbgcl4Ry2THYD4Ojg8nleRX55LNrqhWGN0jl7uc9ezWonSnZNb+my0wMHMrGS+Pz12nUrNarExtWJHtd27PWVfmRd+yduxTADWckwsXIuPXcRM98bLUfT1M1tFRUVPX7ohzHkDfEGzxOnHd45BWfg+i0t34tj3SuiTsrWMXabTe09/t6HYT4qbTSgc+4/weryOpWz/KctJyOWyyOaFF3FBF2RdIxqoi9972iIvuh0FrUa1GtRERE0iJ7ER4cyrjrOd4o/aJiLqurMX9mvL87ET6+67+5cAAAAAAAAADRcg4Vx7lM8M+ax/xUkLVZG7zpGaRV3r5XJs3oAk6XhfwqhP50GAhc/Wv46SSVP3PcqfmUNbFY6lL5tTH1a8iprriha1dfTaIZYAEJemby3xGx1Kskk2O4/I+e6rk1H8R0/xSNX9pzVVV+3cuzV8e47juMY1cfjI3MidK6VyvXbnOcvqq+/bSfgiAbQAAAAAAAAi8R1UfFzkFad2lyVKvbrtReytYnlu39F6v6i0NHe46tzmOMz/xKMShBLEsPTvr600i73213A3gAAAAAAAAAAAAAAAPioippU2inOcdnsT4e8kzuFytpKeNe5l6htFciNf2exrWoq9n+iInptTo5gX8Ji8paq2r9CCzNTf1wPkYirGv1T+pfxRF9gMbAcrwXKIpZMLkGWkhXUidLmOb/wBFyIuvvrRuDnyxQ3/GmF+IhZCuLqO/SszH9PndbdRsVE/WVF0vf/ch0EAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADAzeGqZ/EWMbdZ1RTMVEdrux3s5v0VF7opHfoHxLTH/opORYr4bp8lLnlyfE+X6dXprr19/X333OgADV8e4/R4ziIsbQYqRs+Z73Lt0r1/Wc5fqptAAJfL+H2Eyc6W6qTYi6iqvxWOd5L3Kuv1tJp3dEXub/H1H0cdBUktTWnwxoxZ51RXya93KnqpkgCObwKTJXks8rzk+eZE/qgquhSCBnft1Maunr91/MqqtGpRa5tSrDXRy7ckUaM3+Oj3AAAAAAAI/wAUaNzIcInio1JrczZ4X+VCxXPVEeirpE7qWAAiF8QMra1BjeB8gfaf+olyFK0X36pF2je319V7e5Qcem5BPTkdyKnTrWEf/FtqSK9FbpPXfvvZtwAMTKY+LLYyxj55Jo47DFY50MiseifZU9DLAGBhsLjsBjo8fi6rK1dn7LU7uXSJ1Kvuq6TupngAAai9yzjuMkliu53HwSw/ykT7LOtv26d73+RoV8X+DIqp+mXdvpVl/wC6BagwMPm8Zn6XxmKuR24EcrFfGvo5ERdL9F0qfvM8AAAAAAAAAafPciiwNnFQy13y/pO62o1WuRPLVyLpy/XuiG4InxT3VwOPzKJ/+FZOvYc/16G9XSq69+7k7AWwBrstn8Rgo0kyuSrU0ciqxJpEa5+vXpT1X1T0A2IJfA89xnKMu6nhILVutHH1zXfL6Io3ezfm0qqvf0T6ffVQBO8jz9vC5zj9dscfwWSturWJnovyuVv8W1Pu5d/uNf4lZ7J4PE0f0bbbQ+LuMhmvviSRtZi+rlRUVP3n78T6l21w5zsdVnsXK1qGeFK7FdKxzXp8zdd0VE33QplZXyuOa21UR8FmNFfXsxIvZU30uavv9UUDi/CE+F8bZIoc0/NRvrKx19ZOr4hUiY5e6KqKiOTWtrrSfQ7iQfKMS3D8j4dexOMiiqV7760sNWJGdKTJrq01NdKacq/8S8AAAAAAAAAAAAaHkfIpcFkMJD8O19fJXUqyyucqeWrmr0on3Vf9Sm+I3xWgkfwG5art/wAKoyRWYJEXTonNenztX2VGq794FkDn9bn3I81dvJx3ikd+nUnWHz33mxK5dIu+lyduylJx3I8ivrP+ncDFikZryui22bzPXf6vprt+8DeAAAAAAAAAAAAAAAAAAAAAAAAAAATHKuUuoyR4LCOis8gu7ZXg6kVIE1tZJP6KIndEX11233Kc18GCxlbNWszFTjS/ba1s06ptyo1ERETfomkT09dJv0AxuM8ch47SlZ8RJbt2pVntWpf15pF1tfsnbsnsbkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB5VrVe5Ck1WeOeJVVEfG9HNVUXS90+6aP3JIyKN0kj2sYxFc5zl0jUT1VVOceFfJcBjuA0q17OY6rO2SZXRTW2Mcm5HKm0Vd+gHSQa+hn8LlZnQ47L0bsrW9TmV7LJHIn101V7GRf+N+An/RvkfGdC+R8R1eX1+3V099fgBkGmv8w43jGvW5naESsYr1Z8Q1XqifRqLtfReyJtTRpwfKZza8v5DPdhd+tj6W69f66XXzPRF1revRDeY7h/GsU6N9HBUIZYlVWSpA1ZGr/lqnV/WBo3eLHF36WkuQyEfvJWoyK1q/RepE7m+49n28hqS2o8bfpRMk6WLch8tZU0i9TU3vXf1NsiInoiJ+AA+g1tbkOGu5STF1cnVnuxNV0kEUqOczS6XevRUX1T1Q2QAxshkKuKx89+9MkNauxXySKir0tT7J3X8jJPnr6gRCcg5Tytevi1evQxMjuhmTuNVZHp7vjiX29k6vUx8jZ5ZwmSllMtyZubxstuOtaiXHxwLCx668xFZtVVF1299l/6ehEeLKuk4xSoxRq+e/lK9eFEVE+dXK5N7/ydfmBcAAD8TStggkmejlbG1XKjGq5yoib7IndV+yHKstf5dLxJOR5XO2cbWvSIxuHq042yMa53Sxvnr8zdppVXW036ex1giuaL8XzThuInRH07FqexJGv7T4Y0dHv7Irl7ei+4G0x3BOL46KJIsHTfJH382eJJJFd7qrnbVVKBGo1qNRERETSIh9AENnqq8HyruV4yD/1ZIiMy1OJNdtojZmN9Opvv9U/eW0MsdiFk0T0fHI1HMcno5FTaKYWdxbM3gb2LeqNS3A+JHKm0aqp2XX2XS/karw+yjspwyisqdNmo1alhi62ySP5VRdfZEX8wKUAAAAAAAAn+exRzcCzjZGNe1KMrkRyb7o1VRfyVEX8igPC9DVnoWIbzY3VXxubM2T9VWa77+2gIHA8s5lDxrGzScHnuVmU4nOtMycb5JmdCfOkeupXKnfp9dro22FzPF+c3XpPiWtyuO2j62Rqok8Cb+6L2/Be2++tn4f4m8FxlOKKDLQrFG1I4oa0LndKInZERE7JpNHhw2nmcnyrJcuyuPXGR267K9SrJ/K9CLvqensvZO33+21Db5fn3FcG9YbmYr+c16x+RBuWRHJ+yrWbVq+3fR7cUz1vkVGzesYyWhCll7KqTIqOliRE09UX02u+329zYwYnG1rk12vj6sNqf+Vnjha18n+U5E2v5mWAAAAAAAAAAAAAAAAANfnqD8rx7I46JWJJbqywsV/6qOc1URV/NTYADnWP4VyDidajd43NXfaWsyPI4+eRyQTyI1EWRq+zu35/v3seM8/fnOU28DkMY7FWa8DXthmftznoupERdaVEVU0qeqbX8LQgvEHw0XmeRr5CvfjpzxwLA9ZIlf1N6upuu6aVFV37wL0Ezw/BcjwUckGZ5EmXg6USFHwqj2Kn1eqqqpr67/vpgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANNzCKSfhmbiiar3vx87WtT3VY1Ivwq4vx/J+H9G3fwlC1Ye+VHSzV2PcupHIm1VPoWXJ+TYbjdJn6Yl7WuqOKBrFe+Zdd0RqevqifTun1Oa+HWCynLOFVsfZylaHj8Nh6TVazXefMvX1qyR37Kd0/V9lA3nFMfRveJ+TyWEoVaWLxMHwSOrw9DbMrl29U0iIvSqKi/8AR+p0kxMZjKWGx8OPx1dletCmmRsTsn1X7qq91X3MsAT/ACGTlyWoouO18WsD2akmuPf1Mdv1RrfVETSlAAIpOP8AOcq1YczymCjX924iBWySf9Y7uzSonp6oqooTwo43I7V6XJ34vXybN56s39e2l3+ZagDW4fj2HwECQ4nG16jelGqsbPmcn3d6u9PVVNkAAAAAmOY8Qscnnxdqpl1xtnGTOmietZs7VcutKrHKibRUTS+3cpwBGfwY53/zi/8A2WD+8ycbx/mFbIwT3+cfHVmO3JX/AEVDH5ifTqRdp+RVAARPiQ2TGx4blUMTnuwl1Hzq1UVUrSJ0S6Reyqvyp9vUtjysV4bdaWtYjbLDMxWSRuTaOaqaVFT6KgCtZht12WK8jZI5E21zVRUX9x6kJFiuR8GksR8cx0GWws0yzMpLN5c1VV/WRir2c3suk9dr+J7p4juRNP4Ty1HJ6o3GbTf2Xq7gWhEeHC+bZ5RYj38NJmpvKX0Ttrek9j82eUcm5Gz4HjvHcjiXSaSTIZaFIUgT3VrO6vXXp9yl45ga3GsHXxVVznshRVdI/wDWkeq7c5fuqqBtAAAAAAAAD56n0AY1fG0KknmVqVeB6prqjia1dfTaIZIAAAAAAAAAAAAAAAAAAAAACP8APm/5Z/hvOf5Kcd6/L6l6er4jW9em9e4Fc5zWMV7l01qbVfohpcBzPj3J5pocNkmWZYURXs8t7HIn1RHIm0/A9sfn4MjyHL4aOGRsuJ8nzHu10v8ANYrk1+CJ7k74lY9tLHwcuowtbksLNHN1tTpdND1afG53r06cq+/v9QLgHnXnitV47EL0fFKxHscnuiptFPQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD8Pijkcx742udGu2KqbVq+m0+hJ+HeBm49SzdOSo6rA/M2JKjHLvcGmoxU7qutN9+/YrwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADQcx5DJx7DI+pGk2RtytrUYV9Hyu7Jv7J6r+BvyJym814rYvGSafUxNN19WIn/AOerlY1XfgndNe4Fbj23GY+BuRkiktoxPOfC1WsV3vpF9jJB4XI7EtKaOpO2Cw5ipFK5nWjHa7Lr319APcES3jnP3PYk3OoljR6K5GYyNqqiLvWy2A0PM+RScX4+7JxV22HNmij6HOVEVHPRF7/hs3xKeJ1N9zw+yvlR9cleNthvfWuhyOVfyRFUoMVcbkMRTusf1tswMlR2tdSOai71+YGWDysxPmqyxRzOge9itbKxEVzFVOzk322nr3IRuazfBMzXpclvfpHCXX9MeWmRGPgk6V+R6J7bRNL91XfbSB0AAAAAAAAAg+RSZLA+I0HIocHeylOXELSVKMfW9j0l69qnsmtF4AOXYuxyCDxYx+Ry1Kvj48/UliZXYquf0xN608zv2eiKib7+6di35l/MjO/6Nsf2bjOs4qlbyNLIzwI+1Q6/h5NruPrb0u/en1NdzTDX+QcTvYrG2mVrNlqNbI9yo3XUnUiqiKulTaenuA4N/MTBf6Ph/wBhDekFT4fzOSpDFa5ZDio4I0jhqYqtuKNqJpE6n/MvZEXv7qpV4LG3MVjvhr2Wnyk3WrvPmY1q6X9nSe3479QNkAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABg5DNYnELGmTydOksu+hLM7Y+vXrrqVN+qAZwJq/4h8Rx0SSSZ+nNv0bVkSdy/kzZrv4b5vMIjONcRvuR/6tvJp8NCiL6ORNqr2679tL+8C2B5wed8PH8R0ed0J5nl76erXfW++tnoABp6/IoJ+WXOOrBJHPWrMstkeqIkrXLpelPXSLpN/VVT277gAAYVbLUrmTu42CbrtUPL+Ij0qdHWnU3v77RPYDNBjXcjRxsCz37lepC3W5J5Wsam/TuqmDDy3jViZkMPIcVLLI5GsYy7GrnKvZEREXuoG3AAAAACIpr5XjVkEk+VZsPGse/wBtEf30W5LcsweSlv0+R8f8pctjmPj8ibsy1E71Y5U0vb1b31sCpBFt8RLMSdFvg/KGTt7PbBRSZiL9no5OpPvoyMVc5pmclBdmqUsPh+tXfDTtc+5I3WkR37Ld739U17gbbP4/M5GtEzDZ39Dytft8nwjLHW3Xpp3p39zCwWC5FQya28zy2TLReUsbIEpMrtRVVF6l6V7r21+alGAMTKVI7+JuU5mLJFYgfE9iKqK5HNVFTt+JzfiPiBJiOI47FXMFnLeSrR+T0R0lRFRHKjERfs3pT09jqYA0HHeTuzdy7jrWOlx+Rx7InWoHSNkaxZGq5qI5PXsnfsnqa7xSyEFLg1uvLEsj8i5KkKdkRJHbVqqqqiIidO9nk1UwPi1Kjv5DktNqo53dUngTXSnppvQu/dd/RB4q5DHwcOs4y3HJLYyLFjqRshc/qlRUVvdE7LvX4gVGGrTU8JQq2V3PBWjjkVF3tyNRF7+/dDNMDBssRYDHR2+v4hlWJJetdu60am9r9d7M8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAReUzN/lOUdgeNzTV6sMisyOWiRNRaT+Tidvu/fZV122BaA8qsCVasVdJJJUiYjOuV3U92k1ty+6/c13IK2et1YoMFkK1B7n/x1iaHzHMZr9hvoq70nf2VQM+5dq4+s6zcsxV4WfrSSvRrU/NTS4Pm+H5JmLGPw75rTa0XXJabEqQovVro6l1tfdNdlTelMCp4cYx9htzkNqzyG4xfkkvO2yNPo2NPl/HeyshhirwsggiZFFG1GsYxqNa1E9ERE9EA9AAAPjt9K9Koi67Kp9AEU6h4mdS9ObwWt9v8GeY0vJ+WcUt1ncsqULGJlf5Lr2Pa7qjeqp0q9qr6eqdk/uW+Inxb/mQ7/PIP9tALYgeUUKVvxS48mVqQWKc9SeJrbEaPY6RO6JpU1sviU8SMdavcTfaoMV93Fzx366NTa9Ua7XX1XpV3YDdUuPYTGS+bQw9CpIv7cFZjF/eiGxNBW5pgpON0s5byMFKvci62JPIjXKqfrNRPVyou07bML/lR4T/7fg//AM3/APdArD8uVWsVyNVyom9J6qYuKy1DN0GX8bZZZrSKqNkZvSqi6X1MwDkOd5BySbnODy2M44/FTztkoMdk39KWUX5ulzGr1I1q/Mi+6r9i0w9LnTctBNmsti30W9SywVYHI5+2rpNr6aXS/kYviPTkst41LDWfK+DPVXOcxiuVjPm2qqnom+n+otABz3luUbwnnEPJJoZH08hQfUkSNFXczPnjRde7v1UXv7+iHQiC8Y43N4Uy8yDzXULsM/8Ak6XW/wCtE/MD1wXAad9Uz/LqUd/NWnLK9kyq+Ku1ydokZtWqjU+qL39zE8NpOO8vwz8o7iuGp261lWfxFNidOtOaqLre9Kn5pvt6H3I+JEOexc+P4hTyF/J2YljjkjruYyuru3W5666UTaqi/VPY/HC6DuDcpdxmftBk6cU9V6N0108caNnRF91XSP8At9O4HRQAAAAAAAAAAAAAAARnP4HtyXE8jWY/4qHNxQdbUVemKRFSRFT00qNTv7fYswAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkOVZG/ks1V4hhrPws1qF8160jOpa8Hp8qf0nL2T6FFiMTUweKr4yjH5deuxGMT3X7r9VX1UlfDVPj25vOWV8y9byUsT5F/ZjjXTGJ9Gp9C3AAAACYzmN5hk8k6HHZynicWjU1JFXWSy9dfMi9XyonqqKnc/OD4VJjMwzL5DkOTy1uKN0USTyI2NjXa38qeq9vrr07dkUCpAAAAACI8VlSfjNbHRL13Ll6FteFP1pFRyKuk+yeq+xbnOcxg+c5Hny5OtDjI61SN0WPnsSK5sLXJ8z+hO6ye3f5e3v6gdGPzJG2WN0b0216K1U+qKRS8a8QFTX/KCz/6RCUnH8ZdxOKZVyGWnylhHK51iZqNXv7Iie34qq9/X2QNRhvDbi+Em82Gj8S5E1GlxfOSHvv5Ed+qu/dO5+uV5PA8bxUz3wUfj3xOSnWWFrnzS60xqNRNrt2kP3n8jy1Mi3Hcdw1VWuYjlyN6bULV77b0N+ZV9O/39D98e4jFirDsnkrK5XMy/wApenYiK1Na6Y09GN9eyfVQPvBcG/j3D6FGVHNsLH507Xa+SR/zOb2+irr8ihAAAAAY9+lBk8fYoWmq+CzE6KRqLrbXJpe/t2UyABgYTD1cBiYMZSWVa8CKjPNkV7kTe9bUmfE/qq4fGZeP5ZMbk4JfN9Ejaruld/Zdoi/iWpr89jW5nAX8Y5EX4qu+JN67KrVRF7/RdKBn+p9Jjw8yMl7h9WCyjm3MdujaY5FRWyR6aqL9V1pd/cpwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAhLEN7w9yE12nC+5xy5O6a1BHGr5qb3JtXt16s2ibT22WlO5WyFSK3TnZPXmb1RyMXaOQ9lTaaUj5+E3MVclu8OyqYhZXeZLQki8yrM/8AyfVm9Iiq30ROwFiCHdz3IcfVsPMOP2aqq7pbdoNWes/t/wDM37J3UzsPz2ryHKRVMPislYrqq+ddfAscMWk3rbvV2+ntr0XfsBVAAAAAAAAAAAAAAAAAAAAAAAAAAD4jWt30tRNrtdJ6qfQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADUci5NjOLUWXMnK9rJJPLjZGxXve7SrpET7IpPwcr5nlHRyY7hSQVZFR7Jr11rFfGvoqtRNtXXfXfX3AtwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHjZt1qcSy2rEUEbUVVfK9GoiJ691P1BPDagZYrzMmhkajmSRuRzXIvoqKnZUA9AAAAPOWeGHXmysj36dbkTYHoDUJyrBvzcGFhyUE9+fr1DC/zFb0pterW+nt9dG3AAAAAani/IIeUceq5mvC+CKz19Mciork6Xub31/kgbYAAADU8X5BDyjjtXNV4XwR2evUciork6Xq1fT7tA2wAAAAAAANdjs5SymQyNGs56zY2VsU6ObpNq3aaX3T1T8vwNiRPCf56c0/z2L/YUtgPCO7VmuTU47Eb7ECNdLE1yK5iO9Np7b0e5E8d/xscv/wD2af8AZlHyPNN47gLeXfVmtNqtR7oof1lTaIq/giLtfsigbMHhDdqWHMbBahlc+JJWIyRHK5i+jk16tX6+h7gaXCciZmspmaLaywrirKQK9X78zbd71rt79u5uiLwnVj/FbklKRUYmRq171djfRWtTy3uX6L1fv9S0AGvdnKLeRNwKvd8c6qtvp6V0kaO6d7+u99vsbAiZP8eMX/8AHV/t1AtgDX5vC1eQY12PuvnbA9yK9IZXRq9EXu1VT1avoqAaK3z6CW+7Hcbxs/IbTGqr1qva2CNfZHSu+VP6/wDcY7rHijM5ZYqXGa0b/mbDNJM98aL+y5zeyqnoqp2+hV4/G0sTTZTx9WKtXj/VjibpE/4mUBM4Hlc1nI/oLPU/0dmmtVzWN26Gy1PV8T/dP/hXun30pTEh4k0pv0FXztOPrt4Gyy83XZXRt/lG7/oq3uqe/SU9C5DkcfWvV3dUNmJssa61trkRU/qUDIAMe/ehxtCe9Y6/KrsWR/QxXO0nrpE7qBreMciZyWnbsMrOr/C3JaqtV/V1dC/renvv0N0cr8MOZYmP4vFKlpbN7LTyw9NZ7m9Lta2qJ29O+/T3OqAa/OQ5afGPjwluCrcVU6ZJ41e1E33TX/mazhvIbmbr3qmVhhhymLtOrWWQ76Ha7te1F7o1yem/oUSqjUVVVERO6qvsRHh+rr+c5TnImL8BfutbVlX0lSNFark+yr6KBcEDJn+aZrk+ZxWATDVquNlZE6a02R0qdTd9SIi9K+/ZUL4h+JO+G8ROX052rHNPJBYia79uPpVOpPqm+wFHx+vnK1F7M/erXLKyKrX14VjRG6Tsqe672bUAATeJz1y7zvP4WVIkq46Ou6Hpbpyq9nU7a77lDLLHBE+aaRsccbVc9710jUT1VVX0Q5zguS4CHxN5TclzmOZWniqJDM63GjJFSPS9Lt6XS+ugOkg1OZwOG5ZjYoMnA27U6kmj6ZXNRV12VFYqbTSkpk+EN4dCud4RHJXnqNV9jHrLJJHcYndUVHKq9SJvWvcDoIMDBZevnsHTytVU8q3C2RERyL0qvq1VT3Rdov3RTS8+y13CY3G5GtZWCvFlK/xytRFV1dVVHJrXuqp6dwKkAAADysxPnqywsmfA+RitbKzXUxVTXUm9ptPXuBosznblDmvG8RCka1solrz+pu3J5caOb0rvt3KI5Fyjh09PkfGkynJctkYrVt9bbpUjfEj29+lyeiLpEVPdO3YuMP4d8UwGSjyOLxXw9qNFRsnxErtbTS9nOVPQClMd96pHejovsxttSsWRkKuTqc1PVUT6dzIIrkOqvipxOdqK59uG3XfteyNaxHIqffaqBQ8h5DQ4zjfjr6yK10jYoooWdUkr19Gtb7r6/uNPhPETHZzPMwseLy9S2+NZdW6vQjWp7r3VUT23rW+xhV+jPeK9+awiOp8epxxMZIu2tnkXr8xE9l6UVu/sT+Iz8+W8Y62V8nyadtlnF1+l/UsnkIj3Od9lVya1v+rYHWTwlu1YLUFWWxGyez1eTG5yI6TpTbtJ76Tup7nKeVZzkSeI/HXt4m9X1JLraca3WIt1qxoiu3r5NJp2l3vegOrAxsdYs2sdBPbpupWJGI6Su56PWN3unUnZfxMkD8SyxwQvmmkbHHG1XPe5dI1E7qqr7IfK9iG3XjsV5WywytR7HsXaOavdFRTVcy/mTnf9G2P7Nx58G/mJgv8AR8P+wgHhmvELivHsi7HZXKpBaY1HOjSCR+kVNptWtVPQzeP8pwvKYZpsLd+KjgcjZF8p7NKqbT9ZE2aDw+8t+X5bJY0uQ/TUzXK/+U8hNeUnfv066tex5ZTI/C+NeGrSSSIyzi5Y2NRfl6upzu6b90Zr8dAXYAAm+U8ul4u9r34HIXaaR+ZNartarIU3pd999k7/APhdb6rahu1IrVaRJIZmI+N7fRzVTaKermo5qtciKippUX3Ijw+jfh8tyTiqSLLWxVqOWs5e3THO1XozX2Xff3VV7IBqPEu/exfMMVfxzY32amNtzRpKm2p0t2q6VfVE2v5FtieVYXJ06ckeXoumsxsckbZ2o5XORO3Sq73v29Tw5FwjB8pv07mWgkmdTRyMjSRWsdvX6yJ66VN/69nKLODxmG4Hl1+Chiz3GMnGvndHzSsdMnlucvqrXNcuvT9VAO7gAAAAAAAAAAAAAAAAAAAAAAAAAAS2a5zXp3ZMThqVjM5ZnyrBWb8kLl9PNk9Gp6/ft7H3xJylvDeH+VvUpPLnaxjGv929b2sVU++nLr7m2wGBx3HMTDjsbC2OGNqbdpOqR2kRXOVPVV16gT1Tw8rZCVmS5fMubyS6Xpeqtrw99oxkadtJ9979/Ur4IIasDK9eFkMMbUayONqNa1E9ERE7Ih6AAAANByLhmI5RPDNkviuqFqtYkNl7E0q79EXW/v8A3IauLwn4e3fn0Jrf08+1I7p/DuhZgDV4jjWDwKJ+isVVqORvQskcSI9yfRX/AKy/mptDybarvsvqtnjdPG1HviR6K9rV3pVT1RF0v7j1AAAARnhF/iwxH/Xf20hZkZ4Rf4sMR/139tIBZgwIM1RsZu1hopVW5UiZLKzpXSNd6d/Rf+JngDjlKWet/wCj9irkVh0DattssrmOVF6UtuTtr17qi/kdjOK8T5O634a1eH4bET5fIWK9qK01kiQsrMe9/wAyvcioq6eion9e+wHaWuRzUcndFTaH0gfCyTO5TDVsvk8z59ZK61IqLYURGLGqN8xz1XbnL0rv/KUvgJfMZq9U8QeOYmGVG1L0VlZ2dKL1Kxm29/VNKVBF+ICfC5TiWTi7WGZqKqi//pyo5Hp/UhaAAABE8J/npzT/AD2L/YUtjnrcbzXA8pzt3D4vH3a2TnZK101noVNN16fmpgU8jy6XxcxrMpj6ld6456PhitKrEhV/d6evzbRO3vpPT1QNjcrcswXO81l8RxxmXr5SKBGP+Ojh8tWM6VRUd3Xv/V7/AE9JeM825JUdX5DyGtRp2WKk9THV06tKndnW7fb79/oXgA574R4PF1MAmRjruZl066d3zJFc6JzH92f/AA+jV0n2OgSNc+NzWvVjlRURyIiq1fr3IrgT20M9yzBzORLTMq+8ib9Y5mtVq/lrv+JbgchyXFcvD4jYaLMcvyUrslVlgbcpNSpIiM+dI/l3tNrvuhWxeHflTMk/hnyx/Q5HdL8ntq69lTp7obLN8dlyvJMBlY7DI2YqWV8kbkXb0ezXZfsqJ+/7d9+AOeckvz8f8U6+bkxGTvU3Yb4bqo1llVH+crtL3RE7f60OhgDm+e8UshXxUlnE8VycXQrWus5SssUMW3InzIi7VPzQo8C/nL8g1c83ALQcxV6qDpvM37a6uyobXO46LL4G/jp29Udmu+NUREVU2i6VN+6L3T7oazw/yEuU4JiLM7VbKldIn9TtqqxqrFVV+q9O/wAwKMA85llbBIsDGvlRqqxr3dLXO12RV0uk376UCZ8Scq3F8HvxpGss+QYtGvEm9yPlRW6TSeqJ1L99aNzx+jJjOOYzHyqjpKtOKF6p6KrWIi/6jnUPAuc57kK5/OZ2tjbNd/VSjZA222Hf9FrlRrdaTS912m+xd8fxefxzp1zXJP0yj0Ty0+BZX8vW9/qr3329foBuwABrMNgKWCfeWl5jW3rLrL2OdtrHuRN9KeydtmzAA5/4i5e7lXu4Lg6s8mSvwskksNf0R14utNq5foqIqL9l133o+47gvJH0a2OyfKpadCpGjYYsKnwz9omk6n6VVTW+2u6rsuEpVW3nXkrxpafGkTpulOtWIu0bv6bPcDWYHC/oKk6r+lMjkep6v83IT+bInZOyLpO3b0JrmVPN4rktHluAx7sjKys6jbqt/WfGq9bVT6ad6qnf0+5cACFx3JOQcdvRQc5dB5F9GJWt1Yl8uGVfWJ+vy0vp2Xv9Log+dTpyyZnBsXNG+aw5smQmT5kpxMcju+v21VE0n79b2XYH5lijnifDNG2SORqtex6bRyL6oqL6oQmJ4Jj4+d5+a3xuguLlir/BI+rGsaKjFR/S3XyrtO/ZC+AH4jjjhiZFExscbGo1rGppGonoiJ7IfpzUc1Wr3RU0p9AET4TKreGOrov8VXu2I4m/0Wo9V1+9VNl4h0kv+H+biV6M6Kj5kVW7/k/n1+fTr8yV43/DrjVKxiKnEYp+u5LKy5NfY1mnO33Ynf0+/uVOCTm0t5XcibhGUHxr/FVPMdKjl1pFV3y61vfqBhYHxD4y7j2Ndez1GK0tSJZ41k10P6E6k19l2anlvN8Nk8jxqhhM22ay/OVXStrPdpYtq1yOVO2tqnZV7/QtP4M8f/8AYWN/7JH/AHErzvFY7HO4u6jQrVVfySmjlghazq/X9dJ3AvgABouW8cdyTH1YYbSVrFO5Fbgkczrb1MX0cm0VU0q+ip7G9AAEh4k1LT+P1slRhfLZxF6G61GJtelq6d2TuqaVdp9ivAEhd8POL8ivPzc8Nhz7zWSP6Z3sbInSmtt39DX8nxlHimS4fkqldtfF4q3LWfFH+wlhvT17X1RHJtfddl+SfibjJsnwPIfDP6J6aJbjVfT+LXqX2X2RdffQFYeb4IZJY5pIWPki2sb3NRVZtNLpfbaGLhMnFmcHSycCqsdqBkqb1tNp3Rde6L2X8DOAAAD8TQxWIXwzRslikarXse1Fa5qppUVF9UUj/DaxLBQyXHZ5HSPwd19aNZF+dYd7jVUX21tE9tJ29CzJ+PjEtbm8/I6uRWKK3A2K3T8naTOaio1/VvsqJr2/1ga7kXHcrSzycr4s1suQc1I7lGWTpjuRppE7qumuRE7L/wCSxnKcbm1sR88z9L9G2aWQqsr1EnbMyCFHfM97m9l25U+mvzOyGg5zgZ+TcNyGHqyMjnsNasav9FVr2vRF+m+nW/bYG2yEFi1jp4Klx1OxJGrY7DWI9Y3ezuley/gS9TifKm3YJMhzy1arRyNe+CKjHCsml2idaKqom0Tae6bT3Kun8StKBbjY22fLb5yRKqsR+vm6VXvre9bPYCT8QOc1uFYlr+hZb1pHNqx9Kq1HIn6zl/ooqptN7Xfb6pMcV53wrDNtX8lyf4zMZJzH3bCU52tVWpprWt6OyNRdff8AqTqYAwsTl6GdxkOSxlhLFWbflyI1W70qovZURU7opyPxWV1XkmVotZJJNncbWZWZGxV65GWG/L9101f/AAp2eONkTOiNjWN2q6amk7rtSA8T8bFioqvOakKLkcRPEr1WVyeZCrulWa9PV/09FX8AL58scb2MfI1rpF0xFXSuXW9J9eyKp+yF51aqQ5viWVisxSSQZZtZWJImkZM1Wucv4dKfvLNlyrK9GR2YXuX0a16Kqge4AAAAAAAAAAAAAAAAAAAAAAAMbI0K2Ux1ihbjSSCxGscjV90Uj8Hm7HDUq8a5T/FwRp5NHLud/E2ET9Vrv6DkTtpe3yr3+tyYmUxlPM42fHX4GzVp2Kx7HfT6p9F+i+wGUi7TaH0iW8c5hx2NG8ez8WSqt0jaeXYqqxqezZW996RE0qa9z8sz/iJYVlVOG1KsqvRH25cg10Ot916E+bun3AuAABr85Rv5HGPr43KvxdlXIrbLIWy6RF7p0u+pM/8AJlWvNR+f5BmcvKvdUktLHE131ZG39X8NqWwA0XHOGYTi0k8uMrvbLYREkllldI5UT0Ta+iG9AAAAAc+xPG+ecTotxOBvYO5jonPWD9IMlbIxFcrtfJ2X1OggDkWN/h67xHzSQrx9mTWpClhzkmWFGfsqz36vrvsXPH8JyWjfW3muUrkY3MVFqMpsjY1yqndHJ3VE7/vNbk3JhPFjGZF6arZqk6gvT21M13W1zvrtPlT6FsAPKvWr1I/LrQRwsT9mNiNT9yHqAIzg0UtDkHLMYyJzKMOQbNAit0iOlZ1PRvtpO2kT039yzAA5J4lVuatw02ayOQxlepircVmlDSjc56vR/SxznPT1RH/dF16FL/BHmn/OLN/9Li/7xneJX+LvNf5v/vQ3WEc5+Cx73uVznVY1VVXaqvSgH3EVLlHGQ1r+RdkbLEXrsuiSNX9/6Kdk+hmgACJtf47KP+g3/wBqpbElZxl13ixSybaz1pNxD4XTonyo/wAzfSv30qf+EUCtAAGpXjtJeVN5I18zLiVFqOa1yIx7Orq+ZNbVd/f6G2AAAAAAABG+GqNp43K4ZXO83GZWxEqP7OViu6mP17I5F7fXSlkRSt/QXiyj1+WtyOn0oqe9iHvpf+gvZV99oBagAAAAAAAAAAAABKcu5Jk6dqHA4DHTWcvdj6o53M/iKzVVU63u9O2l7f8ABFqwBoOH8WbxXFy132vjbdmd09m0saMdI5y/n6fj9fwN+AAAAAAAAAAMLJYijl/hPjYfN+DsstQ/MqdMrN9K9vXW17GaAAAAAAAAAB8VEVNKm0U+gD41qNajWoiInZERPQ+gAAAAAAAAAAAAAAAxcljKWYx82PyNdlirOiJJE/0dpdp/WiL+RlADm3MfCzjUXE8jPiMQyC9XhWaJzZJHKvT8yt0qrvaIqfmbTh/D+HS0MXyPGYiGOd8LZmPSV7uh6t7ppXKm0XafZU+xZvYkkbmL6ORUU1vHMFW4zgauHqSSSQ1kcjXyKnUu3K5d6+6qBtAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABi28bSvT1Z7VZkstOTzYHOTvG7SptPyX/V9DKAAAAAAAMHNYmtnsNaxVtZGwWo1jesa6cifVFVF7mTWrx1KsVaJFSOFiMbtdrpE0h6gAAAAAAAAAAAAAAAAATXL8Fdy1rBXKCMfLjcjHM9j3dKLGvZy/inrr8SlAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMXJWLdXHTz0aS3rLG7jrJKkfmL9OpeyfiBlAi15NzzS68OkRfbeag/uKjEyZCbF15MrXir3XM3NFC/rY130Rf/H4r6gZgPOdJlryJXcxsysXy3PRVajtdlVE1tNkVjuRcmw3J62J5gyktfIp0U7dFjvL87+g5XLtFVPTt/v0FyDVcokysPGchLhOn9IRwq6Dqaju6d10i9lXW9b99Hpx/LwZ7AUspXej47MSO3rWnejk/FFRU/IDYgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEx4i0obfB8lLIipLTiW1XkaunRyM+ZrkX29P3KpTkR4qMydjj9WpSo27lWe4xL8dOJXyOhT5lRETv3VE79vxApsHakyvGsfbs6823Tikk6U0m3MRV1+8m/DZy4ynkeKTqjZsLceyJq9nPrvVXxyL+O1/D3MrBZDl9y9XdPgKONwz2/JG+VUsRM18qK1OyL6fL7enseGa4xyGPlUvIeNZGjHPZrtrzQ3onK1Eau0Vqt/1aAqZMhTiyEOPksxttzsc+OFXfM9rfVUT7bMk5dDByZvi3gf4Q3KL5UqTrH8CxyNVul2jupPr9PodRAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACRymPuS+KWCvx1pXVYaVhskyN+Rir6Iq+yrsrgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP/9k="]	900	300	1200	2026-08-08 14:53:44.443581+05:30	2026-08-08 14:53:44.429244+05:30	2026-08-08 14:53:44.429244+05:30
3	4	tenant-1	washing machine is not showing	[]	["data:image/jpeg;base64,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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gKA0NF/gP/9k="]	0	0	0	2026-08-08 15:10:02.589919+05:30	2026-08-08 15:10:02.568739+05:30	2026-08-08 15:10:02.568739+05:30
4	5	tenant-1	job is to fan cail is not working	[]	["data:image/jpeg;base64,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"]	500	600	1100	2026-08-08 16:40:18.47729+05:30	2026-08-08 16:40:18.451639+05:30	2026-08-08 16:40:18.451639+05:30
\.


--
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.jobs (id, tenant_id, customer_name, location, issue_description, priority, service_type, contact_number, preferred_service_date, required_skill, status, assigned_technician_id, sla_deadline, attempt_count, gps_active, work_report, customer_id, customer_email, geofence_radius, previous_priority, bumped_at, site_latitude, site_longitude, site_address, created_at, updated_at, assigned_at, en_route_at, on_site_at, completed_at, cancelled_at, closed_at, assigned_by, en_route_by, on_site_by, completed_by, cancelled_by, closed_by, cancellation_reason, closure_reason, rejection_reason, rejected_at, rejected_by_tech_id, share_token, share_token_expires_at) FROM stdin;
5	tenant-1	Carl Customer	Navallur	My fan is not working: the fan coil is getting heated and fan would run	MEDIUM	Technician	90877654321	2026-08-19	Other	COMPLETED	2	\N	2	f	job is to fan cail is not working	176973fb-629e-49f7-89f9-01807a93d3cf	customer@fieldops.com	100	\N	\N	\N	\N	\N	2026-08-08 15:04:53.851849+05:30	2026-08-08 16:40:20.636469+05:30	\N	\N	2026-08-08 16:38:12.364545+05:30	2026-08-08 16:40:20.639762+05:30	\N	\N	\N	\N	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	\N	\N	i have another job	2026-08-08 15:48:34.25248+05:30	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N
6	__platform__	Yaswanth S	Kombedyu	Warter Leak: Water leak from the Ro purifier	MEDIUM	Water Technician	9876543210	2026-08-11	Other	IN_PROGRESS	4	\N	2	f	\N	e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	yaswanth@gmail.com	100	\N	\N	\N	\N	\N	2026-08-10 10:14:15.534919+05:30	2026-08-10 15:16:46.624115+05:30	\N	\N	2026-08-10 15:16:46.626726+05:30	\N	\N	\N	\N	\N	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
4	tenant-1	Carl Customer	Kodambakkam	Water Leak in Weashing Mechine: the washing mechine have a problem	MEDIUM	Plumbing	9087654321	2026-08-10	Plumbing	EN_ROUTE	2	\N	2	f	washing machine is not showing	176973fb-629e-49f7-89f9-01807a93d3cf	customer@fieldops.com	100	\N	\N	\N	\N	\N	2026-08-08 14:50:09.477239+05:30	2026-08-08 15:55:42.886029+05:30	\N	\N	2026-08-08 15:09:32.308977+05:30	2026-08-08 15:10:05.144925+05:30	\N	\N	\N	\N	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	\N	\N	\N	\N	\N	\N	\N
3	tenant-1	Carl Customer	Kodabakkam Chennai	Networking problem: Networking problem in the wifi	MEDIUM	Networking	9566316840	2026-08-08	Network Support	COMPLETED	2	\N	2	f	washing mechine issue	176973fb-629e-49f7-89f9-01807a93d3cf	customer@fieldops.com	100	\N	\N	\N	\N	\N	2026-08-08 12:37:42.631256+05:30	2026-08-08 14:53:44.829646+05:30	\N	\N	2026-08-08 12:59:41.868623+05:30	2026-08-08 14:53:44.832399+05:30	\N	\N	\N	\N	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	\N	\N	\N	\N	\N	\N	\N
2	tenant-1	Carl Customer	Chennai Kodumbakam	Pipe is dameged: the pipe is dameged and water is lacking	MEDIUM	Plumbing	98765432109	2026-08-07	Plumbing	EN_ROUTE	2	\N	2	f	i completed the job ac is repair	176973fb-629e-49f7-89f9-01807a93d3cf	customer@fieldops.com	100	\N	\N	\N	\N	\N	2026-08-06 10:43:47.271694+05:30	2026-08-08 15:49:38.354144+05:30	\N	\N	2026-08-08 12:24:12.556336+05:30	2026-08-08 12:31:09.656661+05:30	\N	\N	\N	\N	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	\N	\N	\N	\N	\N	\N	\N	\N	\N
1	tenant-1	Carl Customer	Chennai 	Ac Mechnice: ac is fault to do dust 	HIGH	Ac Mechnice	84849404044	2026-08-07	HVAC	EN_ROUTE	2	\N	2	f	\N	176973fb-629e-49f7-89f9-01807a93d3cf	customer@fieldops.com	100	\N	\N	\N	\N	\N	2026-08-05 17:55:56.339195+05:30	2026-08-08 16:41:35.675675+05:30	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N
\.


--
-- Data for Name: notification_deliveries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification_deliveries (id, tech_id, tenant_id, job_id, fcm_message_id, status, error_message, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: notification_templates; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification_templates (id, name, type, channel, locale, format, title_template, body_template, version, is_active, created_at, variables, tenant_id, agent_type, is_deleted, deleted_at, deleted_by) FROM stdin;
705	Job Created (SMS - English)	created	sms	en	text	Job Created	Hello {{customer_name}}, your job '{{job_title}}' has been created.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
706	Job Assigned (SMS - English)	assigned	sms	en	text	Job Assigned	Hello {{customer_name}}, {{technician_name}} has been assigned to {{job_title}}. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
707	Technician En Route (SMS - English)	enroute	sms	en	text	Technician En Route	Hello {{customer_name}}, {{technician_name}} is on the way. Expected arrival: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
708	Technician Arrived (SMS - English)	onsite	sms	en	text	Technician Arrived	Hello {{customer_name}}, {{technician_name}} has arrived for {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
709	Job Completed (SMS - English)	completed	sms	en	text	Job Completed	Hello {{customer_name}}, {{job_title}} has been completed successfully. Thank you for choosing us.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
710	Job Cancelled (SMS - English)	cancelled	sms	en	text	Job Cancelled	Hello {{customer_name}}, your {{job_title}} has been cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
711	Job Assigned (SMS - English)	job_assigned	sms	en	text	Job Assigned	Hello {{customer_name}}, {{technician_name}} has been assigned to {{job_title}}. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
712	New Job Assignment (SMS - English)	technician_job_assigned	sms	en	text	New Job Assignment	A new FieldOps job has been assigned. Open the app for details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
713	Journey Started (SMS - English)	technician_journey_started	sms	en	text	Journey Started	Your journey has started. Open FieldOps for job details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
714	Arrival Recorded (SMS - English)	technician_arrived_on_site	sms	en	text	Arrival Recorded	Your arrival has been recorded. Open FieldOps for job details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
715	Job Completed (SMS - English)	technician_job_completed	sms	en	text	Job Completed	The job completion has been recorded in FieldOps.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
716	Job Cancelled (SMS - English)	technician_job_cancelled	sms	en	text	Job Cancelled	A FieldOps job was cancelled. Open the app for details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
717	Job Assigned (SMS - English)	dispatcher_job_assigned	sms	en	text	Job Assigned	Assignment confirmed for {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
718	Technician En Route (SMS - English)	dispatcher_en_route	sms	en	text	Technician En Route	{{technician_name}} is en route. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
719	Technician On Site (SMS - English)	dispatcher_on_site	sms	en	text	Technician On Site	{{technician_name}} is now on site.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
720	Job Completed (SMS - English)	dispatcher_completed	sms	en	text	Job Completed	{{job_title}} has been completed.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
721	Job Cancelled (SMS - English)	dispatcher_cancelled	sms	en	text	Job Cancelled	{{job_title}} has been cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
722	Technician En Route (SMS - English)	technician_en_route	sms	en	text	Technician En Route	Hello {{customer_name}}, {{technician_name}} is on the way. Expected arrival: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
723	Technician Arrived (SMS - English)	technician_arrived	sms	en	text	Technician Arrived	Hello {{customer_name}}, {{technician_name}} has arrived for {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
724	Job Completed (SMS - English)	job_completed	sms	en	text	Job Completed	Hello {{customer_name}}, {{job_title}} has been completed successfully. Thank you for choosing us.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
725	Job Cancelled (SMS - English)	job_cancelled	sms	en	text	Job Cancelled	Hello {{customer_name}}, your {{job_title}} has been cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
726	ETA Updated (SMS - English)	eta_updated	sms	en	text	ETA Updated	Hello {{customer_name}}, updated ETA for {{technician_name}} is {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
727	Job Created (EMAIL - English)	created	email	en	html	Job Created	<h2>Job Created</h2>\n<p>Hello {{customer_name}},</p>\n<p>Your service request <strong>{{job_title}}</strong> has been created.</p>\n<p>Thank you,<br>FieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
728	Job Assigned (EMAIL - English)	assigned	email	en	html	Job Assigned	\n            <h2>Job Assigned</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                <strong>{{technician_name}}</strong> has been assigned\n                to your service request.\n            </p>\n\n            <p>\n                <strong>Job:</strong> {{job_title}}\n            </p>\n\n            <p>\n                <strong>ETA:</strong> {{eta}}\n            </p>\n\n            <p>\n                Thank you,<br>\n                FieldOps Team\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
729	Technician En Route (EMAIL - English)	enroute	email	en	html	Technician En Route	\n            <h2>Technician En Route</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                {{technician_name}} is currently travelling to your location.\n            </p>\n\n            <p>\n                ETA : <strong>{{eta}}</strong>\n            </p>\n\n            <p>\n                Thank you,<br>\n                FieldOps Team\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
730	Technician Arrived (EMAIL - English)	onsite	email	en	html	Technician Arrived	\n            <h2>Technician Arrived</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                {{technician_name}} has arrived at your location\n                and will begin work shortly.\n            </p>\n\n            <p>\n                Job : {{job_title}}\n            </p>\n\n            <p>\n                Thank you,<br>\n                FieldOps Team\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
731	Job Completed (EMAIL - English)	completed	email	en	html	Job Completed	\n            <h2>Job Completed</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                Your service request has been completed successfully.\n            </p>\n\n            <p>\n                Job : {{job_title}}\n            </p>\n\n            <p>\n                Thank you for choosing FieldOps.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
732	Job Cancelled (EMAIL - English)	cancelled	email	en	html	Job Cancelled	\n            <h2>Job Cancelled</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                Unfortunately your service request\n                has been cancelled.\n            </p>\n\n            <p>\n                Job : {{job_title}}\n            </p>\n\n            <p>\n                Please contact support for assistance.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
733	Job Assigned (EMAIL - English)	job_assigned	email	en	html	Job Assigned	\n            <h2>Job Assigned</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                <strong>{{technician_name}}</strong> has been assigned\n                to your service request.\n            </p>\n\n            <p>\n                <strong>Job:</strong> {{job_title}}\n            </p>\n\n            <p>\n                <strong>ETA:</strong> {{eta}}\n            </p>\n\n            <p>\n                Thank you,<br>\n                FieldOps Team\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
734	New Job Assignment (EMAIL - English)	technician_job_assigned	email	en	html	New Job Assignment	\n            <h2>New Job Assignment</h2>\n            <p>\n                A new FieldOps job has been assigned to you.\n                Open the technician app for details.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
735	Journey Started (EMAIL - English)	technician_journey_started	email	en	html	Journey Started	\n            <h2>Journey Started</h2>\n            <p>\n                Your journey has started.\n                Open FieldOps for job details.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
736	Arrival Recorded (EMAIL - English)	technician_arrived_on_site	email	en	html	Arrival Recorded	\n            <h2>Arrival Recorded</h2>\n            <p>\n                Your arrival at the job site has been recorded.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
737	Job Completed (EMAIL - English)	technician_job_completed	email	en	html	Job Completed	\n            <h2>Job Completed</h2>\n            <p>\n                The job completion has been recorded in FieldOps.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
738	Job Cancelled (EMAIL - English)	technician_job_cancelled	email	en	html	Job Cancelled	\n            <h2>Job Cancelled</h2>\n            <p>\n                A FieldOps job assigned to you was cancelled.\n                Open the app for details.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
739	Job Assigned (EMAIL - English)	dispatcher_job_assigned	email	en	html	Job Assigned	\n            <h2>Job Assigned</h2>\n            <p>\n                Assignment confirmed for {{job_title}}.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
740	Technician En Route (EMAIL - English)	dispatcher_en_route	email	en	html	Technician En Route	\n            <h2>Technician En Route</h2>\n            <p>\n                {{technician_name}} is en route.\n                ETA: {{eta}}.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
741	Technician On Site (EMAIL - English)	dispatcher_on_site	email	en	html	Technician On Site	\n            <h2>Technician On Site</h2>\n            <p>\n                {{technician_name}} is now on site.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
742	Job Completed (EMAIL - English)	dispatcher_completed	email	en	html	Job Completed	\n            <h2>Job Completed</h2>\n            <p>\n                {{job_title}} has been completed.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
743	Job Cancelled (EMAIL - English)	dispatcher_cancelled	email	en	html	Job Cancelled	\n            <h2>Job Cancelled</h2>\n            <p>\n                {{job_title}} has been cancelled.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
744	Technician En Route (EMAIL - English)	technician_en_route	email	en	html	Technician En Route	\n            <h2>Technician En Route</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                {{technician_name}} is currently travelling to your location.\n            </p>\n\n            <p>\n                ETA : <strong>{{eta}}</strong>\n            </p>\n\n            <p>\n                Thank you,<br>\n                FieldOps Team\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
772	Job Assigned (IN_APP - English)	assigned	in_app	en	text	Job Assigned	Your job '{{job_title}}' has been assigned to {{technician_name}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
745	Technician Arrived (EMAIL - English)	technician_arrived	email	en	html	Technician Arrived	\n            <h2>Technician Arrived</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                {{technician_name}} has arrived at your location\n                and will begin work shortly.\n            </p>\n\n            <p>\n                Job : {{job_title}}\n            </p>\n\n            <p>\n                Thank you,<br>\n                FieldOps Team\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
746	Job Completed (EMAIL - English)	job_completed	email	en	html	Job Completed	\n            <h2>Job Completed</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                Your service request has been completed successfully.\n            </p>\n\n            <p>\n                Job : {{job_title}}\n            </p>\n\n            <p>\n                Thank you for choosing FieldOps.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
747	Job Cancelled (EMAIL - English)	job_cancelled	email	en	html	Job Cancelled	\n            <h2>Job Cancelled</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                Unfortunately your service request\n                has been cancelled.\n            </p>\n\n            <p>\n                Job : {{job_title}}\n            </p>\n\n            <p>\n                Please contact support for assistance.\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
748	ETA Updated (EMAIL - English)	eta_updated	email	en	html	ETA Updated	\n            <h2>ETA Updated</h2>\n\n            <p>Hello {{customer_name}},</p>\n\n            <p>\n                Your technician's estimated arrival\n                time has changed.\n            </p>\n\n            <p>\n                New ETA :\n                <strong>{{eta}}</strong>\n            </p>\n\n            <p>\n                Thank you,<br>\n                FieldOps Team\n            </p>\n            	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
749	Job Created (PUSH - English)	created	push	en	text	Job Created	Job '{{job_title}}' created.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
750	Job Assigned (PUSH - English)	assigned	push	en	text	Job Assigned	{{technician_name}} assigned. ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
751	Technician En Route (PUSH - English)	enroute	push	en	text	Technician En Route	{{technician_name}} is on the way.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
752	Technician Arrived (PUSH - English)	onsite	push	en	text	Technician Arrived	{{technician_name}} has arrived.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
753	Job Completed (PUSH - English)	completed	push	en	text	Job Completed	{{job_title}} completed successfully.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
754	Job Cancelled (PUSH - English)	cancelled	push	en	text	Job Cancelled	{{job_title}} cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
755	Job Assigned (PUSH - English)	job_assigned	push	en	text	Job Assigned	{{technician_name}} assigned. ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
756	New Job Assignment (PUSH - English)	technician_job_assigned	push	en	text	New Job Assignment	A new job has been assigned. Open FieldOps for details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
757	Journey Started (PUSH - English)	technician_journey_started	push	en	text	Journey Started	Journey started. Open FieldOps for job details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
758	Arrival Recorded (PUSH - English)	technician_arrived_on_site	push	en	text	Arrival Recorded	Your arrival at the job site was recorded.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
759	Job Completed (PUSH - English)	technician_job_completed	push	en	text	Job Completed	The job completion has been recorded.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
760	Job Cancelled (PUSH - English)	technician_job_cancelled	push	en	text	Job Cancelled	A FieldOps job was cancelled. Open the app for details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
761	Job Assigned (PUSH - English)	dispatcher_job_assigned	push	en	text	Job Assigned	Assignment confirmed for {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
762	Technician En Route (PUSH - English)	dispatcher_en_route	push	en	text	Technician En Route	{{technician_name}} is en route.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
763	Technician On Site (PUSH - English)	dispatcher_on_site	push	en	text	Technician On Site	{{technician_name}} is now on site.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
764	Job Completed (PUSH - English)	dispatcher_completed	push	en	text	Job Completed	{{job_title}} has been completed.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
765	Job Cancelled (PUSH - English)	dispatcher_cancelled	push	en	text	Job Cancelled	{{job_title}} has been cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
766	Technician En Route (PUSH - English)	technician_en_route	push	en	text	Technician En Route	{{technician_name}} is on the way.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
767	Technician Arrived (PUSH - English)	technician_arrived	push	en	text	Technician Arrived	{{technician_name}} has arrived.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
768	Job Completed (PUSH - English)	job_completed	push	en	text	Job Completed	{{job_title}} completed successfully.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
769	Job Cancelled (PUSH - English)	job_cancelled	push	en	text	Job Cancelled	{{job_title}} cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
770	ETA Updated (PUSH - English)	eta_updated	push	en	text	ETA Updated	Updated ETA: {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
771	Job Created (IN_APP - English)	created	in_app	en	text	Job Created	Your job '{{job_title}}' has been created.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
773	Technician En Route (IN_APP - English)	enroute	in_app	en	text	Technician En Route	{{technician_name}} is en route to your location.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
774	Technician Arrived (IN_APP - English)	onsite	in_app	en	text	Technician Arrived	{{technician_name}} has arrived.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
775	Job Completed (IN_APP - English)	completed	in_app	en	text	Job Completed	{{job_title}} has been completed.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
776	Job Cancelled (IN_APP - English)	cancelled	in_app	en	text	Job Cancelled	Your job '{{job_title}}' has been cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
777	Job Assigned (IN_APP - English)	job_assigned	in_app	en	text	Job Assigned	Your job '{{job_title}}' has been assigned to {{technician_name}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
778	New Job Assignment (IN_APP - English)	technician_job_assigned	in_app	en	text	New Job Assignment	A new job has been assigned. Open FieldOps for details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
779	Journey Started (IN_APP - English)	technician_journey_started	in_app	en	text	Journey Started	Journey started. Open FieldOps for job details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
780	Arrival Recorded (IN_APP - English)	technician_arrived_on_site	in_app	en	text	Arrival Recorded	Your arrival at the job site was recorded.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
781	Job Completed (IN_APP - English)	technician_job_completed	in_app	en	text	Job Completed	The job completion has been recorded.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
782	Job Cancelled (IN_APP - English)	technician_job_cancelled	in_app	en	text	Job Cancelled	A FieldOps job was cancelled. Open the app for details.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
783	Job Assigned (IN_APP - English)	dispatcher_job_assigned	in_app	en	text	Job Assigned	Assignment confirmed for {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
784	Technician En Route (IN_APP - English)	dispatcher_en_route	in_app	en	text	Technician En Route	{{technician_name}} is en route. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
785	Technician On Site (IN_APP - English)	dispatcher_on_site	in_app	en	text	Technician On Site	{{technician_name}} is now on site.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
786	Job Completed (IN_APP - English)	dispatcher_completed	in_app	en	text	Job Completed	{{job_title}} has been completed.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
787	Job Cancelled (IN_APP - English)	dispatcher_cancelled	in_app	en	text	Job Cancelled	{{job_title}} has been cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
788	Technician En Route (IN_APP - English)	technician_en_route	in_app	en	text	Technician En Route	{{technician_name}} is en route to your location.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
789	Technician Arrived (IN_APP - English)	technician_arrived	in_app	en	text	Technician Arrived	{{technician_name}} has arrived.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
790	Job Completed (IN_APP - English)	job_completed	in_app	en	text	Job Completed	{{job_title}} has been completed.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
791	Job Cancelled (IN_APP - English)	job_cancelled	in_app	en	text	Job Cancelled	Your job '{{job_title}}' has been cancelled.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
792	ETA Updated (IN_APP - English)	eta_updated	in_app	en	text	ETA Updated	Your ETA has been updated to {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
793	Trabajo creado (SMS - Spanish)	created	sms	es	text	Trabajo creado	Hola {{customer_name}}, su solicitud de servicio {{job_title}} ha sido creada.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
794	Trabajo asignado (SMS - Spanish)	assigned	sms	es	text	Trabajo asignado	Hola {{customer_name}}, {{technician_name}} ha sido asignado a {{job_title}}. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
795	Técnico en camino (SMS - Spanish)	enroute	sms	es	text	Técnico en camino	Hola {{customer_name}}, {{technician_name}} está en camino. Llegada esperada: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
796	Técnico llegó (SMS - Spanish)	onsite	sms	es	text	Técnico llegó	Hola {{customer_name}}, {{technician_name}} ha llegado para {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
797	Trabajo completado (SMS - Spanish)	completed	sms	es	text	Trabajo completado	Hola {{customer_name}}, {{job_title}} se ha completado con éxito. Gracias por elegirnos.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
798	Trabajo cancelado (SMS - Spanish)	cancelled	sms	es	text	Trabajo cancelado	Hola {{customer_name}}, su {{job_title}} ha sido cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
799	Trabajo asignado (SMS - Spanish)	job_assigned	sms	es	text	Trabajo asignado	Hola {{customer_name}}, {{technician_name}} ha sido asignado a {{job_title}}. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
800	Nueva asignación de trabajo (SMS - Spanish)	technician_job_assigned	sms	es	text	Nueva asignación de trabajo	Un nuevo trabajo de FieldOps ha sido asignado. Abra la aplicación para más detalles.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
801	Viaje comenzado (SMS - Spanish)	technician_journey_started	sms	es	text	Viaje comenzado	Su viaje ha comenzado. Abra FieldOps para ver los detalles del trabajo.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
802	Llegada registrada (SMS - Spanish)	technician_arrived_on_site	sms	es	text	Llegada registrada	Su llegada ha sido registrada. Abra FieldOps para ver los detalles del trabajo.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
803	Trabajo completado (SMS - Spanish)	technician_job_completed	sms	es	text	Trabajo completado	La finalización del trabajo ha sido registrada en FieldOps.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
804	Trabajo cancelado (SMS - Spanish)	technician_job_cancelled	sms	es	text	Trabajo cancelado	Un trabajo de FieldOps fue cancelado. Abra la aplicación para más detalles.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
805	Trabajo asignado (SMS - Spanish)	dispatcher_job_assigned	sms	es	text	Trabajo asignado	Asignación confirmada para {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
806	Técnico en camino (SMS - Spanish)	dispatcher_en_route	sms	es	text	Técnico en camino	{{technician_name}} está en camino. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
807	Técnico en el sitio (SMS - Spanish)	dispatcher_on_site	sms	es	text	Técnico en el sitio	{{technician_name}} está ahora en el sitio.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
808	Trabajo completado (SMS - Spanish)	dispatcher_completed	sms	es	text	Trabajo completado	{{job_title}} ha sido completado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
809	Trabajo cancelado (SMS - Spanish)	dispatcher_cancelled	sms	es	text	Trabajo cancelado	{{job_title}} ha sido cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
810	Técnico en camino (SMS - Spanish)	technician_en_route	sms	es	text	Técnico en camino	Hola {{customer_name}}, {{technician_name}} está en camino. Llegada esperada: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
811	Técnico llegó (SMS - Spanish)	technician_arrived	sms	es	text	Técnico llegó	Hola {{customer_name}}, {{technician_name}} ha llegado para {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
812	Trabajo completado (SMS - Spanish)	job_completed	sms	es	text	Trabajo completado	Hola {{customer_name}}, {{job_title}} se ha completado con éxito. Gracias por elegirnos.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
813	Trabajo cancelado (SMS - Spanish)	job_cancelled	sms	es	text	Trabajo cancelado	Hola {{customer_name}}, su {{job_title}} ha sido cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
814	ETA actualizado (SMS - Spanish)	eta_updated	sms	es	text	ETA actualizado	Hola {{customer_name}}, el ETA actualizado para {{technician_name}} es {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
815	Trabajo creado (EMAIL - Spanish)	created	email	es	html	Trabajo creado	<h2>Trabajo creado</h2>\n<p>Hola {{customer_name}},</p>\n<p>Su solicitud de servicio <strong>{{job_title}}</strong> ha sido creada.</p>\n<p>Gracias,<br>FieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
816	Trabajo asignado (EMAIL - Spanish)	assigned	email	es	html	Trabajo asignado	<h2>Trabajo asignado</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p><strong>{{technician_name}}</strong> ha sido asignado a su solicitud de servicio.</p>\n\n<p><strong>Trabajo:</strong> {{job_title}}</p>\n\n<p><strong>ETA:</strong> {{eta}}</p>\n\n<p>Gracias,<br>FieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
817	Técnico en camino (EMAIL - Spanish)	enroute	email	es	html	Técnico en camino	<h2>Técnico en camino</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>{{technician_name}} está viajando a su ubicación.</p>\n\n<p>ETA : <strong>{{eta}}</strong></p>\n\n<p>Gracias,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
818	Técnico llegó (EMAIL - Spanish)	onsite	email	es	html	Técnico llegó	<h2>Técnico llegó</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>{{technician_name}} ha llegado a su ubicación y comenzará a trabajar en breve.</p>\n\n<p>Trabajo : {{job_title}}</p>\n\n<p>Gracias,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
819	Trabajo completado (EMAIL - Spanish)	completed	email	es	html	Trabajo completado	<h2>Trabajo completado</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>Su solicitud de servicio se ha completado con éxito.</p>\n\n<p>Trabajo : {{job_title}}</p>\n\n<p>Gracias por elegir FieldOps.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
820	Trabajo cancelado (EMAIL - Spanish)	cancelled	email	es	html	Trabajo cancelado	<h2>Trabajo cancelado</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>Lamentablemente su solicitud de servicio ha sido cancelada.</p>\n\n<p>Trabajo : {{job_title}}</p>\n\n<p>Por favor, póngase en contacto con el soporte técnico para obtener ayuda.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
821	Trabajo asignado (EMAIL - Spanish)	job_assigned	email	es	html	Trabajo asignado	<h2>Trabajo asignado</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p><strong>{{technician_name}}</strong> ha sido asignado a su solicitud de servicio.</p>\n\n<p><strong>Trabajo:</strong> {{job_title}}</p>\n\n<p><strong>ETA:</strong> {{eta}}</p>\n\n<p>Gracias,<br>FieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
822	Nueva asignación de trabajo (EMAIL - Spanish)	technician_job_assigned	email	es	html	Nueva asignación de trabajo	<h2>Nueva asignación de trabajo</h2>\n<p>Un nuevo trabajo de FieldOps ha sido asignado a usted. Abra la aplicación del técnico para más detalles.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
823	Viaje comenzado (EMAIL - Spanish)	technician_journey_started	email	es	html	Viaje comenzado	<h2>Viaje comenzado</h2>\n<p>Su viaje ha comenzado. Abra FieldOps para ver los detalles del trabajo.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
824	Llegada registrada (EMAIL - Spanish)	technician_arrived_on_site	email	es	html	Llegada registrada	<h2>Llegada registrada</h2>\n<p>Su llegada al lugar del trabajo ha sido registrada.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
825	Trabajo completado (EMAIL - Spanish)	technician_job_completed	email	es	html	Trabajo completado	<h2>Trabajo completado</h2>\n<p>La finalización del trabajo ha sido registrada en FieldOps.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
826	Trabajo cancelado (EMAIL - Spanish)	technician_job_cancelled	email	es	html	Trabajo cancelado	<h2>Trabajo cancelado</h2>\n<p>Un trabajo de FieldOps asignado a usted fue cancelado. Abra la aplicación para más detalles.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
827	Trabajo asignado (EMAIL - Spanish)	dispatcher_job_assigned	email	es	html	Trabajo asignado	<h2>Trabajo asignado</h2>\n<p>Asignación confirmada para {{job_title}}.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
828	Técnico en camino (EMAIL - Spanish)	dispatcher_en_route	email	es	html	Técnico en camino	<h2>Técnico en camino</h2>\n<p>{{technician_name}} está en camino. ETA: {{eta}}.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
829	Técnico en el sitio (EMAIL - Spanish)	dispatcher_on_site	email	es	html	Técnico en el sitio	<h2>Técnico en el sitio</h2>\n<p>{{technician_name}} está ahora en el sitio.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
830	Trabajo completado (EMAIL - Spanish)	dispatcher_completed	email	es	html	Trabajo completado	<h2>Trabajo completado</h2>\n<p>{{job_title}} ha sido completado.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
831	Trabajo cancelado (EMAIL - Spanish)	dispatcher_cancelled	email	es	html	Trabajo cancelado	<h2>Trabajo cancelado</h2>\n<p>{{job_title}} ha sido cancelado.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
832	Técnico en camino (EMAIL - Spanish)	technician_en_route	email	es	html	Técnico en camino	<h2>Técnico en camino</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>{{technician_name}} está viajando a su ubicación.</p>\n\n<p>ETA : <strong>{{eta}}</strong></p>\n\n<p>Gracias,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
833	Técnico llegó (EMAIL - Spanish)	technician_arrived	email	es	html	Técnico llegó	<h2>Técnico llegó</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>{{technician_name}} ha llegado a su ubicación y comenzará a trabajar en breve.</p>\n\n<p>Trabajo : {{job_title}}</p>\n\n<p>Gracias,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
834	Trabajo completado (EMAIL - Spanish)	job_completed	email	es	html	Trabajo completado	<h2>Trabajo completado</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>Su solicitud de servicio se ha completado con éxito.</p>\n\n<p>Trabajo : {{job_title}}</p>\n\n<p>Gracias por elegir FieldOps.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
835	Trabajo cancelado (EMAIL - Spanish)	job_cancelled	email	es	html	Trabajo cancelado	<h2>Trabajo cancelado</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>Lamentablemente su solicitud de servicio ha sido cancelada.</p>\n\n<p>Trabajo : {{job_title}}</p>\n\n<p>Por favor, póngase en contacto con el soporte técnico para obtener ayuda.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
836	ETA actualizado (EMAIL - Spanish)	eta_updated	email	es	html	ETA actualizado	<h2>ETA actualizado</h2>\n\n<p>Hola {{customer_name}},</p>\n\n<p>El tiempo estimado de llegada de su técnico ha cambiado.</p>\n\n<p>Nuevo ETA : <strong>{{eta}}</strong></p>\n\n<p>Gracias,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
837	Trabajo creado (PUSH - Spanish)	created	push	es	text	Trabajo creado	Trabajo '{{job_title}}' creado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
838	Trabajo asignado (PUSH - Spanish)	assigned	push	es	text	Trabajo asignado	{{technician_name}} asignado. ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
839	Técnico en camino (PUSH - Spanish)	enroute	push	es	text	Técnico en camino	{{technician_name}} está en camino.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
840	Técnico llegó (PUSH - Spanish)	onsite	push	es	text	Técnico llegó	{{technician_name}} ha llegado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
841	Trabajo completado (PUSH - Spanish)	completed	push	es	text	Trabajo completado	{{job_title}} completado con éxito.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
842	Trabajo cancelado (PUSH - Spanish)	cancelled	push	es	text	Trabajo cancelado	{{job_title}} cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
843	Trabajo asignado (PUSH - Spanish)	job_assigned	push	es	text	Trabajo asignado	{{technician_name}} asignado. ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
844	Nueva asignación de trabajo (PUSH - Spanish)	technician_job_assigned	push	es	text	Nueva asignación de trabajo	Un nuevo trabajo ha sido asignado. Abra FieldOps para más detalles.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
845	Viaje comenzado (PUSH - Spanish)	technician_journey_started	push	es	text	Viaje comenzado	Su viaje ha comenzado. Abra FieldOps para ver los detalles del trabajo.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
846	Llegada registrada (PUSH - Spanish)	technician_arrived_on_site	push	es	text	Llegada registrada	Su llegada al lugar del trabajo ha sido registrada.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
847	Trabajo completado (PUSH - Spanish)	technician_job_completed	push	es	text	Trabajo completado	La finalización del trabajo ha sido registrada.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
848	Trabajo cancelado (PUSH - Spanish)	technician_job_cancelled	push	es	text	Trabajo cancelado	Un trabajo de FieldOps fue cancelado. Abra la aplicación para más detalles.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
849	Trabajo asignado (PUSH - Spanish)	dispatcher_job_assigned	push	es	text	Trabajo asignado	Asignación confirmada para {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
850	Técnico en camino (PUSH - Spanish)	dispatcher_en_route	push	es	text	Técnico en camino	{{technician_name}} está en camino.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
851	Técnico en el sitio (PUSH - Spanish)	dispatcher_on_site	push	es	text	Técnico en el sitio	{{technician_name}} está ahora en el sitio.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
852	Trabajo completado (PUSH - Spanish)	dispatcher_completed	push	es	text	Trabajo completado	{{job_title}} ha sido completado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
853	Trabajo cancelado (PUSH - Spanish)	dispatcher_cancelled	push	es	text	Trabajo cancelado	{{job_title}} ha sido cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
854	Técnico en camino (PUSH - Spanish)	technician_en_route	push	es	text	Técnico en camino	{{technician_name}} está en camino.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
855	Técnico llegó (PUSH - Spanish)	technician_arrived	push	es	text	Técnico llegó	{{technician_name}} ha llegado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
856	Trabajo completado (PUSH - Spanish)	job_completed	push	es	text	Trabajo completado	{{job_title}} completado con éxito.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
857	Trabajo cancelado (PUSH - Spanish)	job_cancelled	push	es	text	Trabajo cancelado	{{job_title}} cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
858	ETA actualizado (PUSH - Spanish)	eta_updated	push	es	text	ETA actualizado	ETA actualizado: {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
859	Trabajo creado (IN_APP - Spanish)	created	in_app	es	text	Trabajo creado	Su trabajo '{{job_title}}' ha sido creado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
860	Trabajo asignado (IN_APP - Spanish)	assigned	in_app	es	text	Trabajo asignado	Su trabajo '{{job_title}}' ha sido asignado a {{technician_name}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
861	Técnico en camino (IN_APP - Spanish)	enroute	in_app	es	text	Técnico en camino	{{technician_name}} está en camino a su ubicación.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
862	Técnico llegó (IN_APP - Spanish)	onsite	in_app	es	text	Técnico llegó	{{technician_name}} ha llegado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
863	Trabajo completado (IN_APP - Spanish)	completed	in_app	es	text	Trabajo completado	{{job_title}} se ha completado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
864	Trabajo cancelado (IN_APP - Spanish)	cancelled	in_app	es	text	Trabajo cancelado	Su trabajo '{{job_title}}' ha sido cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
865	Trabajo asignado (IN_APP - Spanish)	job_assigned	in_app	es	text	Trabajo asignado	Su trabajo '{{job_title}}' ha sido asignado a {{technician_name}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
866	Nueva asignación de trabajo (IN_APP - Spanish)	technician_job_assigned	in_app	es	text	Nueva asignación de trabajo	Un nuevo trabajo ha sido asignado. Abra FieldOps para más detalles.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
867	Viaje comenzado (IN_APP - Spanish)	technician_journey_started	in_app	es	text	Viaje comenzado	Su viaje ha comenzado. Abra FieldOps para ver los detalles del trabajo.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
868	Llegada registrada (IN_APP - Spanish)	technician_arrived_on_site	in_app	es	text	Llegada registrada	Su llegada al lugar del trabajo ha sido registrada.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
869	Trabajo completado (IN_APP - Spanish)	technician_job_completed	in_app	es	text	Trabajo completado	La finalización del trabajo ha sido registrada.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
870	Trabajo cancelado (IN_APP - Spanish)	technician_job_cancelled	in_app	es	text	Trabajo cancelado	Un trabajo de FieldOps fue cancelado. Abra la aplicación para más detalles.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
871	Trabajo asignado (IN_APP - Spanish)	dispatcher_job_assigned	in_app	es	text	Trabajo asignado	Asignación confirmada para {{job_title}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
872	Técnico en camino (IN_APP - Spanish)	dispatcher_en_route	in_app	es	text	Técnico en camino	{{technician_name}} está en camino. ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
873	Técnico en el sitio (IN_APP - Spanish)	dispatcher_on_site	in_app	es	text	Técnico en el sitio	{{technician_name}} está ahora en el sitio.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
874	Trabajo completado (IN_APP - Spanish)	dispatcher_completed	in_app	es	text	Trabajo completado	{{job_title}} ha sido completado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
875	Trabajo cancelado (IN_APP - Spanish)	dispatcher_cancelled	in_app	es	text	Trabajo cancelado	{{job_title}} ha sido cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
876	Técnico en camino (IN_APP - Spanish)	technician_en_route	in_app	es	text	Técnico en camino	{{technician_name}} está en camino a su ubicación.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
877	Técnico llegó (IN_APP - Spanish)	technician_arrived	in_app	es	text	Técnico llegó	{{technician_name}} ha llegado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
878	Trabajo completado (IN_APP - Spanish)	job_completed	in_app	es	text	Trabajo completado	{{job_title}} se ha completado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
879	Trabajo cancelado (IN_APP - Spanish)	job_cancelled	in_app	es	text	Trabajo cancelado	Su trabajo '{{job_title}}' ha sido cancelado.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
880	ETA actualizado (IN_APP - Spanish)	eta_updated	in_app	es	text	ETA actualizado	Su ETA se ha actualizado a {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
881	பணி உருவாக்கப்பட்டது (SMS - Tamil)	created	sms	ta	text	பணி உருவாக்கப்பட்டது	வணக்கம் {{customer_name}}, உங்கள் சேவை கோரிக்கை {{job_title}} உருவாக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
882	பணி நியமிக்கப்பட்டது (SMS - Tamil)	assigned	sms	ta	text	பணி நியமிக்கப்பட்டது	வணக்கம் {{customer_name}}, {{job_title}} க்கு {{technician_name}} நியமிக்கப்பட்டுள்ளார். ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
883	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (SMS - Tamil)	enroute	sms	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	வணக்கம் {{customer_name}}, {{technician_name}} வழியில் உள்ளார். எதிர்பார்க்கப்படும் வருகை: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
884	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (SMS - Tamil)	onsite	sms	ta	text	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	வணக்கம் {{customer_name}}, {{technician_name}} {{job_title}} க்காக வந்துள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
885	பணி முடிந்தது (SMS - Tamil)	completed	sms	ta	text	பணி முடிந்தது	வணக்கம் {{customer_name}}, {{job_title}} வெற்றிகரமாக முடிக்கப்பட்டுள்ளது. எங்களைத் தேர்ந்தெடுத்ததற்கு நன்றி.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
886	பணி ரத்து செய்யப்பட்டது (SMS - Tamil)	cancelled	sms	ta	text	பணி ரத்து செய்யப்பட்டது	வணக்கம் {{customer_name}}, உங்கள் {{job_title}} ரத்து செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
887	பணி நியமிக்கப்பட்டது (SMS - Tamil)	job_assigned	sms	ta	text	பணி நியமிக்கப்பட்டது	வணக்கம் {{customer_name}}, {{job_title}} க்கு {{technician_name}} நியமிக்கப்பட்டுள்ளார். ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
888	புதிய பணி நியமனம் (SMS - Tamil)	technician_job_assigned	sms	ta	text	புதிய பணி நியமனம்	புதிய FieldOps பணி நியமிக்கப்பட்டுள்ளது. விவரங்களுக்கு செயலியைத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
889	பயணம் தொடங்கியது (SMS - Tamil)	technician_journey_started	sms	ta	text	பயணம் தொடங்கியது	உங்கள் பயணம் தொடங்கிவிட்டது. பணி விவரங்களுக்கு FieldOps ஐத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
890	வருகை பதிவு செய்யப்பட்டது (SMS - Tamil)	technician_arrived_on_site	sms	ta	text	வருகை பதிவு செய்யப்பட்டது	உங்கள் வருகை பதிவு செய்யப்பட்டுள்ளது. பணி விவரங்களுக்கு FieldOps ஐத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
891	பணி முடிந்தது (SMS - Tamil)	technician_job_completed	sms	ta	text	பணி முடிந்தது	பணி முடிந்தது FieldOps இல் பதிவு செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
892	பணி ரத்து செய்யப்பட்டது (SMS - Tamil)	technician_job_cancelled	sms	ta	text	பணி ரத்து செய்யப்பட்டது	FieldOps பணி ரத்து செய்யப்பட்டது. விவரங்களுக்கு செயலியைத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
893	பணி நியமிக்கப்பட்டது (SMS - Tamil)	dispatcher_job_assigned	sms	ta	text	பணி நியமிக்கப்பட்டது	{{job_title}} க்கான நியமனம் உறுதிப்படுத்தப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
894	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (SMS - Tamil)	dispatcher_en_route	sms	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	{{technician_name}} வழியில் உள்ளார். ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
895	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார் (SMS - Tamil)	dispatcher_on_site	sms	ta	text	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார்	{{technician_name}} இப்போது தளத்தில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
896	பணி முடிந்தது (SMS - Tamil)	dispatcher_completed	sms	ta	text	பணி முடிந்தது	{{job_title}} முடிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1028	काम पूरा हुआ (PUSH - Hindi)	dispatcher_completed	push	hi	text	काम पूरा हुआ	{{job_title}} पूरा हो गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
897	பணி ரத்து செய்யப்பட்டது (SMS - Tamil)	dispatcher_cancelled	sms	ta	text	பணி ரத்து செய்யப்பட்டது	{{job_title}} ரத்து செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
898	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (SMS - Tamil)	technician_en_route	sms	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	வணக்கம் {{customer_name}}, {{technician_name}} வழியில் உள்ளார். எதிர்பார்க்கப்படும் வருகை: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
899	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (SMS - Tamil)	technician_arrived	sms	ta	text	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	வணக்கம் {{customer_name}}, {{technician_name}} {{job_title}} க்காக வந்துள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
900	பணி முடிந்தது (SMS - Tamil)	job_completed	sms	ta	text	பணி முடிந்தது	வணக்கம் {{customer_name}}, {{job_title}} வெற்றிகரமாக முடிக்கப்பட்டுள்ளது. எங்களைத் தேர்ந்தெடுத்ததற்கு நன்றி.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
901	பணி ரத்து செய்யப்பட்டது (SMS - Tamil)	job_cancelled	sms	ta	text	பணி ரத்து செய்யப்பட்டது	வணக்கம் {{customer_name}}, உங்கள் {{job_title}} ரத்து செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
902	ETA புதுப்பிக்கப்பட்டது (SMS - Tamil)	eta_updated	sms	ta	text	ETA புதுப்பிக்கப்பட்டது	வணக்கம் {{customer_name}}, {{technician_name}} க்கான புதுப்பிக்கப்பட்ட ETA {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
903	பணி உருவாக்கப்பட்டது (EMAIL - Tamil)	created	email	ta	html	பணி உருவாக்கப்பட்டது	<h2>பணி உருவாக்கப்பட்டது</h2>\n<p>வணக்கம் {{customer_name}},</p>\n<p>உங்கள் சேவை கோரிக்கை <strong>{{job_title}}</strong> உருவாக்கப்பட்டுள்ளது.</p>\n<p>நன்றி,<br>FieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
904	பணி நியமிக்கப்பட்டது (EMAIL - Tamil)	assigned	email	ta	html	பணி நியமிக்கப்பட்டது	<h2>பணி நியமிக்கப்பட்டது</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p><strong>{{technician_name}}</strong> உங்கள் சேவை கோரிக்கைக்கு நியமிக்கப்பட்டுள்ளார்.</p>\n\n<p><strong>பணி:</strong> {{job_title}}</p>\n\n<p><strong>ETA:</strong> {{eta}}</p>\n\n<p>நன்றி,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
905	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (EMAIL - Tamil)	enroute	email	ta	html	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	<h2>தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>{{technician_name}} உங்கள் இடத்திற்குப் பயணம் செய்து கொண்டிருக்கிறார்.</p>\n\n<p>ETA : <strong>{{eta}}</strong></p>\n\n<p>நன்றி,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
906	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (EMAIL - Tamil)	onsite	email	ta	html	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	<h2>தொழில்நுட்ப வல்லுநர் வந்துள்ளார்</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>{{technician_name}} உங்கள் இடத்திற்கு வந்துள்ளார், விரைவில் வேலையைத் தொடங்குவார்.</p>\n\n<p>பணி : {{job_title}}</p>\n\n<p>நன்றி,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
907	பணி முடிந்தது (EMAIL - Tamil)	completed	email	ta	html	பணி முடிந்தது	<h2>பணி முடிந்தது</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>உங்கள் சேவை கோரிக்கை வெற்றிகரமாக முடிக்கப்பட்டுள்ளது.</p>\n\n<p>பணி : {{job_title}}</p>\n\n<p>FieldOps ஐத் தேர்ந்தெடுத்ததற்கு நன்றி.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
908	பணி ரத்து செய்யப்பட்டது (EMAIL - Tamil)	cancelled	email	ta	html	பணி ரத்து செய்யப்பட்டது	<h2>பணி ரத்து செய்யப்பட்டது</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>துரதிர்ஷ்டவசமாக உங்கள் சேவை கோரிக்கை ரத்து செய்யப்பட்டுள்ளது.</p>\n\n<p>பணி : {{job_title}}</p>\n\n<p>உதவிக்கு வாடிக்கையாளர் சேவையைத் தொடர்பு கொள்ளவும்.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
909	பணி நியமிக்கப்பட்டது (EMAIL - Tamil)	job_assigned	email	ta	html	பணி நியமிக்கப்பட்டது	<h2>பணி நியமிக்கப்பட்டது</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p><strong>{{technician_name}}</strong> உங்கள் சேவை கோரிக்கைக்கு நியமிக்கப்பட்டுள்ளார்.</p>\n\n<p><strong>பணி:</strong> {{job_title}}</p>\n\n<p><strong>ETA:</strong> {{eta}}</p>\n\n<p>நன்றி,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
910	புதிய பணி நியமனம் (EMAIL - Tamil)	technician_job_assigned	email	ta	html	புதிய பணி நியமனம்	<h2>புதிய பணி நியமனம்</h2>\n<p>புதிய FieldOps பணி உங்களுக்கு நியமிக்கப்பட்டுள்ளது. விவரங்களுக்கு தொழில்நுட்ப வல்லுநர் செயலியைத் திறக்கவும்.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
911	பயணம் தொடங்கியது (EMAIL - Tamil)	technician_journey_started	email	ta	html	பயணம் தொடங்கியது	<h2>பயணம் தொடங்கியது</h2>\n<p>உங்கள் பயணம் தொடங்கிவிட்டது. பணி விவரங்களுக்கு FieldOps ஐத் திறக்கவும்.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
912	வருகை பதிவு செய்யப்பட்டது (EMAIL - Tamil)	technician_arrived_on_site	email	ta	html	வருகை பதிவு செய்யப்பட்டது	<h2>வருகை பதிவு செய்யப்பட்டது</h2>\n<p>பணி இடத்தில் உங்கள் வருகை பதிவு செய்யப்பட்டுள்ளது.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
913	பணி முடிந்தது (EMAIL - Tamil)	technician_job_completed	email	ta	html	பணி முடிந்தது	<h2>பணி முடிந்தது</h2>\n<p>பணி முடிந்தது FieldOps இல் பதிவு செய்யப்பட்டுள்ளது.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
914	பணி ரத்து செய்யப்பட்டது (EMAIL - Tamil)	technician_job_cancelled	email	ta	html	பணி ரத்து செய்யப்பட்டது	<h2>பணி ரத்து செய்யப்பட்டது</h2>\n<p>உங்களுக்கு நியமிக்கப்பட்ட FieldOps பணி ரத்து செய்யப்பட்டது. விவரங்களுக்கு செயலியைத் திறக்கவும்.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
915	பணி நியமிக்கப்பட்டது (EMAIL - Tamil)	dispatcher_job_assigned	email	ta	html	பணி நியமிக்கப்பட்டது	<h2>பணி நியமிக்கப்பட்டது</h2>\n<p>{{job_title}} க்கான நியமனம் உறுதிப்படுத்தப்பட்டுள்ளது.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
916	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (EMAIL - Tamil)	dispatcher_en_route	email	ta	html	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	<h2>தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்</h2>\n<p>{{technician_name}} வழியில் உள்ளார். ETA: {{eta}}.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
917	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார் (EMAIL - Tamil)	dispatcher_on_site	email	ta	html	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார்	<h2>தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார்</h2>\n<p>{{technician_name}} இப்போது தளத்தில் உள்ளார்.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
918	பணி முடிந்தது (EMAIL - Tamil)	dispatcher_completed	email	ta	html	பணி முடிந்தது	<h2>பணி முடிந்தது</h2>\n<p>{{job_title}} முடிக்கப்பட்டுள்ளது.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
919	பணி ரத்து செய்யப்பட்டது (EMAIL - Tamil)	dispatcher_cancelled	email	ta	html	பணி ரத்து செய்யப்பட்டது	<h2>பணி ரத்து செய்யப்பட்டது</h2>\n<p>{{job_title}} ரத்து செய்யப்பட்டுள்ளது.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
920	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (EMAIL - Tamil)	technician_en_route	email	ta	html	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	<h2>தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>{{technician_name}} உங்கள் இடத்திற்குப் பயணம் செய்து கொண்டிருக்கிறார்.</p>\n\n<p>ETA : <strong>{{eta}}</strong></p>\n\n<p>நன்றி,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
921	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (EMAIL - Tamil)	technician_arrived	email	ta	html	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	<h2>தொழில்நுட்ப வல்லுநர் வந்துள்ளார்</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>{{technician_name}} உங்கள் இடத்திற்கு வந்துள்ளார், விரைவில் வேலையைத் தொடங்குவார்.</p>\n\n<p>பணி : {{job_title}}</p>\n\n<p>நன்றி,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
922	பணி முடிந்தது (EMAIL - Tamil)	job_completed	email	ta	html	பணி முடிந்தது	<h2>பணி முடிந்தது</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>உங்கள் சேவை கோரிக்கை வெற்றிகரமாக முடிக்கப்பட்டுள்ளது.</p>\n\n<p>பணி : {{job_title}}</p>\n\n<p>FieldOps ஐத் தேர்ந்தெடுத்ததற்கு நன்றி.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
923	பணி ரத்து செய்யப்பட்டது (EMAIL - Tamil)	job_cancelled	email	ta	html	பணி ரத்து செய்யப்பட்டது	<h2>பணி ரத்து செய்யப்பட்டது</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>துரதிர்ஷ்டவசமாக உங்கள் சேவை கோரிக்கை ரத்து செய்யப்பட்டுள்ளது.</p>\n\n<p>பணி : {{job_title}}</p>\n\n<p>உதவிக்கு வாடிக்கையாளர் சேவையைத் தொடர்பு கொள்ளவும்.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
924	ETA புதுப்பிக்கப்பட்டது (EMAIL - Tamil)	eta_updated	email	ta	html	ETA புதுப்பிக்கப்பட்டது	<h2>ETA புதுப்பிக்கப்பட்டது</h2>\n\n<p>வணக்கம் {{customer_name}},</p>\n\n<p>உங்கள் தொழில்நுட்ப வல்லுநரின் மதிப்பிடப்பட்ட வருகை நேரம் மாறியுள்ளது.</p>\n\n<p>புதிய ETA : <strong>{{eta}}</strong></p>\n\n<p>நன்றி,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
925	பணி உருவாக்கப்பட்டது (PUSH - Tamil)	created	push	ta	text	பணி உருவாக்கப்பட்டது	பணி '{{job_title}}' உருவாக்கப்பட்டது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
926	பணி நியமிக்கப்பட்டது (PUSH - Tamil)	assigned	push	ta	text	பணி நியமிக்கப்பட்டது	{{technician_name}} நியமிக்கப்பட்டுள்ளார். ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
927	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (PUSH - Tamil)	enroute	push	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	{{technician_name}} வழியில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
928	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (PUSH - Tamil)	onsite	push	ta	text	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	{{technician_name}} வந்துள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
929	பணி முடிந்தது (PUSH - Tamil)	completed	push	ta	text	பணி முடிந்தது	{{job_title}} வெற்றிகரமாக முடிந்தது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
930	பணி ரத்து செய்யப்பட்டது (PUSH - Tamil)	cancelled	push	ta	text	பணி ரத்து செய்யப்பட்டது	{{job_title}} ரத்து செய்யப்பட்டது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
931	பணி நியமிக்கப்பட்டது (PUSH - Tamil)	job_assigned	push	ta	text	பணி நியமிக்கப்பட்டது	{{technician_name}} நியமிக்கப்பட்டுள்ளார். ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
932	புதிய பணி நியமனம் (PUSH - Tamil)	technician_job_assigned	push	ta	text	புதிய பணி நியமனம்	புதிய பணி நியமிக்கப்பட்டுள்ளது. விவரங்களுக்கு FieldOps ஐத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
933	பயணம் தொடங்கியது (PUSH - Tamil)	technician_journey_started	push	ta	text	பயணம் தொடங்கியது	உங்கள் பயணம் தொடங்கிவிட்டது. பணி விவரங்களுக்கு FieldOps ஐத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
934	வருகை பதிவு செய்யப்பட்டது (PUSH - Tamil)	technician_arrived_on_site	push	ta	text	வருகை பதிவு செய்யப்பட்டது	பணி இடத்தில் உங்கள் வருகை பதிவு செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
935	பணி முடிந்தது (PUSH - Tamil)	technician_job_completed	push	ta	text	பணி முடிந்தது	பணி முடிந்தது பதிவு செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
936	பணி ரத்து செய்யப்பட்டது (PUSH - Tamil)	technician_job_cancelled	push	ta	text	பணி ரத்து செய்யப்பட்டது	FieldOps பணி ரத்து செய்யப்பட்டது. விவரங்களுக்கு செயலியைத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
937	பணி நியமிக்கப்பட்டது (PUSH - Tamil)	dispatcher_job_assigned	push	ta	text	பணி நியமிக்கப்பட்டது	{{job_title}} க்கான நியமனம் உறுதிப்படுத்தப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
938	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (PUSH - Tamil)	dispatcher_en_route	push	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	{{technician_name}} வழியில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
939	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார் (PUSH - Tamil)	dispatcher_on_site	push	ta	text	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார்	{{technician_name}} இப்போது தளத்தில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
940	பணி முடிந்தது (PUSH - Tamil)	dispatcher_completed	push	ta	text	பணி முடிந்தது	{{job_title}} முடிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
941	பணி ரத்து செய்யப்பட்டது (PUSH - Tamil)	dispatcher_cancelled	push	ta	text	பணி ரத்து செய்யப்பட்டது	{{job_title}} ரத்து செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
942	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (PUSH - Tamil)	technician_en_route	push	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	{{technician_name}} வழியில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
943	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (PUSH - Tamil)	technician_arrived	push	ta	text	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	{{technician_name}} வந்துள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
944	பணி முடிந்தது (PUSH - Tamil)	job_completed	push	ta	text	பணி முடிந்தது	{{job_title}} வெற்றிகரமாக முடிந்தது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
945	பணி ரத்து செய்யப்பட்டது (PUSH - Tamil)	job_cancelled	push	ta	text	பணி ரத்து செய்யப்பட்டது	{{job_title}} ரத்து செய்யப்பட்டது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
946	ETA புதுப்பிக்கப்பட்டது (PUSH - Tamil)	eta_updated	push	ta	text	ETA புதுப்பிக்கப்பட்டது	புதுப்பிக்கப்பட்ட ETA: {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
947	பணி உருவாக்கப்பட்டது (IN_APP - Tamil)	created	in_app	ta	text	பணி உருவாக்கப்பட்டது	உங்கள் பணி '{{job_title}}' உருவாக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
948	பணி நியமிக்கப்பட்டது (IN_APP - Tamil)	assigned	in_app	ta	text	பணி நியமிக்கப்பட்டது	உங்கள் பணி '{{job_title}}' {{technician_name}} க்கு நியமிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
949	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (IN_APP - Tamil)	enroute	in_app	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	{{technician_name}} உங்கள் இடத்திற்கு வழியில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
950	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (IN_APP - Tamil)	onsite	in_app	ta	text	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	{{technician_name}} வந்துள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
951	பணி முடிந்தது (IN_APP - Tamil)	completed	in_app	ta	text	பணி முடிந்தது	{{job_title}} முடிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
952	பணி ரத்து செய்யப்பட்டது (IN_APP - Tamil)	cancelled	in_app	ta	text	பணி ரத்து செய்யப்பட்டது	உங்கள் பணி '{{job_title}}' ரத்து செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
953	பணி நியமிக்கப்பட்டது (IN_APP - Tamil)	job_assigned	in_app	ta	text	பணி நியமிக்கப்பட்டது	உங்கள் பணி '{{job_title}}' {{technician_name}} க்கு நியமிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
954	புதிய பணி நியமனம் (IN_APP - Tamil)	technician_job_assigned	in_app	ta	text	புதிய பணி நியமனம்	புதிய பணி நியமிக்கப்பட்டுள்ளது. விவரங்களுக்கு FieldOps ஐத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
955	பயணம் தொடங்கியது (IN_APP - Tamil)	technician_journey_started	in_app	ta	text	பயணம் தொடங்கியது	உங்கள் பயணம் தொடங்கிவிட்டது. பணி விவரங்களுக்கு FieldOps ஐத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
956	வருகை பதிவு செய்யப்பட்டது (IN_APP - Tamil)	technician_arrived_on_site	in_app	ta	text	வருகை பதிவு செய்யப்பட்டது	பணி இடத்தில் உங்கள் வருகை பதிவு செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
957	பணி முடிந்தது (IN_APP - Tamil)	technician_job_completed	in_app	ta	text	பணி முடிந்தது	பணி முடிந்தது பதிவு செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1029	काम रद्द किया गया (PUSH - Hindi)	dispatcher_cancelled	push	hi	text	काम रद्द किया गया	{{job_title}} रद्द कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
958	பணி ரத்து செய்யப்பட்டது (IN_APP - Tamil)	technician_job_cancelled	in_app	ta	text	பணி ரத்து செய்யப்பட்டது	FieldOps பணி ரத்து செய்யப்பட்டது. விவரங்களுக்கு செயலியைத் திறக்கவும்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
959	பணி நியமிக்கப்பட்டது (IN_APP - Tamil)	dispatcher_job_assigned	in_app	ta	text	பணி நியமிக்கப்பட்டது	{{job_title}} க்கான நியமனம் உறுதிப்படுத்தப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
960	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (IN_APP - Tamil)	dispatcher_en_route	in_app	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	{{technician_name}} வழியில் உள்ளார். ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
961	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார் (IN_APP - Tamil)	dispatcher_on_site	in_app	ta	text	தொழில்நுட்ப வல்லுநர் தளத்தில் உள்ளார்	{{technician_name}} இப்போது தளத்தில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
962	பணி முடிந்தது (IN_APP - Tamil)	dispatcher_completed	in_app	ta	text	பணி முடிந்தது	{{job_title}} முடிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
963	பணி ரத்து செய்யப்பட்டது (IN_APP - Tamil)	dispatcher_cancelled	in_app	ta	text	பணி ரத்து செய்யப்பட்டது	{{job_title}} ரத்து செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
964	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார் (IN_APP - Tamil)	technician_en_route	in_app	ta	text	தொழில்நுட்ப வல்லுநர் வழியில் உள்ளார்	{{technician_name}} உங்கள் இடத்திற்கு வழியில் உள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
965	தொழில்நுட்ப வல்லுநர் வந்துள்ளார் (IN_APP - Tamil)	technician_arrived	in_app	ta	text	தொழில்நுட்ப வல்லுநர் வந்துள்ளார்	{{technician_name}} வந்துள்ளார்.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
966	பணி முடிந்தது (IN_APP - Tamil)	job_completed	in_app	ta	text	பணி முடிந்தது	{{job_title}} முடிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
967	பணி ரத்து செய்யப்பட்டது (IN_APP - Tamil)	job_cancelled	in_app	ta	text	பணி ரத்து செய்யப்பட்டது	உங்கள் பணி '{{job_title}}' ரத்து செய்யப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
968	ETA புதுப்பிக்கப்பட்டது (IN_APP - Tamil)	eta_updated	in_app	ta	text	ETA புதுப்பிக்கப்பட்டது	உங்கள் ETA {{eta}} ஆகப் புதுப்பிக்கப்பட்டுள்ளது.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
969	काम बनाया गया (SMS - Hindi)	created	sms	hi	text	काम बनाया गया	नमस्ते {{customer_name}}, आपका सेवा अनुरोध {{job_title}} बना दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
970	काम असाइन किया गया (SMS - Hindi)	assigned	sms	hi	text	काम असाइन किया गया	नमस्ते {{customer_name}}, {{technician_name}} को {{job_title}} के लिए असाइन किया गया है। ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
971	तकनीशियन रास्ते में है (SMS - Hindi)	enroute	sms	hi	text	तकनीशियन रास्ते में है	नमस्ते {{customer_name}}, {{technician_name}} रास्ते में है। अनुमानित आगमन: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
972	तकनीशियन आ गया (SMS - Hindi)	onsite	sms	hi	text	तकनीशियन आ गया	नमस्ते {{customer_name}}, {{technician_name}} {{job_title}} के लिए आ गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
973	काम पूरा हुआ (SMS - Hindi)	completed	sms	hi	text	काम पूरा हुआ	नमस्ते {{customer_name}}, {{job_title}} सफलतापूर्वक पूरा हो गया है। हमें चुनने के लिए धन्यवाद।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
974	काम रद्द किया गया (SMS - Hindi)	cancelled	sms	hi	text	काम रद्द किया गया	नमस्ते {{customer_name}}, आपका {{job_title}} रद्द कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
975	काम असाइन किया गया (SMS - Hindi)	job_assigned	sms	hi	text	काम असाइन किया गया	नमस्ते {{customer_name}}, {{technician_name}} को {{job_title}} के लिए असाइन किया गया है। ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
976	नया काम असाइन किया गया (SMS - Hindi)	technician_job_assigned	sms	hi	text	नया काम असाइन किया गया	एक नया FieldOps काम असाइन किया गया है। विवरण के लिए ऐप खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
977	यात्रा शुरू (SMS - Hindi)	technician_journey_started	sms	hi	text	यात्रा शुरू	आपकी यात्रा शुरू हो गई है। काम के विवरण के लिए FieldOps खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
978	आगमन दर्ज किया गया (SMS - Hindi)	technician_arrived_on_site	sms	hi	text	आगमन दर्ज किया गया	आपका आगमन दर्ज कर लिया गया है। काम के विवरण के लिए FieldOps खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
979	काम पूरा हुआ (SMS - Hindi)	technician_job_completed	sms	hi	text	काम पूरा हुआ	काम का पूरा होना FieldOps में दर्ज कर लिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
980	काम रद्द किया गया (SMS - Hindi)	technician_job_cancelled	sms	hi	text	काम रद्द किया गया	एक FieldOps काम रद्द कर दिया गया था। विवरण के लिए ऐप खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
981	काम असाइन किया गया (SMS - Hindi)	dispatcher_job_assigned	sms	hi	text	काम असाइन किया गया	{{job_title}} के लिए असाइनमेंट की पुष्टि हो गई है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
982	तकनीशियन रास्ते में है (SMS - Hindi)	dispatcher_en_route	sms	hi	text	तकनीशियन रास्ते में है	{{technician_name}} रास्ते में है। ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
983	तकनीशियन साइट पर है (SMS - Hindi)	dispatcher_on_site	sms	hi	text	तकनीशियन साइट पर है	{{technician_name}} अब साइट पर है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
984	काम पूरा हुआ (SMS - Hindi)	dispatcher_completed	sms	hi	text	काम पूरा हुआ	{{job_title}} पूरा हो गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
985	काम रद्द किया गया (SMS - Hindi)	dispatcher_cancelled	sms	hi	text	काम रद्द किया गया	{{job_title}} रद्द कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
986	तकनीशियन रास्ते में है (SMS - Hindi)	technician_en_route	sms	hi	text	तकनीशियन रास्ते में है	नमस्ते {{customer_name}}, {{technician_name}} रास्ते में है। अनुमानित आगमन: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
987	तकनीशियन आ गया (SMS - Hindi)	technician_arrived	sms	hi	text	तकनीशियन आ गया	नमस्ते {{customer_name}}, {{technician_name}} {{job_title}} के लिए आ गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
988	काम पूरा हुआ (SMS - Hindi)	job_completed	sms	hi	text	काम पूरा हुआ	नमस्ते {{customer_name}}, {{job_title}} सफलतापूर्वक पूरा हो गया है। हमें चुनने के लिए धन्यवाद।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
989	काम रद्द किया गया (SMS - Hindi)	job_cancelled	sms	hi	text	काम रद्द किया गया	नमस्ते {{customer_name}}, आपका {{job_title}} रद्द कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
990	ETA अपडेट किया गया (SMS - Hindi)	eta_updated	sms	hi	text	ETA अपडेट किया गया	नमस्ते {{customer_name}}, {{technician_name}} के लिए अद्यतन ETA {{eta}} है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
991	काम बनाया गया (EMAIL - Hindi)	created	email	hi	html	काम बनाया गया	<h2>काम बनाया गया</h2>\n<p>नमस्ते {{customer_name}},</p>\n<p>आपका सेवा अनुरोध <strong>{{job_title}}</strong> बना दिया गया है।</p>\n<p>धन्यवाद,<br>FieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
992	काम असाइन किया गया (EMAIL - Hindi)	assigned	email	hi	html	काम असाइन किया गया	<h2>काम असाइन किया गया</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p><strong>{{technician_name}}</strong> को आपके सेवा अनुरोध के लिए असाइन किया गया है।</p>\n\n<p><strong>काम:</strong> {{job_title}}</p>\n\n<p><strong>ETA:</strong> {{eta}}</p>\n\n<p>धन्यवाद,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
993	तकनीशियन रास्ते में है (EMAIL - Hindi)	enroute	email	hi	html	तकनीशियन रास्ते में है	<h2>तकनीशियन रास्ते में है</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>{{technician_name}} वर्तमान में आपके स्थान की यात्रा कर रहा है।</p>\n\n<p>ETA : <strong>{{eta}}</strong></p>\n\n<p>धन्यवाद,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
994	तकनीशियन आ गया (EMAIL - Hindi)	onsite	email	hi	html	तकनीशियन आ गया	<h2>तकनीशियन आ गया</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>{{technician_name}} आपके स्थान पर आ गया है और जल्द ही काम शुरू करेगा।</p>\n\n<p>काम : {{job_title}}</p>\n\n<p>धन्यवाद,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
995	काम पूरा हुआ (EMAIL - Hindi)	completed	email	hi	html	काम पूरा हुआ	<h2>काम पूरा हुआ</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>आपका सेवा अनुरोध सफलतापूर्वक पूरा हो गया है।</p>\n\n<p>काम : {{job_title}}</p>\n\n<p>FieldOps को चुनने के लिए धन्यवाद।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
996	काम रद्द किया गया (EMAIL - Hindi)	cancelled	email	hi	html	काम रद्द किया गया	<h2>काम रद्द किया गया</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>दुर्भाग्य से आपका सेवा अनुरोध रद्द कर दिया गया है।</p>\n\n<p>काम : {{job_title}}</p>\n\n<p>सहायता के लिए कृपया समर्थन से संपर्क करें।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
997	काम असाइन किया गया (EMAIL - Hindi)	job_assigned	email	hi	html	काम असाइन किया गया	<h2>काम असाइन किया गया</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p><strong>{{technician_name}}</strong> को आपके सेवा अनुरोध के लिए असाइन किया गया है।</p>\n\n<p><strong>काम:</strong> {{job_title}}</p>\n\n<p><strong>ETA:</strong> {{eta}}</p>\n\n<p>धन्यवाद,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
998	नया काम असाइन किया गया (EMAIL - Hindi)	technician_job_assigned	email	hi	html	नया काम असाइन किया गया	<h2>नया काम असाइन किया गया</h2>\n<p>आपको एक नया FieldOps काम असाइन किया गया है। विवरण के लिए तकनीशियन ऐप खोलें।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
999	यात्रा शुरू (EMAIL - Hindi)	technician_journey_started	email	hi	html	यात्रा शुरू	<h2>यात्रा शुरू</h2>\n<p>आपकी यात्रा शुरू हो गई है। काम के विवरण के लिए FieldOps खोलें।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1000	आगमन दर्ज किया गया (EMAIL - Hindi)	technician_arrived_on_site	email	hi	html	आगमन दर्ज किया गया	<h2>आगमन दर्ज किया गया</h2>\n<p>कार्य स्थल पर आपका आगमन दर्ज कर लिया गया है।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1001	काम पूरा हुआ (EMAIL - Hindi)	technician_job_completed	email	hi	html	काम पूरा हुआ	<h2>काम पूरा हुआ</h2>\n<p>काम का पूरा होना FieldOps में दर्ज कर लिया गया है।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1002	काम रद्द किया गया (EMAIL - Hindi)	technician_job_cancelled	email	hi	html	काम रद्द किया गया	<h2>काम रद्द किया गया</h2>\n<p>आपको असाइन किया गया FieldOps काम रद्द कर दिया गया था। विवरण के लिए ऐप खोलें।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1003	काम असाइन किया गया (EMAIL - Hindi)	dispatcher_job_assigned	email	hi	html	काम असाइन किया गया	<h2>काम असाइन किया गया</h2>\n<p>{{job_title}} के लिए असाइनमेंट की पुष्टि हो गई है।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1004	तकनीशियन रास्ते में है (EMAIL - Hindi)	dispatcher_en_route	email	hi	html	तकनीशियन रास्ते में है	<h2>तकनीशियन रास्ते में है</h2>\n<p>{{technician_name}} रास्ते में है। ETA: {{eta}}.</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1005	तकनीशियन साइट पर है (EMAIL - Hindi)	dispatcher_on_site	email	hi	html	तकनीशियन साइट पर है	<h2>तकनीशियन साइट पर है</h2>\n<p>{{technician_name}} अब साइट पर है।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1006	काम पूरा हुआ (EMAIL - Hindi)	dispatcher_completed	email	hi	html	काम पूरा हुआ	<h2>काम पूरा हुआ</h2>\n<p>{{job_title}} पूरा हो गया है।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1007	काम रद्द किया गया (EMAIL - Hindi)	dispatcher_cancelled	email	hi	html	काम रद्द किया गया	<h2>काम रद्द किया गया</h2>\n<p>{{job_title}} रद्द कर दिया गया है।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1008	तकनीशियन रास्ते में है (EMAIL - Hindi)	technician_en_route	email	hi	html	तकनीशियन रास्ते में है	<h2>तकनीशियन रास्ते में है</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>{{technician_name}} वर्तमान में आपके स्थान की यात्रा कर रहा है।</p>\n\n<p>ETA : <strong>{{eta}}</strong></p>\n\n<p>धन्यवाद,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1009	तकनीशियन आ गया (EMAIL - Hindi)	technician_arrived	email	hi	html	तकनीशियन आ गया	<h2>तकनीशियन आ गया</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>{{technician_name}} आपके स्थान पर आ गया है और जल्द ही काम शुरू करेगा।</p>\n\n<p>काम : {{job_title}}</p>\n\n<p>धन्यवाद,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1010	काम पूरा हुआ (EMAIL - Hindi)	job_completed	email	hi	html	काम पूरा हुआ	<h2>काम पूरा हुआ</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>आपका सेवा अनुरोध सफलतापूर्वक पूरा हो गया है।</p>\n\n<p>काम : {{job_title}}</p>\n\n<p>FieldOps को चुनने के लिए धन्यवाद।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1011	काम रद्द किया गया (EMAIL - Hindi)	job_cancelled	email	hi	html	काम रद्द किया गया	<h2>काम रद्द किया गया</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>दुर्भाग्य से आपका सेवा अनुरोध रद्द कर दिया गया है।</p>\n\n<p>काम : {{job_title}}</p>\n\n<p>सहायता के लिए कृपया समर्थन से संपर्क करें।</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1012	ETA अपडेट किया गया (EMAIL - Hindi)	eta_updated	email	hi	html	ETA अपडेट किया गया	<h2>ETA अपडेट किया गया</h2>\n\n<p>नमस्ते {{customer_name}},</p>\n\n<p>आपके तकनीशियन का अनुमानित आगमन समय बदल गया है।</p>\n\n<p>नया ETA : <strong>{{eta}}</strong></p>\n\n<p>धन्यवाद,<br>\nFieldOps Team</p>	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1013	काम बनाया गया (PUSH - Hindi)	created	push	hi	text	काम बनाया गया	काम '{{job_title}}' बना दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1014	काम असाइन किया गया (PUSH - Hindi)	assigned	push	hi	text	काम असाइन किया गया	{{technician_name}} असाइन किया गया। ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1015	तकनीशियन रास्ते में है (PUSH - Hindi)	enroute	push	hi	text	तकनीशियन रास्ते में है	{{technician_name}} रास्ते में है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1016	तकनीशियन आ गया (PUSH - Hindi)	onsite	push	hi	text	तकनीशियन आ गया	{{technician_name}} आ गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1017	काम पूरा हुआ (PUSH - Hindi)	completed	push	hi	text	काम पूरा हुआ	{{job_title}} सफलतापूर्वक पूरा हुआ।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1018	काम रद्द किया गया (PUSH - Hindi)	cancelled	push	hi	text	काम रद्द किया गया	{{job_title}} रद्द कर दिया गया।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1019	काम असाइन किया गया (PUSH - Hindi)	job_assigned	push	hi	text	काम असाइन किया गया	{{technician_name}} असाइन किया गया। ETA {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1020	नया काम असाइन किया गया (PUSH - Hindi)	technician_job_assigned	push	hi	text	नया काम असाइन किया गया	एक नया काम असाइन किया गया है। विवरण के लिए FieldOps खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1021	यात्रा शुरू (PUSH - Hindi)	technician_journey_started	push	hi	text	यात्रा शुरू	आपकी यात्रा शुरू हो गई है। काम के विवरण के लिए FieldOps खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1022	आगमन दर्ज किया गया (PUSH - Hindi)	technician_arrived_on_site	push	hi	text	आगमन दर्ज किया गया	कार्य स्थल पर आपका आगमन दर्ज कर लिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1023	काम पूरा हुआ (PUSH - Hindi)	technician_job_completed	push	hi	text	काम पूरा हुआ	काम का पूरा होना दर्ज कर लिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1024	काम रद्द किया गया (PUSH - Hindi)	technician_job_cancelled	push	hi	text	काम रद्द किया गया	एक FieldOps काम रद्द कर दिया गया था। विवरण के लिए ऐप खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1025	काम असाइन किया गया (PUSH - Hindi)	dispatcher_job_assigned	push	hi	text	काम असाइन किया गया	{{job_title}} के लिए असाइनमेंट की पुष्टि हो गई है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1026	तकनीशियन रास्ते में है (PUSH - Hindi)	dispatcher_en_route	push	hi	text	तकनीशियन रास्ते में है	{{technician_name}} रास्ते में है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1027	तकनीशियन साइट पर है (PUSH - Hindi)	dispatcher_on_site	push	hi	text	तकनीशियन साइट पर है	{{technician_name}} अब साइट पर है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1030	तकनीशियन रास्ते में है (PUSH - Hindi)	technician_en_route	push	hi	text	तकनीशियन रास्ते में है	{{technician_name}} रास्ते में है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1031	तकनीशियन आ गया (PUSH - Hindi)	technician_arrived	push	hi	text	तकनीशियन आ गया	{{technician_name}} आ गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1032	काम पूरा हुआ (PUSH - Hindi)	job_completed	push	hi	text	काम पूरा हुआ	{{job_title}} सफलतापूर्वक पूरा हुआ।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1033	काम रद्द किया गया (PUSH - Hindi)	job_cancelled	push	hi	text	काम रद्द किया गया	{{job_title}} रद्द कर दिया गया।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1034	ETA अपडेट किया गया (PUSH - Hindi)	eta_updated	push	hi	text	ETA अपडेट किया गया	अद्यतन ETA: {{eta}}	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1035	काम बनाया गया (IN_APP - Hindi)	created	in_app	hi	text	काम बनाया गया	आपका काम '{{job_title}}' बना दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1036	काम असाइन किया गया (IN_APP - Hindi)	assigned	in_app	hi	text	काम असाइन किया गया	आपका काम '{{job_title}}' {{technician_name}} को असाइन किया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1037	तकनीशियन रास्ते में है (IN_APP - Hindi)	enroute	in_app	hi	text	तकनीशियन रास्ते में है	{{technician_name}} आपके स्थान के रास्ते में है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1038	तकनीशियन आ गया (IN_APP - Hindi)	onsite	in_app	hi	text	तकनीशियन आ गया	{{technician_name}} आ गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1039	काम पूरा हुआ (IN_APP - Hindi)	completed	in_app	hi	text	काम पूरा हुआ	{{job_title}} पूरा हो गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1040	काम रद्द किया गया (IN_APP - Hindi)	cancelled	in_app	hi	text	काम रद्द किया गया	आपका काम '{{job_title}}' रद्द कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1041	काम असाइन किया गया (IN_APP - Hindi)	job_assigned	in_app	hi	text	काम असाइन किया गया	आपका काम '{{job_title}}' {{technician_name}} को असाइन किया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1042	नया काम असाइन किया गया (IN_APP - Hindi)	technician_job_assigned	in_app	hi	text	नया काम असाइन किया गया	एक नया काम असाइन किया गया है। विवरण के लिए FieldOps खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1043	यात्रा शुरू (IN_APP - Hindi)	technician_journey_started	in_app	hi	text	यात्रा शुरू	आपकी यात्रा शुरू हो गई है। काम के विवरण के लिए FieldOps खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1044	आगमन दर्ज किया गया (IN_APP - Hindi)	technician_arrived_on_site	in_app	hi	text	आगमन दर्ज किया गया	कार्य स्थल पर आपका आगमन दर्ज कर लिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1045	काम पूरा हुआ (IN_APP - Hindi)	technician_job_completed	in_app	hi	text	काम पूरा हुआ	काम का पूरा होना दर्ज कर लिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1046	काम रद्द किया गया (IN_APP - Hindi)	technician_job_cancelled	in_app	hi	text	काम रद्द किया गया	एक FieldOps काम रद्द कर दिया गया था। विवरण के लिए ऐप खोलें।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1047	काम असाइन किया गया (IN_APP - Hindi)	dispatcher_job_assigned	in_app	hi	text	काम असाइन किया गया	{{job_title}} के लिए असाइनमेंट की पुष्टि हो गई है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1048	तकनीशियन रास्ते में है (IN_APP - Hindi)	dispatcher_en_route	in_app	hi	text	तकनीशियन रास्ते में है	{{technician_name}} रास्ते में है। ETA: {{eta}}.	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1049	तकनीशियन साइट पर है (IN_APP - Hindi)	dispatcher_on_site	in_app	hi	text	तकनीशियन साइट पर है	{{technician_name}} अब साइट पर है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1050	काम पूरा हुआ (IN_APP - Hindi)	dispatcher_completed	in_app	hi	text	काम पूरा हुआ	{{job_title}} पूरा हो गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1051	काम रद्द किया गया (IN_APP - Hindi)	dispatcher_cancelled	in_app	hi	text	काम रद्द किया गया	{{job_title}} रद्द कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1052	तकनीशियन रास्ते में है (IN_APP - Hindi)	technician_en_route	in_app	hi	text	तकनीशियन रास्ते में है	{{technician_name}} आपके स्थान के रास्ते में है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1053	तकनीशियन आ गया (IN_APP - Hindi)	technician_arrived	in_app	hi	text	तकनीशियन आ गया	{{technician_name}} आ गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1054	काम पूरा हुआ (IN_APP - Hindi)	job_completed	in_app	hi	text	काम पूरा हुआ	{{job_title}} पूरा हो गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1055	काम रद्द किया गया (IN_APP - Hindi)	job_cancelled	in_app	hi	text	काम रद्द किया गया	आपका काम '{{job_title}}' रद्द कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
1056	ETA अपडेट किया गया (IN_APP - Hindi)	eta_updated	in_app	hi	text	ETA अपडेट किया गया	आपका ETA {{eta}} में अपडेट कर दिया गया है।	1	t	2026-08-05 17:04:16.553148+05:30	[]	tenant-1	CommsAgent	f	\N	\N
\.


--
-- Data for Name: notifications; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notifications (id, tech_id, tenant_id, job_id, type, title, body, status, action_url, action_type, priority, created_at, read_at, dismissed_at, expires_at, notification_metadata) FROM stdin;
f038e5f0-d18a-49aa-be14-c3d9f7a2d45a	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	3	JOB_ASSIGNED	New Job Assigned	You have been assigned to Job #3: Networking at Kodabakkam Chennai.	READ	\N	\N	MEDIUM	2026-08-08 12:37:42.631256+05:30	2026-08-08 12:59:14.202618+05:30	\N	\N	{}
d5e166a3-c658-4069-a384-8ccaba807a22	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	5	JOB_REJECTED	Job Rejected by Technician	Tom Technician rejected Job #5: i have another job	READ	\N	\N	HIGH	2026-08-08 15:48:34.242117+05:30	2026-08-08 15:48:54.838706+05:30	\N	\N	{}
31354228-b679-42ae-9182-f8ca3785bc7d	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	2	JOB_ASSIGNED	New Job Assigned	You have been assigned to Job #2: Plumbing at Chennai Kodumbakam.	READ	\N	\N	MEDIUM	2026-08-06 10:43:47.271694+05:30	2026-08-08 15:49:51.501811+05:30	\N	\N	{}
6405af46-5c77-46fb-9329-2cb00dbe05ea	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	4	JOB_ASSIGNED	New Job Assigned	You have been assigned to Job #4: Plumbing at Kodambakkam.	READ	\N	\N	MEDIUM	2026-08-08 14:50:09.477239+05:30	2026-08-08 15:55:42.891747+05:30	\N	\N	{}
0a06eab3-95ad-4ec3-929d-05c0b9358786	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	5	JOB_ASSIGNED	New Job Assigned	You have been assigned to Job #5: Technician at Navallur.	READ	\N	\N	MEDIUM	2026-08-08 15:04:53.851849+05:30	2026-08-08 16:01:44.832161+05:30	\N	\N	{}
be5c136c-5c8a-4518-89d1-3818d6bdf97b	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	1	JOB_ASSIGNED	New Job Assigned	You have been assigned to Job #1: Ac Mechnice at Chennai .	READ	\N	\N	HIGH	2026-08-05 17:55:56.339195+05:30	2026-08-08 16:41:35.678194+05:30	\N	\N	{}
8d4a295b-6559-45e5-aa1d-623e6aed1acb	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	6	JOB_ASSIGNED	New Job Assigned	You have been assigned to Job #6: Water Technician at Kombedyu.	READ	\N	\N	MEDIUM	2026-08-10 10:14:15.534919+05:30	2026-08-10 10:22:53.784988+05:30	\N	\N	{}
\.


--
-- Data for Name: organizations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.organizations (id, name, slug, status, subscription_plan, max_users, max_technicians, max_jobs_per_month, settings, contact_email, contact_phone, address, logo_url, primary_color, created_at, updated_at, deleted_at, deleted_by, suspended_at, suspended_by, suspension_reason) FROM stdin;
tenant-1	FieldOps Core Enterprise	fieldops-core	ACTIVE	ENTERPRISE	100	500	500	{}	support@fieldops.com	\N	\N	\N	\N	2026-08-05 17:03:46.217362+05:30	2026-08-05 17:03:46.217362+05:30	\N	\N	\N	\N	\N
__platform__	Platform Administration	platform-admin	ACTIVE	ENTERPRISE	9999	9999	500	{}	superadmin@fieldops.com	\N	\N	\N	\N	2026-08-05 17:03:46.217362+05:30	2026-08-05 17:03:46.217362+05:30	\N	\N	\N	\N	\N
\.


--
-- Data for Name: override_audit_events; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.override_audit_events (id, event_type, actor_id, actor_role, actor_name, job_id, action, before_state, after_state, justification, reason, ip_address, user_agent, correlation_id, tenant_id, created_at) FROM stdin;
\.


--
-- Data for Name: preference_audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.preference_audit_logs (id, tenant_id, tech_id, updated_by, old_preferences, new_preferences, created_at) FROM stdin;
\.


--
-- Data for Name: redispatch_attempts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.redispatch_attempts (id, job_id, attempt_number, technician_id, technician_name, event_type, reason, queue_position, next_dispatch_eta, created_at) FROM stdin;
\.


--
-- Data for Name: refresh_tokens; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.refresh_tokens (id, user_id, token_hash, expires_at, revoked_at, device_info, ip_address, created_at) FROM stdin;
ee05934c-e15f-499b-9b15-37e455cb7336	87306d32-abbb-4add-94b2-675471fedcf8	1674366a2f515631283826e055aa971d9d729a009305339fa53491e57639b9be	2026-08-12 17:04:55.186042+05:30	2026-08-05 17:14:58.480216+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-05 17:04:54.917427+05:30
eb52413e-a41f-4f95-a45e-68330afa44d3	87306d32-abbb-4add-94b2-675471fedcf8	c8ca9156feee8d1cd41e164ac5b4f5718da9d9adca3abce71c877c5d00c8cc3d	2026-08-12 17:53:24.568658+05:30	2026-08-05 17:53:54.994957+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-05 17:53:24.265836+05:30
c1fd404a-1302-48ff-911f-c38a4d0296be	176973fb-629e-49f7-89f9-01807a93d3cf	1d7aa68567756a94c369439d01938a165db050b8584a8b1645e148de171ae0d0	2026-08-12 17:54:29.743764+05:30	2026-08-05 17:56:21.76475+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-05 17:54:29.510945+05:30
34e859ec-0aaa-425e-9dc8-48a1ce8a5b66	87306d32-abbb-4add-94b2-675471fedcf8	70f3c018157a7b9743ff0e1f38c121befcaf25912457d9da18a1efaaa9ba5b21	2026-08-12 17:56:53.687323+05:30	2026-08-05 17:58:53.811612+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-05 17:56:53.452573+05:30
ffb1181f-46d0-4cd5-9af8-a15647715d06	176973fb-629e-49f7-89f9-01807a93d3cf	7704519db8387ea4e4d36bc643491d70ac585e0cf81b5bbe9d94a4d403e29b82	2026-08-13 10:26:16.018215+05:30	2026-08-06 10:26:26.83076+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:26:15.748284+05:30
e79cbc1e-9ade-4b58-85eb-53831bf4dcc1	87306d32-abbb-4add-94b2-675471fedcf8	bfd8c1a75c68dfc140027a748426d611de2ba4bd548c9829977b9fae00b23e16	2026-08-13 10:27:07.699166+05:30	2026-08-06 10:40:12.382352+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:27:07.463431+05:30
d52a262a-bb51-4cd5-abf1-46a8fdc54354	176973fb-629e-49f7-89f9-01807a93d3cf	fa42465460dc7734eaf7b2f288be56e317f94d154c76187ac496ba40b5a3094d	2026-08-13 10:41:58.025901+05:30	2026-08-06 10:46:35.302477+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:41:57.779746+05:30
1ee1029e-5155-4903-a65f-e09d5bd5ce44	3147275b-8e7d-49ab-8e8e-59a206437aa3	51b6ae0f23ace2e481134aba851adb37c62362bedd37709f295b500ae370ca36	2026-08-13 10:47:00.669136+05:30	2026-08-06 10:48:38.731998+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:46:59.912688+05:30
cc7eca87-77e3-4bca-8da0-b0ac127ef4bf	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	4812621a9eb217d9cbfbe8cc21236dd898a6aba461d45c7c34a62978ad17eed5	2026-08-13 10:49:13.903825+05:30	2026-08-06 10:49:48.764167+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:49:13.664445+05:30
60a5f8a4-6ca9-4456-b129-22ddef0306d5	3147275b-8e7d-49ab-8e8e-59a206437aa3	b7ef0371aaef4affeb5a7fb6c116c8a0e664ee41c5d4d03f6c0cbdde85540e78	2026-08-13 10:50:26.429749+05:30	2026-08-06 10:56:46.377118+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:50:26.193831+05:30
505ababf-9708-4574-be4d-83cced730d43	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	cc1ffcdb464d978b315a20963cc87c249ff8100ffb5631c4ce48895efbc94812	2026-08-13 10:57:22.250115+05:30	2026-08-06 10:57:39.664626+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:57:22.006537+05:30
7601bcc3-471e-46ad-992f-35bf8b80a7cd	3147275b-8e7d-49ab-8e8e-59a206437aa3	273638f8c72aa112eeaa48e950fe2bd5c0947dfa11b89b26a927d325ca5419ff	2026-08-13 10:57:59.20775+05:30	2026-08-07 15:37:26.752178+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-06 10:57:58.970972+05:30
59e51fda-0350-4112-9fec-7e64f573f7af	3147275b-8e7d-49ab-8e8e-59a206437aa3	718fa03325eadef82dfe811868540f80a18340ba4a0e71c396b4c1e0877f879e	2026-08-14 15:37:26.755179+05:30	2026-08-07 15:37:29.887395+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-07 15:37:26.745322+05:30
1072e302-109e-4b68-b55c-91606e6fe0f1	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	9911d01db6439a073eef6d0439f70775f8a72aaaa3166245d4a8c2ea36fe52d8	2026-08-14 15:38:06.242539+05:30	2026-08-07 17:45:13.805846+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-07 15:38:05.97605+05:30
2bd8cd8d-01d9-411f-b465-609fd868e082	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	7fbeb8e3682594e1fc9318d4efdccf2ed7ca137cfdebc598382fc95fd04c0427	2026-08-14 17:45:13.819731+05:30	2026-08-07 17:46:00.926973+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-07 17:45:13.790252+05:30
4240384f-26c6-4d6a-84bc-36865afec7aa	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	48621a64f15383c842c2bd38483e441e79925cd4e66b17d4d415eae4ea19e109	2026-08-14 17:59:24.240406+05:30	2026-08-07 18:26:22.169269+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.131.0 Chrome/148.0.7778.280 Electron/42.7.0 Safari/537.36	127.0.0.1	2026-08-07 17:59:23.927089+05:30
118d3826-d9df-4438-bf9c-b1bc9dbc5410	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	165782a1cb5f4485cc9640c1cc66ac17a31c0b34ee434ec4c24519ef8ecc1f0f	2026-08-14 18:03:30.824894+05:30	2026-08-07 18:26:22.169269+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	127.0.0.1	2026-08-07 18:03:30.572585+05:30
280d7c97-f81c-4e49-9759-1716e930596a	176973fb-629e-49f7-89f9-01807a93d3cf	af989f5181edb8fc738d821802cf1e370a83cb7b9977dced24a464222634d99e	2026-08-14 18:27:05.819895+05:30	2026-08-07 18:41:23.813986+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	127.0.0.1	2026-08-07 18:27:05.569175+05:30
617cdf01-e125-4e7e-8be0-010fc8c3186e	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	53bb282178ee8fce8cf43ede49bb79cf0ce462baeec1528e989922f834e27873	2026-08-14 18:42:06.852239+05:30	2026-08-08 09:43:09.621119+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36	127.0.0.1	2026-08-07 18:42:06.571149+05:30
715ab469-d76b-4d23-8e18-503fceffbeca	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	0fab98bf7b658684819acf30551993f1c98d5d94c067f3eff35e4016d7e71102	2026-08-15 09:43:09.623119+05:30	2026-08-08 09:43:09.665926+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 09:43:09.6101+05:30
4dd31067-fb0a-4b40-9b47-3e3c1ea4928b	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	7c852a01d15b7add48f8bcae95f5ba3cfee3c7f5d13a01a4802c1dff943d2187	2026-08-15 09:43:09.668012+05:30	2026-08-08 10:13:09.037817+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 09:43:09.66229+05:30
6c15f97d-43f8-4182-8821-581fa5be9285	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	3fcb6d4f64facba421782c1e72311b1b9c27fbbe2bf450bda4a2338a6b2727c8	2026-08-15 09:42:45.745614+05:30	2026-08-08 10:13:42.384868+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.132.0 Chrome/148.0.7778.280 Electron/42.7.1 Safari/537.36	127.0.0.1	2026-08-08 09:42:45.466782+05:30
eb003360-2c8e-45a7-8166-1d866b81e934	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	bfc9ad983bd3f2c02955cd5475d40c611a762209915dfbe6a50c5bc6ef5ce580	2026-08-15 15:11:34.152536+05:30	2026-08-08 15:11:54.000199+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:11:33.89819+05:30
ba5d701f-21e8-4930-b2cf-c37e73b3a347	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	37cedf89524af7d2f47ee39e6b3d9b33a3f885f9552e5777ca7cb10d6abc91d9	2026-08-15 10:09:16.169383+05:30	2026-08-08 10:39:16.542681+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 10:09:15.893587+05:30
e5e6fcd1-f3ce-4c57-ac00-51055088d774	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	a0634e34f4829263bc78913750bcb203278cdf30685f88d0025942a084f52043	2026-08-15 15:43:42.241238+05:30	2026-08-08 15:56:01.047284+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:43:42.216568+05:30
e046ba7e-e04a-403f-b136-d4176c88c650	87306d32-abbb-4add-94b2-675471fedcf8	9885cde85267e81e1ecc9b15499748b013ad945744fccab63e465f92b14f3444	2026-08-15 15:56:18.339025+05:30	2026-08-08 16:01:27.817122+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:56:18.071603+05:30
447d78fe-edb1-47d0-8ce8-83a4c9dab4e3	87306d32-abbb-4add-94b2-675471fedcf8	9b2e73b0785221ee80ab906f1a31c60ea3fab6986b1907d09a70412b25ec2f9e	2026-08-15 16:37:16.911744+05:30	2026-08-08 16:37:42.71424+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 16:37:16.614728+05:30
f49e41dc-2215-40af-b2cb-74f47aad3cb8	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	58802537a53b7ffc84904b535e8b8d4a9013848e96f5b67dd61b81961de91e8f	2026-08-15 16:41:29.906585+05:30	2026-08-08 17:11:42.326489+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 16:41:29.670055+05:30
7cf0535f-c923-40ae-8043-b004e55364e6	87306d32-abbb-4add-94b2-675471fedcf8	353206bd118e092990dd92f662ca3fc79f82e4f7ce8a6277a5c8a428c6cfc4e9	2026-08-15 17:58:59.211863+05:30	2026-08-10 09:59:07.518187+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 17:58:58.936946+05:30
5132b4c1-206a-46a3-bcd4-04fa375356d7	87306d32-abbb-4add-94b2-675471fedcf8	615382ae7e927f770c502fcc59a6e2ae8ad5ce78a8355e073eb9c99d1e39f735	2026-08-17 09:59:07.520673+05:30	2026-08-10 10:01:10.87554+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 09:59:07.484066+05:30
d2e0a561-390d-4bb4-8979-e66690ac79ef	176973fb-629e-49f7-89f9-01807a93d3cf	905179be548729f349b8a8b7ead54d85fc9915a564e0a4692b9fff3c2daa79d6	2026-08-17 10:03:19.018485+05:30	2026-08-10 10:11:00.097743+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:03:18.778906+05:30
1642de47-d2bc-4ac5-baa3-87246bcb89da	87306d32-abbb-4add-94b2-675471fedcf8	45296d2bb68fe5a36351d2150bab9809a2d2f42d2771fc30852b93246b3d8732	2026-08-17 10:11:22.850918+05:30	2026-08-10 10:12:22.679994+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:11:22.595747+05:30
0c40eb13-6949-457e-8fa1-c1ef6dba2355	e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	4bb3b50fbd1cda8f1c73973a6be3f8c5f3ff82fd961dfb2165c4b1eb5fe57170	2026-08-17 10:12:28.248838+05:30	2026-08-10 10:14:20.952099+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:12:28.006341+05:30
47b0374e-5730-4034-b80a-68fa1862f348	87306d32-abbb-4add-94b2-675471fedcf8	0e977fd121db61a5bba65b55de3eafe1395f9d05e1f074d1b93e55780502a50f	2026-08-17 10:14:26.696251+05:30	2026-08-10 10:17:33.243806+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:14:26.457551+05:30
51f4cd20-18cf-4c7d-9f72-8f8252a117ee	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	abcbf78b8ede60b702ec58ada55a997f743178fbb7635baed03a03551278bfad	2026-08-17 10:17:35.63921+05:30	2026-08-10 10:19:26.612454+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:17:35.396842+05:30
7635d446-6e72-4947-9288-28439c815386	87306d32-abbb-4add-94b2-675471fedcf8	e633dd0c8aa59887c6618b7f0855d5fc14f2b0932c4f1205c3aca23792f854c5	2026-08-17 10:19:32.516956+05:30	2026-08-10 10:19:58.321784+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:19:32.276318+05:30
4378f420-a968-49c2-925f-d409c24ba47b	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	8aef9b37c317fb4c4adf3a41ef40b25bb8381866d8268e1e46d84a5ba37a2b2f	2026-08-17 10:20:02.639993+05:30	2026-08-10 10:20:25.83978+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:20:02.401715+05:30
f4ef4cb7-a744-40da-8791-255e88984d33	87306d32-abbb-4add-94b2-675471fedcf8	a9c048c68af75ee6045f0b27e25dc4bfd9016557c858daa10a146c8fee4fc779	2026-08-17 10:20:30.322171+05:30	2026-08-10 10:21:11.925673+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:20:30.077321+05:30
ecf7f914-6620-4da1-80d8-45c93070b51f	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	79beeb01ad5a46cf4e9c2cf007f589fdb70e354db85c736df5db4355055e217a	2026-08-17 10:21:15.738422+05:30	2026-08-10 10:21:39.04491+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:21:15.498402+05:30
5b9f5386-92ce-4b3d-8a25-147e2d42ec1c	87306d32-abbb-4add-94b2-675471fedcf8	08e4dfcf367597508cf1f399859b3512eeea997c2ab798a86be460d6fc153686	2026-08-17 10:21:49.911304+05:30	2026-08-10 10:22:41.75546+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:21:49.670338+05:30
05061f54-910e-4597-a2cf-dccadbd29c74	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	e99d8218d4c03ab947f2574766374e0162dbe1bc06d018f037f43586d2b515bf	2026-08-17 10:22:47.548407+05:30	2026-08-10 12:35:41.464573+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:22:47.310592+05:30
37447c48-e989-491d-a45b-06b8647e207b	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	fd5f274802ea579721db923f3146ed80ac5af0ad01104bc1fdda5d7df01efb9a	2026-08-17 12:35:41.471574+05:30	2026-08-10 14:46:08.260317+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 12:35:41.442275+05:30
1d3aae97-551a-4caf-9728-81b5df521c63	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	ac6764fe9b1a73a91a1325a1e5ce3fb20a86dd5e21c541e4ee94daa8599eb738	2026-08-17 14:46:08.270886+05:30	2026-08-10 15:14:33.439998+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 14:46:08.24778+05:30
97ca6bd3-cb7e-4f76-a254-29230d4851b9	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	6ebe530be577db4e82c64457f96c5a2e4486f0f6e83fccb2c21cc59cfc7872b9	2026-08-17 15:14:38.093846+05:30	2026-08-10 15:14:42.170215+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 15:14:37.855805+05:30
2110b231-4c6c-40cf-b96b-13f9579df072	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	fe844884e6eb224e81259a95ebcd2d6a132b9f9df8b59c51fbfd4cdd1c6cf3e5	2026-08-17 15:15:38.858873+05:30	2026-08-10 15:16:09.237087+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 15:15:38.620427+05:30
ae7046ed-8820-49a8-a433-f45b53ed9020	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	16ef43f6d81a6d5d43c0ff05320b553870dd3800ebd490f0e04d87c2f947ea3e	2026-08-17 15:16:18.452192+05:30	\N	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 15:16:18.214484+05:30
e324409a-14ce-4a32-8e7d-f6b8de4b3f64	87306d32-abbb-4add-94b2-675471fedcf8	8819281c0b3f33552a0183a45a11068763f2bcced17b34b76aaa8e1fa385cb88	2026-08-15 15:12:13.085346+05:30	2026-08-08 15:13:02.76479+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:12:12.844087+05:30
6c6e3d88-9144-4ef8-a85c-88967985d97a	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	30b0eb8713e309983c16dae05ef4c28eecfbc924d42fca26e11ee7d6aeb71aee	2026-08-15 10:13:09.039823+05:30	2026-08-08 10:43:20.78091+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 10:13:09.032467+05:30
55c4a7ca-f09f-4353-ad3f-d7eb7591f973	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	1809932681a6ae075e44c727d3f60841a377f69cfb9604a0453d9116fc21bec7	2026-08-15 16:01:39.155762+05:30	2026-08-08 16:31:42.13734+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 16:01:38.912255+05:30
05ad4674-7c69-4f06-92fc-367a8d55a008	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	c2568b6cd91c2daa8af82967ddb5528e250e331e992290517b21990a0389351b	2026-08-15 10:13:42.385867+05:30	2026-08-08 10:43:42.353182+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.132.0 Chrome/148.0.7778.280 Electron/42.7.1 Safari/537.36	127.0.0.1	2026-08-08 10:13:42.37719+05:30
59d767b3-3098-4df4-885d-b3c45bc57442	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	b8acf073c039c7ea6bfb6fd181ddf31c86d390cf1653bdb84a59a458aa652299	2026-08-15 10:43:42.354186+05:30	2026-08-08 12:12:42.3896+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.132.0 Chrome/148.0.7778.280 Electron/42.7.1 Safari/537.36	127.0.0.1	2026-08-08 10:43:42.349129+05:30
1f8e9fc7-aebd-46f8-be9e-cc24be85db95	87306d32-abbb-4add-94b2-675471fedcf8	4ddef367e4b7c853a0175c9c1a4c11a7e9763f14168f32d47293fd08fb07f36d	2026-08-15 16:40:43.021699+05:30	2026-08-08 16:41:14.146443+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 16:40:42.777935+05:30
24856b9f-ce42-473f-b2df-bd4e42453567	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	533eea9cb8b903f806ebe888eb05660c835bab50d5593f9f556406657eda3182	2026-08-15 10:43:20.788223+05:30	2026-08-08 12:12:42.423388+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 10:43:20.771935+05:30
1ff91722-a691-4316-ab6a-068fdd807545	87306d32-abbb-4add-94b2-675471fedcf8	d68ee9520253382270b9ed2b49b8ff657a0cd9b39e2e912ce3ba997d5d66d56b	2026-08-17 09:57:56.820115+05:30	2026-08-10 10:01:10.87554+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.132.0 Chrome/148.0.7778.280 Electron/42.7.1 Safari/537.36	127.0.0.1	2026-08-10 09:57:56.545038+05:30
91f982cb-2f68-4792-91ba-beb9d59e038e	87306d32-abbb-4add-94b2-675471fedcf8	12d34b2498e7ef0236beeb3000d135e837963b80f6bf95b025efeeb32b53190e	2026-08-15 12:13:10.885017+05:30	2026-08-08 12:14:24.639378+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:13:10.618656+05:30
dd1bdba2-5630-49f6-82d5-3dfe83856d13	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	48f4022cd3d53c1bb875c5ab8bd263da6247620bf078ebad795fc072d149a80c	2026-08-15 10:39:16.548684+05:30	2026-08-08 12:21:37.756944+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 10:39:16.519674+05:30
b08c5e99-6ca3-45b8-b01c-f82060c9fe9d	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	054f3dd5344e326967db513f0444f6486159428f8d86ad1f51a3fc31a61a368d	2026-08-15 12:12:42.401572+05:30	2026-08-08 12:21:37.756944+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Code/1.132.0 Chrome/148.0.7778.280 Electron/42.7.1 Safari/537.36	127.0.0.1	2026-08-08 12:12:42.378839+05:30
bb0af6af-9276-4c41-a60c-00c65437daa5	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	fa870241ac22bb06b328775edb86712ef30863ee1acb7b9e0f78d90a69104fac	2026-08-15 12:12:42.424391+05:30	2026-08-08 12:21:37.756944+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:12:42.423795+05:30
bd85bc85-7383-469b-92d1-0157c064ad7a	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	6770ed04bb968fdf97d25af9b01395c4ed7750653d0b9738716a097612c998ee	2026-08-15 12:14:48.520345+05:30	2026-08-08 12:21:37.756944+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:14:48.278276+05:30
617a58c2-1d93-4f03-b0fc-d68d758e683f	d5195840-ec9a-4f73-b8ac-c73573100aab	1330e0128b204c4a78eb424ab96fcfdb2080a73b1c87dac6bb6cf86511d81055	2026-08-17 10:02:33.426347+05:30	2026-08-10 10:02:50.545896+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 10:02:33.188655+05:30
00262e99-4048-4065-ab98-b7d37a7457d0	87306d32-abbb-4add-94b2-675471fedcf8	afd980f2f8c91c9c044281e419fc04d29708816ba6179d646bd463dd8caa27a5	2026-08-15 12:21:57.001978+05:30	2026-08-08 12:23:14.432352+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:21:56.74095+05:30
64c77040-a499-4fe6-b4ab-1d097c11ec1a	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	a314e8867647e1addaefb318d4ff9f85c6ee0f52dc7bbcda5437d6a1dc183e95	2026-08-15 12:23:45.79925+05:30	2026-08-08 12:28:12.774296+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:23:45.554742+05:30
471181bb-2b2b-44d1-aec4-8f1ae3638b5e	87306d32-abbb-4add-94b2-675471fedcf8	5558b8ba9a4bce0ba4d34117f4a8d4bc4781b4123217cec8b4b0fcf097e6130a	2026-08-15 12:28:35.862416+05:30	2026-08-08 12:29:17.627577+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:28:35.601882+05:30
86a28cf5-ba7c-40f6-a89f-9ddf5a887395	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	7077bb11bae3830a87797c131363ab1c6700ee44749ebabe0589c20819c0f7ed	2026-08-15 12:29:36.910807+05:30	2026-08-08 12:31:21.063725+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:29:36.664986+05:30
a22e204f-9720-4dac-9c19-5415137716a0	87306d32-abbb-4add-94b2-675471fedcf8	ffcd3149dac51f1ca1d090edbbdd5f9044c1a85851a554dbd6d50654a5720fa4	2026-08-15 12:31:37.839666+05:30	2026-08-08 12:32:33.984901+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:31:37.597172+05:30
d53b167b-9c7e-4d3f-a47f-29ce579d2967	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	956d2b0f4ab377fb3b920c80e0d84f1c46409ec4a34a163ba77cf83c13c09b08	2026-08-15 12:33:10.013354+05:30	2026-08-08 12:34:52.766247+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:33:09.750839+05:30
852dffce-4389-4c21-b1fe-166f6d07aaab	176973fb-629e-49f7-89f9-01807a93d3cf	290742dde27a543db7b28c5f65d00a591039039a168b7bd8b0aba81f61b6a386	2026-08-15 12:35:49.55886+05:30	2026-08-08 12:37:48.926788+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:35:49.315418+05:30
8c76a591-7e6f-4fdb-aa65-7b0f7541a521	3147275b-8e7d-49ab-8e8e-59a206437aa3	4a559c4211d1b38a74f7bbc6ba349daf29bfb06ee892686028edd08790f50882	2026-08-15 12:38:18.625383+05:30	2026-08-08 12:39:09.213346+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:38:18.392673+05:30
86e4f7fc-3da6-45bf-966f-b12ca9d2449b	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	3baf252d0aff5d13e30bf717175fca8901410f226359bd67d9a4196e7a9a9648	2026-08-15 12:39:38.353041+05:30	2026-08-08 12:52:36.900098+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:39:38.112062+05:30
8f41e349-0edc-4332-9219-58d91ce33b64	87306d32-abbb-4add-94b2-675471fedcf8	2d1f61cb67ae1822bdfe2cbebba6b906a8ce709d038b3634684ed9a560beedbb	2026-08-15 15:10:40.616727+05:30	2026-08-08 15:11:17.277992+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:10:40.372134+05:30
4d50c1f8-aaa3-408c-9b3d-fd01c5f558ed	87306d32-abbb-4add-94b2-675471fedcf8	7f7f802034636a794a3e6f02ff7e826907f157b0fbdac69ddab2ce5f899adc0a	2026-08-15 12:45:34.598367+05:30	2026-08-08 12:47:56.26954+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:45:34.331031+05:30
da50a298-4760-4e76-9fdc-bb20427d76be	87306d32-abbb-4add-94b2-675471fedcf8	8d262d418ad58a190049951afb71305eb1ea16d8e4231a543317223170be67ce	2026-08-15 12:53:19.410628+05:30	2026-08-08 12:55:16.09763+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:53:19.146152+05:30
bdf7b47c-b2d7-4ba1-bb20-982eed01b419	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	e8d615bb8c2806314f48ad506ed231b0d2bc9d06f2b61fa404901f156948e95c	2026-08-15 15:13:16.224627+05:30	2026-08-08 15:43:42.234554+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:13:15.982652+05:30
619cd378-414b-4138-b375-ddfbac630322	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	9e67701af6ae2711222e8635cb2be20023540858f5e38d3e0242dac945c89184	2026-08-15 12:55:49.731893+05:30	2026-08-08 12:56:02.23796+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:55:49.48955+05:30
fabfc61b-436e-4f37-8d68-73a86e830d4a	87306d32-abbb-4add-94b2-675471fedcf8	3aca4fa679b23c08d319102dbbe0535377f58b7a5fe62fe65aec71eb881b826e	2026-08-15 12:57:28.685468+05:30	2026-08-08 12:58:42.658342+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:57:28.445928+05:30
bad6e158-797a-4807-8a53-b3286488fa63	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	003b1a702ec4b47ff2dd49caae8ca1e03fb12aaaf22b9d381172d17f6679f3d5	2026-08-15 16:31:42.153638+05:30	2026-08-08 16:37:02.694587+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 16:31:42.120183+05:30
07cd866c-a430-4ba6-9eec-536425ae0510	87306d32-abbb-4add-94b2-675471fedcf8	b217dcc95bf079ea0bd7918a1cf10e2ede04dd44802ec6740bba648f051bc634	2026-08-15 13:22:01.237289+05:30	2026-08-08 13:23:14.148767+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 13:22:00.962144+05:30
1be80ce5-cef1-4787-a0c7-23f6206dd47a	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	9f9ad28c8afc70e9f401b8571fc7986501d83e2e50379e7576775d7912c3ed0d	2026-08-15 16:38:03.410903+05:30	2026-08-08 16:40:29.114007+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 16:38:03.170605+05:30
073551ce-7bf2-4e73-9ec6-d95cdffc738a	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	890c3f13e9ed0912ebfc080ee792769c892185c09b6bced4196972ceead629e3	2026-08-15 13:23:35.836456+05:30	2026-08-08 14:26:42.730354+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 13:23:35.590824+05:30
390ffbc7-ba74-482b-b817-76841f40ccba	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	aff69e2023c07d8cf7a6bc04eae6ef9a20354e692fa4f7de8695e26fc358b327	2026-08-15 17:11:42.330522+05:30	\N	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 17:11:42.322488+05:30
e2013620-40f7-4676-a8dd-f155cee4a9c0	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	31d4ff49949cfe0943dcf7aef77125c038b1086409fba874fa95e3f7f07f9595	2026-08-15 12:59:07.650028+05:30	2026-08-08 14:46:42.750333+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 12:59:07.402659+05:30
bd0ece42-00b5-4859-a2e2-2a591bc1fa84	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	828d1ef31253bf9aa76833eee1406a89eec00afe8a930e47c14f00a0cc6a87ae	2026-08-15 14:26:42.741188+05:30	2026-08-08 14:46:42.750333+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:26:42.702503+05:30
30506e91-4b4d-44d8-bfd1-3b743932ac4f	87306d32-abbb-4add-94b2-675471fedcf8	cac4e8e1d053aa273c46af7b89713cf6bc39083787451ea78cd4baadeae091f8	2026-08-15 14:46:58.193157+05:30	2026-08-08 14:47:41.429783+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:46:57.929142+05:30
1ff9ff41-4c63-4a05-b824-b63cd1daf807	176973fb-629e-49f7-89f9-01807a93d3cf	6945fd9877d3d7ab03aa153409832b304ec753fc75fac31cb08df410268bdb66	2026-08-15 14:48:26.823205+05:30	2026-08-08 14:50:15.322256+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:48:26.585579+05:30
e9756084-2bc0-4354-ad15-e31b4cd57049	87306d32-abbb-4add-94b2-675471fedcf8	99d38053c95ee7da4292cd4ed0d1619b15e639c6d009d0653fd9a607d5726a79	2026-08-15 14:50:33.208721+05:30	2026-08-08 14:51:37.673091+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:50:32.967239+05:30
0ed7a631-d954-45df-90be-d1a2c5ed554e	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	2bb3df0c987c07696de19450303c92daa06646e6ef5016dcea42014c95cfc4f6	2026-08-15 14:52:44.181426+05:30	2026-08-08 14:54:07.583903+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:52:43.940517+05:30
6142e66b-c266-46d9-8b26-677443147446	87306d32-abbb-4add-94b2-675471fedcf8	7f5e9b3754b72026c2bb8d850f62e1e7ac96e9fd98de6df5493fa85b6a228521	2026-08-15 14:54:30.696205+05:30	2026-08-08 14:55:53.924816+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:54:30.458678+05:30
b76d4136-0067-4e8b-970e-e439a4fcb13d	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	f89e1d96844f214b27100ea4bf565ffe70aa2871580827f34c0295ab05957d59	2026-08-15 14:56:14.589794+05:30	2026-08-08 14:57:45.455937+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:56:14.335464+05:30
2c4d6ed8-0c47-4835-81ab-cd270a1ae139	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	21d36965ca8523da5784fef298790a879a740973e0013db381ab0f272d8ac0c4	2026-08-15 14:58:07.112648+05:30	2026-08-08 14:58:11.064579+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:58:06.865656+05:30
c625f634-28b3-41c2-b2fa-feb2a774cf14	87306d32-abbb-4add-94b2-675471fedcf8	c20e55197d696610dddd618c00a3507d2268a1f18cc982f855fbbb3a3ab947a7	2026-08-15 14:58:32.476583+05:30	2026-08-08 14:59:21.499456+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:58:32.171048+05:30
5ec0a593-b157-4ce0-9405-0745b861dd3f	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	2a65ef25385efb5ea0324aaf31ab0657dcbfff715cff8c0495cf4c791ca14d4e	2026-08-15 14:59:35.961107+05:30	2026-08-08 15:01:43.619668+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 14:59:35.717586+05:30
3900dcaf-6df9-40be-81ff-6a1c68cf291b	176973fb-629e-49f7-89f9-01807a93d3cf	e6066d5d78b79f7e0db59758d84b2741e77b987c7cfe9008052d933da204bd4b	2026-08-15 15:02:18.935261+05:30	2026-08-08 15:04:58.423029+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:02:18.693904+05:30
fd7cb9ac-39e4-4efa-8515-9cc807bb943f	87306d32-abbb-4add-94b2-675471fedcf8	f08e226646bfeb29c9e385183bef1b0a19ae13c7364a2cee48a6ab6dc0c17050	2026-08-15 15:05:15.487452+05:30	2026-08-08 15:08:37.343729+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:05:15.244979+05:30
6c34a0f6-fc44-4f7b-9b40-3860df7ac917	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	c06b64d89114e87db35ef752ef36a4b18dc01b2467db0414d9fe3cb84e2f5bcc	2026-08-15 15:08:50.210016+05:30	2026-08-08 15:10:23.491884+05:30	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-08 15:08:49.942746+05:30
fd8353b1-2ff0-454c-95a7-042f261352ad	87306d32-abbb-4add-94b2-675471fedcf8	652a13ae08595294186ec66507e0514862a6d301984846b24980f1febc7e8eae	2026-08-17 17:07:00.699252+05:30	\N	Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36	127.0.0.1	2026-08-10 17:07:00.428219+05:30
\.


--
-- Data for Name: scoring_configurations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scoring_configurations (id, tenant_id, proximity_weight, skill_weight, workload_weight, updated_at) FROM stdin;
\.


--
-- Data for Name: security_audit_logs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.security_audit_logs (id, event, "timestamp", severity, user_tenant, attempted_channel, ip_address, websocket_id, action_taken, payload_tenant, target_tenant, technician_id, job_id, tenant_id) FROM stdin;
\.


--
-- Data for Name: service_requests; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.service_requests (id, request_number, customer_user_id, tenant_id, title, description, service_type, priority, preferred_visit_date, images, location, contact_number, status, linked_job_id, cancellation_reason, cancelled_at, created_at, updated_at) FROM stdin;
1	SR-20260805122556-DB6360	176973fb-629e-49f7-89f9-01807a93d3cf	tenant-1	Ac Mechnice	ac is fault to do dust 	Ac Mechnice	HIGH	2026-08-07	[]	Chennai 	84849404044	CANCELLED	1	\N	2026-08-06 10:42:07.248501+05:30	2026-08-05 17:55:56.339195+05:30	2026-08-06 10:42:07.242549+05:30
2	SR-20260806051347-C7DF1F	176973fb-629e-49f7-89f9-01807a93d3cf	tenant-1	Pipe is dameged	the pipe is dameged and water is lacking	Plumbing	MEDIUM	2026-08-07	[]	Chennai Kodumbakam	98765432109	CANCELLED	2	\N	2026-08-07 18:31:56.365425+05:30	2026-08-06 10:43:47.271694+05:30	2026-08-07 18:31:56.362777+05:30
4	SR-20260808092009-2F8DF7	176973fb-629e-49f7-89f9-01807a93d3cf	tenant-1	Water Leak in Weashing Mechine	the washing mechine have a problem	Plumbing	MEDIUM	2026-08-10	[]	Kodambakkam	9087654321	CANCELLED	4	\N	2026-08-08 15:02:32.128121+05:30	2026-08-08 14:50:09.477239+05:30	2026-08-08 15:02:32.109157+05:30
3	SR-20260808070742-95F230	176973fb-629e-49f7-89f9-01807a93d3cf	tenant-1	Networking problem	Networking problem in the wifi	Networking	MEDIUM	2026-08-08	[]	Kodabakkam Chennai	9566316840	CANCELLED	3	\N	2026-08-08 15:02:35.321997+05:30	2026-08-08 12:37:42.631256+05:30	2026-08-08 15:02:35.320673+05:30
5	SR-20260808093453-C08E69	176973fb-629e-49f7-89f9-01807a93d3cf	tenant-1	My fan is not working	the fan coil is getting heated and fan would run	Technician	MEDIUM	2026-08-19	[]	Navallur	90877654321	PENDING	5	\N	\N	2026-08-08 15:04:53.851849+05:30	2026-08-08 15:04:53.851849+05:30
6	SR-20260810044415-8E829C	e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	__platform__	Warter Leak	Water leak from the Ro purifier	Water Technician	MEDIUM	2026-08-11	[]	Kombedyu	9876543210	PENDING	6	\N	\N	2026-08-10 10:14:15.534919+05:30	2026-08-10 10:14:15.534919+05:30
\.


--
-- Data for Name: skill_taxonomy; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.skill_taxonomy (id, taxonomy_data, updated_at) FROM stdin;
\.


--
-- Data for Name: sla_escalations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sla_escalations (id, tenant_id, job_id, manager_notified_at, manager_responded_at, cto_notified_at, action_taken, status, created_at) FROM stdin;
\.


--
-- Data for Name: sms_deliveries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.sms_deliveries (id, tech_id, job_id, sms_sid, status, cost, error_message, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: technician_profiles; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.technician_profiles (id, user_id, tenant_id, full_name, profile_photo, mobile_number, date_of_birth, gender, address, city, state, pincode, emergency_contact, skills, experience, certifications, profile_completed, created_at, updated_at) FROM stdin;
8ce69d3c-ca31-417d-badb-1dfc8b523c80	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Tom Technician		9566316840	2003-06-12	Male	Chennai Kodambakkam	Chennai	Tamilnadu	700012		["Plumbing", "Network Support"]	2 years	[]	t	2026-08-07 15:40:43.728332+05:30	2026-08-08 10:39:41.803708+05:30
850bf082-87dd-497c-92f5-fcbe220b78f8	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	John Doe		9566316840	2003-06-20	Male	Thiruvika nagar	Chennai	Tamil Nadu	627719	Sanglikkalia 9876543210	["Plumbing", "Roofing & Carpentry"]	3	[]	t	2026-08-10 10:19:16.346603+05:30	2026-08-10 10:19:16.346603+05:30
\.


--
-- Data for Name: technicians; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.technicians (technician_id, tech_id, tenant_id, technician_name, technician_skill, certifications_data, technician_location, technician_status, current_jobs, max_jobs, last_ping, fcm_token, device_type, phone_number, sms_opt_out, notification_preferences, created_at, updated_at) FROM stdin;
3	tech-e8ff3055	__platform__	Aravindh	Plumbing, HVAC Repair	\N	Navallur Chennai	OFFLINE	0	5	2026-08-10 10:27:01.627566+05:30	\N	\N	\N	0	{"sms_enabled": true, "push_enabled": true, "inapp_enabled": true, "email_enabled": false}	2026-08-08 12:54:02.410403+05:30	2026-08-10 10:27:01.625678+05:30
4	eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	__platform__	John Doe	Plumbing, Roofing & Carpentry	\N	Thiruvika nagar	OFFLINE	3	5	2026-08-10 17:16:23.677748+05:30	\N	\N	9566316840	0	{"sms_enabled": true, "push_enabled": true, "inapp_enabled": true, "email_enabled": false}	2026-08-10 10:19:16.346603+05:30	2026-08-10 17:16:23.676087+05:30
1	tech-0ad0e957	tenant-1	Dharsan	Network Support, Plumbing	\N	Chennai Kodumbakam	Available	3	5	\N	\N	\N	\N	0	{"sms_enabled": true, "push_enabled": true, "inapp_enabled": true, "email_enabled": false}	2026-08-06 10:51:18.459021+05:30	2026-08-08 12:47:34.192044+05:30
2	923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tenant-1	Tom Technician	Plumbing, Network Support	\N	Chennai Kodambakkam	AVAILABLE	4	5	\N	\N	\N	9566316840	0	{"sms_enabled": true, "push_enabled": true, "inapp_enabled": true, "email_enabled": false}	2026-08-07 15:40:43.728332+05:30	2026-08-08 16:41:05.767662+05:30
\.


--
-- Data for Name: template_versions; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.template_versions (id, template_id, version_number, title_template, body_template, created_by, created_at, change_summary, is_active) FROM stdin;
\.


--
-- Data for Name: tenant_gps_configurations; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenant_gps_configurations (tenant_id, retention_days, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: tenants; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.tenants (id, name, parent_tenant_id) FROM stdin;
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.users (id, email, password_hash, first_name, last_name, role, tenant_id, phone_number, is_active, is_email_verified, failed_login_attempts, locked_until, last_login, created_at, updated_at, deleted_at, deleted_by) FROM stdin;
840483df-ac48-44d2-97dd-20e8b94972ac	admin@fieldops.com	$2b$12$pWF24gBEMvUojvu96kE.Rehp4iJMrQgpfxJeW.s8YAI1If8qJ901q	Rajesh	Admin	admin	tenant-1	\N	t	t	0	\N	\N	2026-08-05 17:03:46.217362+05:30	2026-08-05 17:03:46.217362+05:30	\N	\N
75940350-05cc-4bb8-a9d3-21d3901c92a7	elastaff@gmail.com	$2b$12$O1evBFRYcN5L1z08qVK3m.I5Fv8nat.GZTg3uCVTAvLHzsID6dOy2	Ela	Staff	admin	tenant-1	\N	t	t	0	\N	\N	2026-08-05 17:03:46.217362+05:30	2026-08-05 17:03:46.217362+05:30	\N	\N
3147275b-8e7d-49ab-8e8e-59a206437aa3	dispatcher@fieldops.com	$2b$12$SVPl2pmf/lsC.ZDlbDUZPeMrJQGu7TJvGcs74QVBztthcJnwMHW6y	David	Dispatcher	dispatcher	tenant-1	\N	t	t	0	\N	2026-08-08 12:38:18.625383+05:30	2026-08-05 17:03:46.217362+05:30	2026-08-08 12:38:18.392673+05:30	\N	\N
923fc5b3-881a-44f2-bef9-bc5b5b883dfd	tech@fieldops.com	$2b$12$nTeb4MrwDhjMpzBIEwZwOeHDuigmdBD07V.bk/SL/oqzuYxf/kA2S	Tom	Technician	technician	tenant-1	\N	t	t	0	\N	2026-08-08 16:41:29.906585+05:30	2026-08-05 17:03:46.217362+05:30	2026-08-08 16:41:29.670055+05:30	\N	\N
61fb8daa-dd90-4a62-ba3a-f99eedf7be9f	bala@gmail.com	$2b$12$5rg6dlgFCRiPSNLgN.mrt.HpD.tcGUVL2dwry679MFp/Yk/hp3Tam	Bala	S	technician	__platform__	\N	t	t	0	\N	\N	2026-08-08 18:00:24.631804+05:30	2026-08-08 18:00:24.631804+05:30	\N	\N
c4d825cd-9dbc-4625-82ed-40724bff7c6d	prabhu@gmail.com	$2b$12$WiiFDjXTbxOnqhLaMQj5EOW59OgrQqNhqxQ1t8cPe3yviU3olaiyO	Prabhu	S	technician	__platform__	\N	t	t	4	\N	\N	2026-08-10 10:00:13.652962+05:30	2026-08-10 10:02:20.982815+05:30	\N	\N
d5195840-ec9a-4f73-b8ac-c73573100aab	kevin@gmail.com	$2b$12$J6EBuMPF.c/kRS9Nq2R8QOQ1PWvk4rADf0JYe7sGr.pYOObko4VMC	Kevin	R	technician	__platform__	\N	t	t	0	\N	2026-08-10 10:02:33.426347+05:30	2026-08-08 18:01:58.25672+05:30	2026-08-10 10:02:33.188655+05:30	\N	\N
176973fb-629e-49f7-89f9-01807a93d3cf	customer@fieldops.com	$2b$12$bOQG1x8K3nH6qNDHBpxd0eFN.9fpquqgn3QA.UqbbG3Jd/3iqvqlK	Carl	Customer	customer	tenant-1	\N	t	t	0	\N	2026-08-10 10:03:19.017358+05:30	2026-08-05 17:03:46.217362+05:30	2026-08-10 10:03:18.778906+05:30	\N	\N
eb4f2b55-42e5-4720-8f35-0fb3bc79d6dd	john@gmail.com	$2b$12$zdCq/TMmPyvo.rztzmzS6OA4n5rk9DQ9X4CM0AHrNwHkOVgvzIoqu	John	Doe	technician	__platform__	\N	t	t	0	\N	2026-08-10 15:16:18.452192+05:30	2026-08-10 10:16:44.982561+05:30	2026-08-10 15:16:18.214484+05:30	\N	\N
e3dd52c2-d6f8-4294-8c56-a8da73f0e96a	yaswanth@gmail.com	$2b$12$1ssHY/R/SyNwq586a1LZWuGw9oAfe6Nu1988xgHyh2g86hWWnTIFG	Yaswanth	S	customer	__platform__	\N	t	t	0	\N	2026-08-10 10:12:28.24783+05:30	2026-08-10 10:12:14.027499+05:30	2026-08-10 10:12:28.006341+05:30	\N	\N
87306d32-abbb-4add-94b2-675471fedcf8	superhead@fieldops.com	$2b$12$V2u2uwBjVTh9NfyMeGfEheT3oGq4cjol4ubq7ZnujQQYyw68amOYq	Super	Admin	super_admin	__platform__	\N	t	t	0	\N	2026-08-10 17:07:00.698098+05:30	2026-08-05 17:03:46.217362+05:30	2026-08-10 17:07:00.428219+05:30	\N	\N
\.


--
-- Name: agent_state_records_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.agent_state_records_id_seq', 1, false);


--
-- Name: assignment_overrides_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.assignment_overrides_id_seq', 1, false);


--
-- Name: audit_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.audit_events_id_seq', 24, true);


--
-- Name: dispatcher_notifications_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.dispatcher_notifications_id_seq', 13, true);


--
-- Name: job_assignments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.job_assignments_id_seq', 1, false);


--
-- Name: job_closures_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.job_closures_id_seq', 4, true);


--
-- Name: jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.jobs_id_seq', 6, true);


--
-- Name: notification_deliveries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notification_deliveries_id_seq', 1, false);


--
-- Name: notification_templates_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notification_templates_id_seq', 1056, true);


--
-- Name: preference_audit_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.preference_audit_logs_id_seq', 1, false);


--
-- Name: redispatch_attempts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.redispatch_attempts_id_seq', 1, false);


--
-- Name: scoring_configurations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.scoring_configurations_id_seq', 1, false);


--
-- Name: service_requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.service_requests_id_seq', 6, true);


--
-- Name: sla_escalations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sla_escalations_id_seq', 1, false);


--
-- Name: sms_deliveries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.sms_deliveries_id_seq', 1, false);


--
-- Name: technicians_technician_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.technicians_technician_id_seq', 4, true);


--
-- Name: template_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.template_versions_id_seq', 704, true);


--
-- Name: agent_state_records agent_state_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_state_records
    ADD CONSTRAINT agent_state_records_pkey PRIMARY KEY (id);


--
-- Name: ai_brand_safety_rules ai_brand_safety_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_brand_safety_rules
    ADD CONSTRAINT ai_brand_safety_rules_pkey PRIMARY KEY (id);


--
-- Name: ai_guardrail_violations ai_guardrail_violations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_guardrail_violations
    ADD CONSTRAINT ai_guardrail_violations_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: assignment_overrides assignment_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assignment_overrides
    ADD CONSTRAINT assignment_overrides_pkey PRIMARY KEY (id);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);


--
-- Name: communication_channel_configurations communication_channel_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_channel_configurations
    ADD CONSTRAINT communication_channel_configurations_pkey PRIMARY KEY (id);


--
-- Name: communication_configuration_audits communication_configuration_audits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_configuration_audits
    ADD CONSTRAINT communication_configuration_audits_pkey PRIMARY KEY (id);


--
-- Name: customer_preference_audits customer_preference_audits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_preference_audits
    ADD CONSTRAINT customer_preference_audits_pkey PRIMARY KEY (id);


--
-- Name: customer_profiles_extended customer_profiles_extended_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_profiles_extended
    ADD CONSTRAINT customer_profiles_extended_pkey PRIMARY KEY (id);


--
-- Name: customer_profiles customer_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_profiles
    ADD CONSTRAINT customer_profiles_pkey PRIMARY KEY (id);


--
-- Name: dispatcher_alerts dispatcher_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispatcher_alerts
    ADD CONSTRAINT dispatcher_alerts_pkey PRIMARY KEY (id);


--
-- Name: dispatcher_notifications dispatcher_notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispatcher_notifications
    ADD CONSTRAINT dispatcher_notifications_pkey PRIMARY KEY (id);


--
-- Name: enterprise_audit_logs enterprise_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enterprise_audit_logs
    ADD CONSTRAINT enterprise_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: eta_history eta_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eta_history
    ADD CONSTRAINT eta_history_pkey PRIMARY KEY (id);


--
-- Name: gps_pings gps_pings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gps_pings
    ADD CONSTRAINT gps_pings_pkey PRIMARY KEY (id);


--
-- Name: gps_purge_audit_logs gps_purge_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gps_purge_audit_logs
    ADD CONSTRAINT gps_purge_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: gps_rejected_ping_logs gps_rejected_ping_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gps_rejected_ping_logs
    ADD CONSTRAINT gps_rejected_ping_logs_pkey PRIMARY KEY (id);


--
-- Name: job_assignments job_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_pkey PRIMARY KEY (id);


--
-- Name: job_closures job_closures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_closures
    ADD CONSTRAINT job_closures_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: notification_deliveries notification_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_deliveries
    ADD CONSTRAINT notification_deliveries_pkey PRIMARY KEY (id);


--
-- Name: notification_templates notification_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_templates
    ADD CONSTRAINT notification_templates_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: override_audit_events override_audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.override_audit_events
    ADD CONSTRAINT override_audit_events_pkey PRIMARY KEY (id);


--
-- Name: preference_audit_logs preference_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preference_audit_logs
    ADD CONSTRAINT preference_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: redispatch_attempts redispatch_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.redispatch_attempts
    ADD CONSTRAINT redispatch_attempts_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id);


--
-- Name: refresh_tokens refresh_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: scoring_configurations scoring_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scoring_configurations
    ADD CONSTRAINT scoring_configurations_pkey PRIMARY KEY (id);


--
-- Name: security_audit_logs security_audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.security_audit_logs
    ADD CONSTRAINT security_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: service_requests service_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_pkey PRIMARY KEY (id);


--
-- Name: skill_taxonomy skill_taxonomy_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.skill_taxonomy
    ADD CONSTRAINT skill_taxonomy_pkey PRIMARY KEY (id);


--
-- Name: sla_escalations sla_escalations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sla_escalations
    ADD CONSTRAINT sla_escalations_pkey PRIMARY KEY (id);


--
-- Name: sms_deliveries sms_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sms_deliveries
    ADD CONSTRAINT sms_deliveries_pkey PRIMARY KEY (id);


--
-- Name: technician_profiles technician_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technician_profiles
    ADD CONSTRAINT technician_profiles_pkey PRIMARY KEY (id);


--
-- Name: technicians technicians_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_pkey PRIMARY KEY (technician_id);


--
-- Name: template_versions template_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_versions
    ADD CONSTRAINT template_versions_pkey PRIMARY KEY (id);


--
-- Name: tenant_gps_configurations tenant_gps_configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_gps_configurations
    ADD CONSTRAINT tenant_gps_configurations_pkey PRIMARY KEY (tenant_id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: agent_state_records uq_agent_state_tenant_agent; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_state_records
    ADD CONSTRAINT uq_agent_state_tenant_agent UNIQUE (tenant_id, agent_id);


--
-- Name: ai_brand_safety_rules uq_ai_brand_safety_tenant_rule; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_brand_safety_rules
    ADD CONSTRAINT uq_ai_brand_safety_tenant_rule UNIQUE (tenant_id, rule_id);


--
-- Name: communication_channel_configurations uq_communication_channel_configuration_channel; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_channel_configurations
    ADD CONSTRAINT uq_communication_channel_configuration_channel UNIQUE (channel);


--
-- Name: customer_profiles uq_customer_profiles_tenant_customer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_profiles
    ADD CONSTRAINT uq_customer_profiles_tenant_customer UNIQUE (tenant_id, customer_id);


--
-- Name: users uq_users_email_tenant; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email_tenant UNIQUE (email, tenant_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: idx_agent_state_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_state_agent_id ON public.agent_state_records USING btree (agent_id);


--
-- Name: idx_agent_state_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_state_tenant ON public.agent_state_records USING btree (tenant_id);


--
-- Name: idx_agent_state_tenant_state; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_state_tenant_state ON public.agent_state_records USING btree (tenant_id, state);


--
-- Name: idx_ai_brand_safety_tenant_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_brand_safety_tenant_active ON public.ai_brand_safety_rules USING btree (tenant_id, active);


--
-- Name: idx_ai_brand_safety_tenant_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_brand_safety_tenant_category ON public.ai_brand_safety_rules USING btree (tenant_id, category);


--
-- Name: idx_ai_guardrail_code_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_guardrail_code_created ON public.ai_guardrail_violations USING btree (violation_code, created_at);


--
-- Name: idx_ai_guardrail_job_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_guardrail_job_created ON public.ai_guardrail_violations USING btree (job_id, created_at);


--
-- Name: idx_ai_guardrail_tenant_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_guardrail_tenant_created ON public.ai_guardrail_violations USING btree (tenant_id, created_at);


--
-- Name: idx_assignment_overrides_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assignment_overrides_job_id ON public.assignment_overrides USING btree (job_id);


--
-- Name: idx_audit_events_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_events_tech_id ON public.audit_events USING btree (tech_id);


--
-- Name: idx_cust_profile_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cust_profile_tenant ON public.customer_profiles_extended USING btree (tenant_id);


--
-- Name: idx_cust_profile_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cust_profile_user ON public.customer_profiles_extended USING btree (user_id);


--
-- Name: idx_dispatcher_notifications_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_dispatcher_notifications_tech_id ON public.dispatcher_notifications USING btree (tech_id);


--
-- Name: idx_enterprise_audit_action_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enterprise_audit_action_time ON public.enterprise_audit_logs USING btree (action, "timestamp");


--
-- Name: idx_enterprise_audit_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enterprise_audit_entity ON public.enterprise_audit_logs USING btree (entity_type, entity_id);


--
-- Name: idx_enterprise_audit_tenant_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enterprise_audit_tenant_time ON public.enterprise_audit_logs USING btree (tenant_id, "timestamp");


--
-- Name: idx_enterprise_audit_user_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_enterprise_audit_user_time ON public.enterprise_audit_logs USING btree (user_id, "timestamp");


--
-- Name: idx_notifications_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_created_at ON public.notifications USING btree (created_at);


--
-- Name: idx_notifications_tech_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_tech_status ON public.notifications USING btree (tech_id, status);


--
-- Name: idx_notifications_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notifications_type ON public.notifications USING btree (type);


--
-- Name: idx_organizations_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organizations_active ON public.organizations USING btree (status, deleted_at);


--
-- Name: idx_organizations_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organizations_status ON public.organizations USING btree (status);


--
-- Name: idx_redispatch_attempts_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_redispatch_attempts_job_id ON public.redispatch_attempts USING btree (job_id);


--
-- Name: idx_refresh_tokens_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_expires ON public.refresh_tokens USING btree (expires_at);


--
-- Name: idx_refresh_tokens_user_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_refresh_tokens_user_active ON public.refresh_tokens USING btree (user_id, revoked_at);


--
-- Name: idx_sr_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sr_customer ON public.service_requests USING btree (customer_user_id);


--
-- Name: idx_sr_linked_job; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sr_linked_job ON public.service_requests USING btree (linked_job_id);


--
-- Name: idx_sr_tenant_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sr_tenant_status ON public.service_requests USING btree (tenant_id, status);


--
-- Name: idx_tech_profile_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tech_profile_tenant ON public.technician_profiles USING btree (tenant_id);


--
-- Name: idx_tech_profile_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tech_profile_user ON public.technician_profiles USING btree (user_id);


--
-- Name: idx_template_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_template_lookup ON public.notification_templates USING btree (type, channel, locale, is_active);


--
-- Name: idx_template_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_template_version ON public.template_versions USING btree (template_id, version_number);


--
-- Name: idx_users_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_active ON public.users USING btree (is_active, deleted_at);


--
-- Name: idx_users_tenant_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_tenant_role ON public.users USING btree (tenant_id, role);


--
-- Name: ix_agent_state_records_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_state_records_id ON public.agent_state_records USING btree (id);


--
-- Name: ix_agent_state_records_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_state_records_tenant_id ON public.agent_state_records USING btree (tenant_id);


--
-- Name: ix_ai_brand_safety_rules_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_brand_safety_rules_tenant_id ON public.ai_brand_safety_rules USING btree (tenant_id);


--
-- Name: ix_ai_guardrail_violations_agent_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_agent_name ON public.ai_guardrail_violations USING btree (agent_name);


--
-- Name: ix_ai_guardrail_violations_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_category ON public.ai_guardrail_violations USING btree (category);


--
-- Name: ix_ai_guardrail_violations_channel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_channel ON public.ai_guardrail_violations USING btree (channel);


--
-- Name: ix_ai_guardrail_violations_checker_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_checker_name ON public.ai_guardrail_violations USING btree (checker_name);


--
-- Name: ix_ai_guardrail_violations_correlation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_correlation_id ON public.ai_guardrail_violations USING btree (correlation_id);


--
-- Name: ix_ai_guardrail_violations_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_created_at ON public.ai_guardrail_violations USING btree (created_at);


--
-- Name: ix_ai_guardrail_violations_fallback_triggered; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_fallback_triggered ON public.ai_guardrail_violations USING btree (fallback_triggered);


--
-- Name: ix_ai_guardrail_violations_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_job_id ON public.ai_guardrail_violations USING btree (job_id);


--
-- Name: ix_ai_guardrail_violations_notification_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_notification_type ON public.ai_guardrail_violations USING btree (notification_type);


--
-- Name: ix_ai_guardrail_violations_output_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_output_hash ON public.ai_guardrail_violations USING btree (output_hash);


--
-- Name: ix_ai_guardrail_violations_pipeline_decision; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_pipeline_decision ON public.ai_guardrail_violations USING btree (pipeline_decision);


--
-- Name: ix_ai_guardrail_violations_prompt_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_prompt_hash ON public.ai_guardrail_violations USING btree (prompt_hash);


--
-- Name: ix_ai_guardrail_violations_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_severity ON public.ai_guardrail_violations USING btree (severity);


--
-- Name: ix_ai_guardrail_violations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_tenant_id ON public.ai_guardrail_violations USING btree (tenant_id);


--
-- Name: ix_ai_guardrail_violations_violation_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ai_guardrail_violations_violation_code ON public.ai_guardrail_violations USING btree (violation_code);


--
-- Name: ix_assignment_overrides_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assignment_overrides_id ON public.assignment_overrides USING btree (id);


--
-- Name: ix_assignment_overrides_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assignment_overrides_job_id ON public.assignment_overrides USING btree (job_id);


--
-- Name: ix_assignment_overrides_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_assignment_overrides_tenant_id ON public.assignment_overrides USING btree (tenant_id);


--
-- Name: ix_audit_events_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_events_id ON public.audit_events USING btree (id);


--
-- Name: ix_audit_events_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_events_job_id ON public.audit_events USING btree (job_id);


--
-- Name: ix_audit_events_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_events_tech_id ON public.audit_events USING btree (tech_id);


--
-- Name: ix_audit_events_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_events_tenant_id ON public.audit_events USING btree (tenant_id);


--
-- Name: ix_communication_channel_configurations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_communication_channel_configurations_tenant_id ON public.communication_channel_configurations USING btree (tenant_id);


--
-- Name: ix_communication_configuration_audits_channel; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_communication_configuration_audits_channel ON public.communication_configuration_audits USING btree (channel);


--
-- Name: ix_communication_configuration_audits_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_communication_configuration_audits_tenant_id ON public.communication_configuration_audits USING btree (tenant_id);


--
-- Name: ix_customer_preference_audits_profile_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_preference_audits_profile_id ON public.customer_preference_audits USING btree (customer_profile_id);


--
-- Name: ix_customer_preference_audits_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_preference_audits_tenant_id ON public.customer_preference_audits USING btree (tenant_id);


--
-- Name: ix_customer_preference_audits_tenant_profile; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_preference_audits_tenant_profile ON public.customer_preference_audits USING btree (tenant_id, customer_profile_id);


--
-- Name: ix_customer_profiles_extended_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_profiles_extended_tenant_id ON public.customer_profiles_extended USING btree (tenant_id);


--
-- Name: ix_customer_profiles_extended_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_customer_profiles_extended_user_id ON public.customer_profiles_extended USING btree (user_id);


--
-- Name: ix_customer_profiles_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_profiles_tenant_id ON public.customer_profiles USING btree (tenant_id);


--
-- Name: ix_dispatcher_alerts_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dispatcher_alerts_job_id ON public.dispatcher_alerts USING btree (job_id);


--
-- Name: ix_dispatcher_alerts_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dispatcher_alerts_tenant_id ON public.dispatcher_alerts USING btree (tenant_id);


--
-- Name: ix_dispatcher_notifications_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dispatcher_notifications_id ON public.dispatcher_notifications USING btree (id);


--
-- Name: ix_dispatcher_notifications_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dispatcher_notifications_tech_id ON public.dispatcher_notifications USING btree (tech_id);


--
-- Name: ix_dispatcher_notifications_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dispatcher_notifications_tenant_id ON public.dispatcher_notifications USING btree (tenant_id);


--
-- Name: ix_enterprise_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_action ON public.enterprise_audit_logs USING btree (action);


--
-- Name: ix_enterprise_audit_logs_correlation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_correlation_id ON public.enterprise_audit_logs USING btree (correlation_id);


--
-- Name: ix_enterprise_audit_logs_entity_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_entity_id ON public.enterprise_audit_logs USING btree (entity_id);


--
-- Name: ix_enterprise_audit_logs_entity_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_entity_type ON public.enterprise_audit_logs USING btree (entity_type);


--
-- Name: ix_enterprise_audit_logs_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_role ON public.enterprise_audit_logs USING btree (role);


--
-- Name: ix_enterprise_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_tenant_id ON public.enterprise_audit_logs USING btree (tenant_id);


--
-- Name: ix_enterprise_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_timestamp ON public.enterprise_audit_logs USING btree ("timestamp");


--
-- Name: ix_enterprise_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enterprise_audit_logs_user_id ON public.enterprise_audit_logs USING btree (user_id);


--
-- Name: ix_eta_history_calculated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eta_history_calculated_at ON public.eta_history USING btree (calculated_at);


--
-- Name: ix_eta_history_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eta_history_job_id ON public.eta_history USING btree (job_id);


--
-- Name: ix_eta_history_source_ping_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eta_history_source_ping_id ON public.eta_history USING btree (source_ping_id);


--
-- Name: ix_eta_history_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eta_history_tenant_id ON public.eta_history USING btree (tenant_id);


--
-- Name: ix_gps_pings_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_pings_job_id ON public.gps_pings USING btree (job_id);


--
-- Name: ix_gps_pings_technician_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_pings_technician_id ON public.gps_pings USING btree (technician_id);


--
-- Name: ix_gps_pings_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_pings_tenant_id ON public.gps_pings USING btree (tenant_id);


--
-- Name: ix_gps_purge_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_purge_audit_logs_created_at ON public.gps_purge_audit_logs USING btree (created_at);


--
-- Name: ix_gps_purge_audit_logs_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_purge_audit_logs_job_id ON public.gps_purge_audit_logs USING btree (job_id);


--
-- Name: ix_gps_purge_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_purge_audit_logs_tenant_id ON public.gps_purge_audit_logs USING btree (tenant_id);


--
-- Name: ix_gps_rejected_ping_logs_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_rejected_ping_logs_job_id ON public.gps_rejected_ping_logs USING btree (job_id);


--
-- Name: ix_gps_rejected_ping_logs_technician_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_rejected_ping_logs_technician_id ON public.gps_rejected_ping_logs USING btree (technician_id);


--
-- Name: ix_gps_rejected_ping_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_rejected_ping_logs_tenant_id ON public.gps_rejected_ping_logs USING btree (tenant_id);


--
-- Name: ix_gps_rejected_ping_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gps_rejected_ping_logs_timestamp ON public.gps_rejected_ping_logs USING btree ("timestamp");


--
-- Name: ix_job_assignments_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_assignments_id ON public.job_assignments USING btree (id);


--
-- Name: ix_job_assignments_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_assignments_job_id ON public.job_assignments USING btree (job_id);


--
-- Name: ix_job_assignments_technician_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_assignments_technician_id ON public.job_assignments USING btree (technician_id);


--
-- Name: ix_job_assignments_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_assignments_tenant_id ON public.job_assignments USING btree (tenant_id);


--
-- Name: ix_job_closures_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_closures_id ON public.job_closures USING btree (id);


--
-- Name: ix_job_closures_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_closures_job_id ON public.job_closures USING btree (job_id);


--
-- Name: ix_job_closures_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_job_closures_tenant_id ON public.job_closures USING btree (tenant_id);


--
-- Name: ix_jobs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jobs_id ON public.jobs USING btree (id);


--
-- Name: ix_jobs_share_token; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_jobs_share_token ON public.jobs USING btree (share_token);


--
-- Name: ix_jobs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jobs_tenant_id ON public.jobs USING btree (tenant_id);


--
-- Name: ix_notification_deliveries_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_deliveries_id ON public.notification_deliveries USING btree (id);


--
-- Name: ix_notification_deliveries_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_deliveries_job_id ON public.notification_deliveries USING btree (job_id);


--
-- Name: ix_notification_deliveries_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_deliveries_tenant_id ON public.notification_deliveries USING btree (tenant_id);


--
-- Name: ix_notification_templates_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notification_templates_id ON public.notification_templates USING btree (id);


--
-- Name: ix_notifications_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_notifications_tenant_id ON public.notifications USING btree (tenant_id);


--
-- Name: ix_organizations_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_organizations_slug ON public.organizations USING btree (slug);


--
-- Name: ix_organizations_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_organizations_status ON public.organizations USING btree (status);


--
-- Name: ix_override_audit_events_actor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_override_audit_events_actor_id ON public.override_audit_events USING btree (actor_id);


--
-- Name: ix_override_audit_events_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_override_audit_events_job_id ON public.override_audit_events USING btree (job_id);


--
-- Name: ix_override_audit_events_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_override_audit_events_tenant_id ON public.override_audit_events USING btree (tenant_id);


--
-- Name: ix_preference_audit_logs_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_preference_audit_logs_id ON public.preference_audit_logs USING btree (id);


--
-- Name: ix_preference_audit_logs_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_preference_audit_logs_tech_id ON public.preference_audit_logs USING btree (tech_id);


--
-- Name: ix_preference_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_preference_audit_logs_tenant_id ON public.preference_audit_logs USING btree (tenant_id);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_scoring_configurations_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scoring_configurations_id ON public.scoring_configurations USING btree (id);


--
-- Name: ix_scoring_configurations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_scoring_configurations_tenant_id ON public.scoring_configurations USING btree (tenant_id);


--
-- Name: ix_security_audit_logs_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_logs_event ON public.security_audit_logs USING btree (event);


--
-- Name: ix_security_audit_logs_payload_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_logs_payload_tenant ON public.security_audit_logs USING btree (payload_tenant);


--
-- Name: ix_security_audit_logs_target_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_logs_target_tenant ON public.security_audit_logs USING btree (target_tenant);


--
-- Name: ix_security_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_logs_tenant_id ON public.security_audit_logs USING btree (tenant_id);


--
-- Name: ix_security_audit_logs_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_logs_timestamp ON public.security_audit_logs USING btree ("timestamp");


--
-- Name: ix_security_audit_logs_user_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_security_audit_logs_user_tenant ON public.security_audit_logs USING btree (user_tenant);


--
-- Name: ix_service_requests_customer_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_service_requests_customer_user_id ON public.service_requests USING btree (customer_user_id);


--
-- Name: ix_service_requests_linked_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_service_requests_linked_job_id ON public.service_requests USING btree (linked_job_id);


--
-- Name: ix_service_requests_request_number; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_service_requests_request_number ON public.service_requests USING btree (request_number);


--
-- Name: ix_service_requests_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_service_requests_tenant_id ON public.service_requests USING btree (tenant_id);


--
-- Name: ix_sla_escalations_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sla_escalations_id ON public.sla_escalations USING btree (id);


--
-- Name: ix_sla_escalations_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sla_escalations_job_id ON public.sla_escalations USING btree (job_id);


--
-- Name: ix_sla_escalations_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sla_escalations_tenant_id ON public.sla_escalations USING btree (tenant_id);


--
-- Name: ix_sms_deliveries_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sms_deliveries_id ON public.sms_deliveries USING btree (id);


--
-- Name: ix_sms_deliveries_job_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sms_deliveries_job_id ON public.sms_deliveries USING btree (job_id);


--
-- Name: ix_sms_deliveries_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sms_deliveries_tech_id ON public.sms_deliveries USING btree (tech_id);


--
-- Name: ix_technician_profiles_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technician_profiles_tenant_id ON public.technician_profiles USING btree (tenant_id);


--
-- Name: ix_technician_profiles_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_technician_profiles_user_id ON public.technician_profiles USING btree (user_id);


--
-- Name: ix_technicians_tech_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_technicians_tech_id ON public.technicians USING btree (tech_id);


--
-- Name: ix_technicians_technician_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technicians_technician_id ON public.technicians USING btree (technician_id);


--
-- Name: ix_technicians_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_technicians_tenant_id ON public.technicians USING btree (tenant_id);


--
-- Name: ix_template_versions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_template_versions_id ON public.template_versions USING btree (id);


--
-- Name: ix_template_versions_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_template_versions_template_id ON public.template_versions USING btree (template_id);


--
-- Name: ix_tenants_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenants_id ON public.tenants USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: ix_users_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_tenant_id ON public.users USING btree (tenant_id);


--
-- Name: agent_state_records agent_state_records_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_state_records
    ADD CONSTRAINT agent_state_records_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: ai_brand_safety_rules ai_brand_safety_rules_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_brand_safety_rules
    ADD CONSTRAINT ai_brand_safety_rules_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: ai_guardrail_violations ai_guardrail_violations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_guardrail_violations
    ADD CONSTRAINT ai_guardrail_violations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: assignment_overrides assignment_overrides_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assignment_overrides
    ADD CONSTRAINT assignment_overrides_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: assignment_overrides assignment_overrides_new_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assignment_overrides
    ADD CONSTRAINT assignment_overrides_new_technician_id_fkey FOREIGN KEY (new_technician_id) REFERENCES public.technicians(technician_id);


--
-- Name: assignment_overrides assignment_overrides_previous_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assignment_overrides
    ADD CONSTRAINT assignment_overrides_previous_technician_id_fkey FOREIGN KEY (previous_technician_id) REFERENCES public.technicians(technician_id);


--
-- Name: assignment_overrides assignment_overrides_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assignment_overrides
    ADD CONSTRAINT assignment_overrides_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: audit_events audit_events_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: communication_channel_configurations communication_channel_configurations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_channel_configurations
    ADD CONSTRAINT communication_channel_configurations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: communication_configuration_audits communication_configuration_audits_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.communication_configuration_audits
    ADD CONSTRAINT communication_configuration_audits_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: customer_preference_audits customer_preference_audits_customer_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_preference_audits
    ADD CONSTRAINT customer_preference_audits_customer_profile_id_fkey FOREIGN KEY (customer_profile_id) REFERENCES public.customer_profiles(id);


--
-- Name: customer_preference_audits customer_preference_audits_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_preference_audits
    ADD CONSTRAINT customer_preference_audits_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: customer_profiles_extended customer_profiles_extended_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_profiles_extended
    ADD CONSTRAINT customer_profiles_extended_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: customer_profiles_extended customer_profiles_extended_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_profiles_extended
    ADD CONSTRAINT customer_profiles_extended_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: dispatcher_alerts dispatcher_alerts_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispatcher_alerts
    ADD CONSTRAINT dispatcher_alerts_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: dispatcher_alerts dispatcher_alerts_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispatcher_alerts
    ADD CONSTRAINT dispatcher_alerts_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: dispatcher_notifications dispatcher_notifications_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dispatcher_notifications
    ADD CONSTRAINT dispatcher_notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: enterprise_audit_logs enterprise_audit_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enterprise_audit_logs
    ADD CONSTRAINT enterprise_audit_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: eta_history eta_history_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eta_history
    ADD CONSTRAINT eta_history_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: eta_history eta_history_source_ping_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eta_history
    ADD CONSTRAINT eta_history_source_ping_id_fkey FOREIGN KEY (source_ping_id) REFERENCES public.gps_pings(id);


--
-- Name: eta_history eta_history_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eta_history
    ADD CONSTRAINT eta_history_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: gps_pings gps_pings_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gps_pings
    ADD CONSTRAINT gps_pings_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.technicians(tech_id);


--
-- Name: gps_pings gps_pings_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gps_pings
    ADD CONSTRAINT gps_pings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: gps_purge_audit_logs gps_purge_audit_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gps_purge_audit_logs
    ADD CONSTRAINT gps_purge_audit_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: gps_rejected_ping_logs gps_rejected_ping_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gps_rejected_ping_logs
    ADD CONSTRAINT gps_rejected_ping_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: job_assignments job_assignments_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: job_assignments job_assignments_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_technician_id_fkey FOREIGN KEY (technician_id) REFERENCES public.technicians(technician_id);


--
-- Name: job_assignments job_assignments_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_assignments
    ADD CONSTRAINT job_assignments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: job_closures job_closures_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_closures
    ADD CONSTRAINT job_closures_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: job_closures job_closures_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.job_closures
    ADD CONSTRAINT job_closures_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: jobs jobs_assigned_technician_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_assigned_technician_id_fkey FOREIGN KEY (assigned_technician_id) REFERENCES public.technicians(technician_id);


--
-- Name: jobs jobs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: notification_deliveries notification_deliveries_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_deliveries
    ADD CONSTRAINT notification_deliveries_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: notification_deliveries notification_deliveries_tech_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_deliveries
    ADD CONSTRAINT notification_deliveries_tech_id_fkey FOREIGN KEY (tech_id) REFERENCES public.technicians(tech_id);


--
-- Name: notification_deliveries notification_deliveries_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification_deliveries
    ADD CONSTRAINT notification_deliveries_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: notifications notifications_tech_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_tech_id_fkey FOREIGN KEY (tech_id) REFERENCES public.technicians(tech_id);


--
-- Name: notifications notifications_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: override_audit_events override_audit_events_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.override_audit_events
    ADD CONSTRAINT override_audit_events_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: override_audit_events override_audit_events_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.override_audit_events
    ADD CONSTRAINT override_audit_events_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: preference_audit_logs preference_audit_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.preference_audit_logs
    ADD CONSTRAINT preference_audit_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: refresh_tokens refresh_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: scoring_configurations scoring_configurations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scoring_configurations
    ADD CONSTRAINT scoring_configurations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: security_audit_logs security_audit_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.security_audit_logs
    ADD CONSTRAINT security_audit_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: service_requests service_requests_customer_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_customer_user_id_fkey FOREIGN KEY (customer_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: service_requests service_requests_linked_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_linked_job_id_fkey FOREIGN KEY (linked_job_id) REFERENCES public.jobs(id);


--
-- Name: service_requests service_requests_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.service_requests
    ADD CONSTRAINT service_requests_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: sla_escalations sla_escalations_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sla_escalations
    ADD CONSTRAINT sla_escalations_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(id);


--
-- Name: sla_escalations sla_escalations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sla_escalations
    ADD CONSTRAINT sla_escalations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: technician_profiles technician_profiles_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technician_profiles
    ADD CONSTRAINT technician_profiles_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: technician_profiles technician_profiles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technician_profiles
    ADD CONSTRAINT technician_profiles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: technicians technicians_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.technicians
    ADD CONSTRAINT technicians_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: template_versions template_versions_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.template_versions
    ADD CONSTRAINT template_versions_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.notification_templates(id) ON DELETE CASCADE;


--
-- Name: tenant_gps_configurations tenant_gps_configurations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_gps_configurations
    ADD CONSTRAINT tenant_gps_configurations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- Name: tenants tenants_parent_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_parent_tenant_id_fkey FOREIGN KEY (parent_tenant_id) REFERENCES public.tenants(id);


--
-- Name: users users_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.organizations(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict aWzcgNGlUT3HZ9XVvfNgiHgh4jbAZ6qYzh7wl33pXUFQDKWDbW2WohaK7coHcwY

