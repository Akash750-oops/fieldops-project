--
-- PostgreSQL database dump
--


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

COMMENT ON COLUMN public.agent_state_records.last_error IS 'Safe error summary only â€” no stack traces or secrets.';


--
-- Name: COLUMN agent_state_records.safe_metadata; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.agent_state_records.safe_metadata IS 'Safe operational metadata â€” no customer data or secrets.';


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
    id INTEGER NOT NULL,
    tech_id VARCHAR(36) NOT NULL,
    job_id VARCHAR(36) NOT NULL,
    sms_sid VARCHAR(255),
    status VARCHAR(30) NOT NULL,
    cost DOUBLE PRECISION,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),



    

    CONSTRAINT sms_deliveries_tenant_id_fkey
        FOREIGN KEY (tenant_id)
        REFERENCES public.organizations(id)
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

CREATE TABLE public.organization_onboardings (
    id VARCHAR(36) NOT NULL,
    organization_name VARCHAR(200) NOT NULL,
    admin_first_name VARCHAR(100) NOT NULL,
    admin_last_name VARCHAR(100) NOT NULL,
    admin_email VARCHAR(255) NOT NULL,
    otp_hash VARCHAR(255) NOT NULL,
    otp_expires_at TIMESTAMPTZ NOT NULL,
    otp_verified BOOLEAN NOT NULL,
    otp_verified_at TIMESTAMPTZ,
    otp_attempts INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT organization_onboardings_pkey PRIMARY KEY (id)
);
--
-- PostgreSQL database dump complete
--




