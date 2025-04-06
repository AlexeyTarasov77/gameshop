BEGIN;
alter table product drop constraint if exists product_sub_id_check;
alter table product add constraint product_sub_id_check CHECK (
  (platform = 'STEAM' AND category = 'GAMES' AND sub_id IS NOT NULL) 
  OR (platform != 'STEAM' OR category != 'GAMES' AND sub_id IS NULL));
COMMIT;

