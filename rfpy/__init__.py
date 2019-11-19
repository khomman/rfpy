import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import Config

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Read config from config.py
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from rfpy import views, models
