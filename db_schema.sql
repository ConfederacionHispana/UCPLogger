-- Table: public.wikis

-- DROP TABLE public.wikis;

CREATE TABLE public.wikis
(
    id SERIAL,
    wiki_url text COLLATE pg_catalog."default" NOT NULL,
    webhook text COLLATE pg_catalog."default" NOT NULL,
    lang text COLLATE pg_catalog."default" NOT NULL,
    display integer NOT NULL,
    wiki_id integer,
    rcid integer,
    postid text COLLATE pg_catalog."default",
    CONSTRAINT wikis_pkey PRIMARY KEY (id)
)
WITH (
    OIDS = FALSE
)
TABLESPACE pg_default;

-- Index: idx_webhooks

-- DROP INDEX public.idx_webhooks;

CREATE INDEX idx_webhooks
    ON public.wikis USING btree
    (webhook COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_wikis

-- DROP INDEX public.idx_wikis;

CREATE INDEX idx_wikis
    ON public.wikis USING btree
    (wiki_url COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;