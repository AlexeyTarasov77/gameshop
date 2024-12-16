CREATE DATABASE gameshop;
CREATE ROLE www WITH LOGIN PASSWORD 'd41fdf00e308270f';
GRANT CREATE ON SCHEMA public TO www;
INSERT INTO platform(name, url) VALUES ('Xbox', 'xboxconsole'), ('Psn', 'playstation'), ('Steam', 'steampc');
INSERT INTO category(name, url) VALUES ('Игры', 'game'), ('Подписки', 'subscription'), ('Карты пополнения', 'rechargcards'), ('Внутриигровая валюта', 'donate');
INSERT INTO delivery_method(name, url) VALUES ('ключ', 'key'), ('покупка на аккаунт', 'accpurchase'), ('карта пополнения', 'gift');
