echo "upgrade pip"
python3 -m pip install --upgrade pip
echo "installing requirements"
python3 -m pip install -r requirements.txt

echo "creating database"
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput

echo "collect statics"
python3 manage.py collectstatic --noinput