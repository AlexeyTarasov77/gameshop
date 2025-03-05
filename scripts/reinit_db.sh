set -e

if [[ -z $MODE ]]; then
	echo "Please set MODE environment variable"
	exit 1
fi
	
read -p "Enter db name: " db_name

if [[ -z $db_name ]]; then
	db_name=gameshop
fi

echo "db name: $db_name"
psql -U root -c "DROP DATABASE "$db_name";"
psql -U root -c "CREATE DATABASE "$db_name";"
psql -U root -d $db_name -c "CREATE EXTENSION citext;"
make migrations/run mode=$MODE
psql -U root -d $db_name -c "
	CREATE ROLE www WITH LOGIN PASSWORD $USER_PASS;
	GRANT CREATE ON SCHEMA public TO www;
	INSERT INTO platform(name, url) VALUES ('Xbox', 'xboxconsole'), ('Psn', 'playstation'), ('Steam', 'steampc');
	INSERT INTO category(name, url) VALUES ('Игры', 'game'), ('Подписки', 'subscription'), ('Карты пополнения', 'rechargcards'), ('Внутриигровая валюта', 'donate');
	INSERT INTO delivery_method(name, url) VALUES ('ключ', 'key'), ('покупка на аккаунт', 'accpurchase'), ('карта пополнения', 'gift');"

