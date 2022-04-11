[Flashscore](https://www.flashscore.ru.com/) parsing with selenium & bs4

## How to install
```
git clone https://github.com/ilyashirko/fs_selenium
cd fs_selenium
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```

Also you will need google-chrome-stable (i used 99.0.4844.82).  
And chromedriver for your chrome version.  

## How to use  
create .env and write full name of your future sqlite3 database to `DATABASE`:  
```
DATABASE=fs.sqlite3
```

create database:  
```
python3 create_db.py
```
and start parser:
```
python3 football_parsing.py
```
