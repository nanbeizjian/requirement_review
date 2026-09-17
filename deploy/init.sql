--
-- PostgreSQL database dump
--


-- Dumped by pg_dump version 16.15 (Debian 16.15-1.pgdg12+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_events (
    id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    actor_id character varying(128) NOT NULL,
    action character varying(128) NOT NULL,
    object_type character varying(64) NOT NULL,
    object_id character varying(128) NOT NULL,
    summary json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_chunks (
    id character varying(128) NOT NULL,
    project_id character varying(64) NOT NULL,
    document_id character varying(64) NOT NULL,
    document_version integer NOT NULL,
    locator character varying(1024) NOT NULL,
    text text NOT NULL,
    embedding json
);


--
-- Name: finding_decisions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.finding_decisions (
    id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    finding_id character varying(128) NOT NULL,
    action character varying(32) NOT NULL,
    actor_id character varying(128) NOT NULL,
    comment text NOT NULL,
    idempotency_key character varying(128) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: project_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_members (
    project_id character varying(64) NOT NULL,
    user_id character varying(128) NOT NULL,
    role character varying(32) NOT NULL
);


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id character varying(64) NOT NULL,
    name character varying(200) NOT NULL,
    data_policy character varying(32) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: report_approvals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.report_approvals (
    id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    action character varying(32) NOT NULL,
    actor_id character varying(128) NOT NULL,
    comment text NOT NULL,
    idempotency_key character varying(128) NOT NULL
);


--
-- Name: requirement_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.requirement_items (
    id character varying(128) NOT NULL,
    project_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    requirement_id character varying(32) NOT NULL,
    text text NOT NULL,
    evidence json NOT NULL
);


--
-- Name: review_findings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_findings (
    id character varying(128) NOT NULL,
    project_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    requirement_id character varying(32) NOT NULL,
    dimension character varying(32) NOT NULL,
    severity character varying(32) NOT NULL,
    payload json NOT NULL
);


--
-- Name: review_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_reports (
    id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    review_id character varying(64) NOT NULL,
    version integer NOT NULL,
    markdown text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: review_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.review_runs (
    id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    thread_id character varying(128) NOT NULL,
    document_id character varying(64),
    status character varying(32) NOT NULL,
    config_snapshot json NOT NULL,
    errors json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: source_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.source_documents (
    id character varying(64) NOT NULL,
    project_id character varying(64) NOT NULL,
    kind character varying(32) NOT NULL,
    filename character varying(512) NOT NULL,
    version integer NOT NULL,
    checksum character varying(128) NOT NULL,
    access_level character varying(32) NOT NULL,
    status character varying(32) NOT NULL
);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);


--
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


--
-- Name: finding_decisions finding_decisions_finding_id_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finding_decisions
    ADD CONSTRAINT finding_decisions_finding_id_idempotency_key_key UNIQUE (finding_id, idempotency_key);


--
-- Name: finding_decisions finding_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finding_decisions
    ADD CONSTRAINT finding_decisions_pkey PRIMARY KEY (id);


--
-- Name: project_members project_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_pkey PRIMARY KEY (project_id, user_id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: report_approvals report_approvals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_approvals
    ADD CONSTRAINT report_approvals_pkey PRIMARY KEY (id);


--
-- Name: report_approvals report_approvals_review_id_idempotency_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_approvals
    ADD CONSTRAINT report_approvals_review_id_idempotency_key_key UNIQUE (review_id, idempotency_key);


--
-- Name: requirement_items requirement_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requirement_items
    ADD CONSTRAINT requirement_items_pkey PRIMARY KEY (id);


--
-- Name: review_findings review_findings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_findings
    ADD CONSTRAINT review_findings_pkey PRIMARY KEY (id);


--
-- Name: review_reports review_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_reports
    ADD CONSTRAINT review_reports_pkey PRIMARY KEY (id);


--
-- Name: review_reports review_reports_review_id_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_reports
    ADD CONSTRAINT review_reports_review_id_version_key UNIQUE (review_id, version);


--
-- Name: review_runs review_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_runs
    ADD CONSTRAINT review_runs_pkey PRIMARY KEY (id);


--
-- Name: review_runs review_runs_thread_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_runs
    ADD CONSTRAINT review_runs_thread_id_key UNIQUE (thread_id);


--
-- Name: source_documents source_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_documents
    ADD CONSTRAINT source_documents_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_events_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_events_project_id ON public.audit_events USING btree (project_id);


--
-- Name: ix_document_chunks_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_document_chunks_project_id ON public.document_chunks USING btree (project_id);


--
-- Name: ix_finding_decisions_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_finding_decisions_project_id ON public.finding_decisions USING btree (project_id);


--
-- Name: ix_report_approvals_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_report_approvals_project_id ON public.report_approvals USING btree (project_id);


--
-- Name: ix_requirement_items_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_requirement_items_project_id ON public.requirement_items USING btree (project_id);


--
-- Name: ix_requirement_items_review_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_requirement_items_review_id ON public.requirement_items USING btree (review_id);


--
-- Name: ix_review_findings_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_findings_project_id ON public.review_findings USING btree (project_id);


--
-- Name: ix_review_findings_review_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_findings_review_id ON public.review_findings USING btree (review_id);


--
-- Name: ix_review_reports_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_reports_project_id ON public.review_reports USING btree (project_id);


--
-- Name: ix_review_reports_review_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_reports_review_id ON public.review_reports USING btree (review_id);


--
-- Name: ix_review_runs_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_review_runs_project_id ON public.review_runs USING btree (project_id);


--
-- Name: ix_source_documents_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_source_documents_project_id ON public.source_documents USING btree (project_id);


--
-- Name: audit_events audit_events_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: document_chunks document_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.source_documents(id);


--
-- Name: document_chunks document_chunks_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: finding_decisions finding_decisions_finding_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finding_decisions
    ADD CONSTRAINT finding_decisions_finding_id_fkey FOREIGN KEY (finding_id) REFERENCES public.review_findings(id);


--
-- Name: finding_decisions finding_decisions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.finding_decisions
    ADD CONSTRAINT finding_decisions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: project_members project_members_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_members
    ADD CONSTRAINT project_members_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: report_approvals report_approvals_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_approvals
    ADD CONSTRAINT report_approvals_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: report_approvals report_approvals_review_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.report_approvals
    ADD CONSTRAINT report_approvals_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.review_runs(id);


--
-- Name: requirement_items requirement_items_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requirement_items
    ADD CONSTRAINT requirement_items_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: requirement_items requirement_items_review_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.requirement_items
    ADD CONSTRAINT requirement_items_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.review_runs(id);


--
-- Name: review_findings review_findings_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_findings
    ADD CONSTRAINT review_findings_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: review_findings review_findings_review_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_findings
    ADD CONSTRAINT review_findings_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.review_runs(id);


--
-- Name: review_reports review_reports_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_reports
    ADD CONSTRAINT review_reports_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: review_reports review_reports_review_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_reports
    ADD CONSTRAINT review_reports_review_id_fkey FOREIGN KEY (review_id) REFERENCES public.review_runs(id);


--
-- Name: review_runs review_runs_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.review_runs
    ADD CONSTRAINT review_runs_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: source_documents source_documents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.source_documents
    ADD CONSTRAINT source_documents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- PostgreSQL database dump complete
--

--
-- Alembic version marker (equivalent to `alembic upgrade head`)
--
INSERT INTO public.alembic_version (version_num) VALUES ('0001');
