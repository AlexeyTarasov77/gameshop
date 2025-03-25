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
elif [[ "$1" == "test" ]]; then
    remote_host=subpack.fun
    dest_dir="/var/www/gamebazaar.ru/backend/gameshop"
else
  echo "Unsupported parameter: $1"
  exit 1
fi

require_confirmation
version_fn=.last_${1}_version
curr_version=$(git log -1 | cut -d ' ' -f 1)
echo "Updating from $(cat $version_fn) to $curr_version"
echo $curr_version > $version_fn

rsync -aPzc --exclude '.git' --exclude 'media' --exclude '__pycache__' -e 'ssh' "$(pwd)/" \
  "$remote_username@$remote_host:$dest_dir" && \
	ssh "$remote_username@$remote_host" "cd $dest_dir && docker compose restart web"

  
