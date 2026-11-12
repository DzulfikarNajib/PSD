-- Permit the Excel seed archive to retain an unknown capture date.
-- Existing OLX rows and the table's primary key remain unchanged.
alter table public.listing_snapshots
    alter column fetched_at drop not null;

alter table public.listing_snapshots
    add column if not exists data_source text not null default 'olx_refresh';
