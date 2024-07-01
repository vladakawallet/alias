from dotenv import load_dotenv
import os

load_dotenv()


TOKEN = os.environ.get("TOKEN")

#MYSQL 
MYSQLHOST = os.environ.get("MYSQLHOST")
MYSQLUSER = os.environ.get("MYSQLUSER")
MYSQLPASSWORD = os.environ.get("MYSQLPASSWORD")
MYSQLDATABASE = os.environ.get("MYSQLDATABASE")
MYSQLPORT = os.environ.get("MYSQLPORT")
