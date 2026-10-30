-- Run AFTER the schema migrations. service_role (BYPASSRLS) is what the backend
-- uses, so it needs full access to every object the migrations created.
grant all on all tables    in schema public to service_role;
grant all on all sequences in schema public to service_role;
grant execute on all functions in schema public to service_role, authenticated, anon;

-- authenticated/anon access is still gated by the RLS policies in 004_rls.sql.
grant select, insert, update, delete on all tables in schema public to authenticated;

-- Future objects
alter default privileges in schema public grant all on tables    to service_role;
alter default privileges in schema public grant all on sequences to service_role;
alter default privileges in schema public grant execute on functions to service_role, authenticated, anon;

-- Let PostgREST reload its schema cache
notify pgrst, 'reload schema';
