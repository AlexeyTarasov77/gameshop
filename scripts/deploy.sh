set -e

remote_username=www

require_confirmation() {
  read -p "Are you sure you want to deploy to a prod server? (y/n) " is_confirmed
  echo $is_confirmed
  [[ $is_confirmed != "y" ]] && (echo "Aborting..." && exit 1)
  return 0
}

if [[ "$1" == "prod" ]]; then
  remote_host=gamebazaar.ru
  dest_dir="/home/www/projects/gameshop"
  require_confirmation
elif [[ "$1" == "test" ]]; then
    remote_host=212.193.27.188
    dest_dir="/var/www/gamebazaar.ru/backend/gameshop"
    require_confirmation
else
  echo "Unsupported parameter: $1"
  exit 1
fi


rsync -aPzc --exclude '.git' --exclude 'media' --exclude '__pycache__' -e 'ssh' "$(pwd)/" \
  "$remote_username@$remote_host:$dest_dir" && \
	ssh "$remote_username@$remote_host" "cd $dest_dir && docker compose restart web"

  
