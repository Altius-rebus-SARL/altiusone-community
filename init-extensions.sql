-- PostgreSQL Extensions for AltiusOne
-- This script is executed when the PostgreSQL container is first initialized

-- PostGIS - Geographic Information System extension
-- Required for django.contrib.gis
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Full-text search improvements
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Cryptographic functions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Performance monitoring (optional but recommended)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Verify extensions are installed
SELECT extname, extversion FROM pg_extension ORDER BY extname;
