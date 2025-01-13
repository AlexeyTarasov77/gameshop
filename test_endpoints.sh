set -e

for i in {1..100}; do
  curl http://127.0.0.1:8000/api/v1/products/platforms >> /dev/null
  curl http://127.0.0.1:8000/api/v1/products/categories >> /dev/null
  curl http://127.0.0.1:8000/api/v1/products/delivery-methods >> /dev/null
done
