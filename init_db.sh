set -e

if [[ -z $MODE ]]; then
	echo "Please set MODE environment variable"
	exit 1
fi
	
read -p "Enter db name: " db_name

if [[ -z $db_name ]]; then
	echo "db_name is required"
	exit 1
fi
echo "db name: $db_name"
psql -U postgres -c "DROP DATABASE "$db_name";"
psql -U postgres -c "CREATE DATABASE "$db_name";"
psql -U postgres -d $db_name -c "CREATE EXTENSION citext;"
make migrations/run mode=$MODE

