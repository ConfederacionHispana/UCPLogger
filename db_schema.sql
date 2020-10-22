/*
 Navicat Premium Data Transfer

 Source Server         : postgres-local
 Source Server Type    : PostgreSQL
 Source Server Version : 100014
 Source Host           : localhost:5432
 Source Catalog        : rcgcdb
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 100014
 File Encoding         : 65001

 Date: 22/10/2020 03:06:47
*/


-- ----------------------------
-- Table structure for wikis
-- ----------------------------
DROP TABLE IF EXISTS "public"."wikis";
CREATE TABLE "public"."wikis" (
  "guild" text COLLATE "pg_catalog"."default" NOT NULL,
  "configid" int4 NOT NULL,
  "webhook" text COLLATE "pg_catalog"."default" NOT NULL,
  "wiki" text COLLATE "pg_catalog"."default" NOT NULL,
  "lang" text COLLATE "pg_catalog"."default" NOT NULL,
  "display" int4 NOT NULL,
  "wikiid" int4,
  "rcid" int4,
  "postid" text COLLATE "pg_catalog"."default"
)
;

-- ----------------------------
-- Indexes structure for table wikis
-- ----------------------------
CREATE INDEX "idx_rcgcdw_config" ON "public"."wikis" USING btree (
  "guild" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST,
  "configid" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_rcgcdw_webhook" ON "public"."wikis" USING btree (
  "webhook" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_rcgcdw_wiki" ON "public"."wikis" USING btree (
  "wiki" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table wikis
-- ----------------------------
ALTER TABLE "public"."wikis" ADD CONSTRAINT "wikis_pkey" PRIMARY KEY ("configid");
