echo "upgrade pip"
python3 -m pip install --upgrade pip
echo "installing requirements"
python3 -m pip install -r requirements.txt

echo "creating database makemigrations"
python3 manage.py makemigrations --noinput

echo "creating database migrate tenants and domains"
python3 manage.py migrate core --noinput

echo "creating database migrate"
python3 manage.py migrate --noinput

echo "collect statics"
python3 manage.py collectstatic --noinput