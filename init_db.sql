CREATE DATABASE gameshop;
CREATE ROLE www WITH LOGIN PASSWORD 'd41fdf00e308270f';
GRANT CREATE ON SCHEMA public TO www;
INSERT INTO platform(name) VALUES ('Xbox'), ('Psn'), ('Steam');
INSERT INTO category(name) VALUES ('Игры'), ('Подписки'), ('Карты пополнения'), ('Внутриигровая валюта');
