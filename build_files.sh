echo "upgrade pip"
python3 -m pip install --upgrade pip
echo "installing requirements"
python3 -m pip install -r requirements.txt

echo "creating database"
python3 manage.py makemigrations
python3 manage.py migrate

echo "collect statics"
python3 manage.py collectstatic --noinput