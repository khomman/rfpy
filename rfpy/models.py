from datetime import datetime
from rfpy import db

class Stations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station = db.Column(db.String(10), index=True, unique=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    elevation = db.Column(db.Float)
    status = db.Column(db.String(1))

    # Set the relationship to the rftn table with a backref.  That way we can
    # get the station details from the receiver functions table
    receiver_functions = db.relationship('ReceiverFunctions', 
                                        backref='station_receiver_functions',
                                        lazy='dynamic')
    hks = db.relationship('HKResults', backref='hk_station', lazy='dynamic')

    def __repr__(self):
        return f'<Station: {self.id}, {self.station}, {self.latitude}, '\
                f'{self.longitude}, {self.elevation}, {self.status}>'

class Filters(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filter = db.Column(db.Float)

    receiver_functions = db.relationship('ReceiverFunctions',
                                        backref='filter_receiver_functions',
                                        lazy='dynamic')
    hkresult = db.relationship('HKResults', backref='hk_receiver_functions',
                                lazy='dynamic')

    def __repr__(self):
        return f'<Filter Center: {self.id}, {self.filter}'

class HKResults(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station = db.Column(db.Integer, db.ForeignKey('stations.id'))
    filter = db.Column(db.Integer, db.ForeignKey('filters.id'))
    hkpath = db.Column(db.String(255))
    savedhkpath = db.Column(db.String(255))
    h = db.Column(db.Float)
    sigmah = db.Column(db.Float)
    k = db.Column(db.Float)
    sigmak = db.Column(db.Float)
    vp = db.Column(db.Float)

    def __repr__(self):
        return f'<Station: {self.station}, H: {self.h}, K: {self.k}>'

class ReceiverFunctions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    station = db.Column(db.Integer, db.ForeignKey('stations.id'))
    filter = db.Column(db.Integer, db.ForeignKey('filters.id'))
    path = db.Column(db.String(255), index=True)
    new_receiver_function = db.Column(db.Boolean)
    accepted = db.Column(db.Boolean)

    def __repr__(self):
        return f'<Station: {self.station} id: {self.id}, Accepted:'\
                f'{self.accepted}'